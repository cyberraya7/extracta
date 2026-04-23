import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import ProcessRequest, ProcessResponse, ProcessStatusResponse
from app.services.entity_normalizer import normalize_entities
from app.services.link_analyzer import build_graph
from app.services.evidence_mapper import build_evidence
from app.services.face_pipeline import extract_faces_for_document, assign_face_clusters
from app.services.osint_enrichment import enrich_entities, SUPPORTED_LABELS
from app.services.regex_extractor import extract_regex_entities
from app.store.memory_store import store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process", response_model=ProcessResponse)
async def process_documents(body: ProcessRequest, request: Request):
    ner_engine = request.app.state.ner_engine

    doc_ids = body.document_ids or store.get_all_document_ids()
    if not doc_ids:
        raise HTTPException(status_code=400, detail="No documents uploaded")

    doc_names = []
    for did in doc_ids:
        doc = store.get_document(did)
        if doc:
            doc_names.append(doc.filename)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    name = ", ".join(doc_names[:3])
    if len(doc_names) > 3:
        name += f" +{len(doc_names) - 3} more"
    session_name = f"{name} ({timestamp})"

    session_id = store.create_session(
        name=session_name,
        document_ids=doc_ids,
        labels=body.labels,
        confidence_threshold=body.confidence_threshold,
    )

    store.set_task_progress(session_id, {
        "status": "processing",
        "progress": 0,
        "total": len(doc_ids),
        "current_file": "",
        "entity_count": 0,
        "edge_count": 0,
        "documents_with_no_text": 0,
        "documents_skipped_for_extraction": 0,
        "warnings": [],
    })

    thread = threading.Thread(
        target=_run_processing,
        args=(
            ner_engine,
            session_id,
            doc_ids,
            body.labels,
            body.confidence_threshold,
            body.enable_osint,
            body.osint_timeout_seconds,
        ),
        daemon=True,
    )
    thread.start()

    return ProcessResponse(
        status="processing",
        entity_count=0,
        edge_count=0,
        document_ids=doc_ids,
        session_id=session_id,
    )


@router.get("/process/status/{session_id}", response_model=ProcessStatusResponse)
async def get_process_status(session_id: str):
    progress = store.get_task_progress(session_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="No processing task found for this session")
    return ProcessStatusResponse(session_id=session_id, **progress)


def _run_processing(
    ner_engine,
    session_id: str,
    doc_ids: list[str],
    labels: list[str] | None,
    confidence_threshold: float,
    enable_osint: bool,
    osint_timeout_seconds: int,
) -> None:
    """Heavy processing that runs in a background thread."""
    try:
        store.clear_results()

        all_raw_entities = []
        all_texts: list[tuple[str, str, str]] = []
        per_doc_raw: dict[str, list] = {}
        all_faces: list[dict] = []
        face_thumb_dir = Path(__file__).resolve().parent.parent.parent / "face_thumbnails"
        documents_with_no_text = 0
        documents_skipped_for_extraction = 0
        warning_messages: list[str] = []

        for i, doc_id in enumerate(doc_ids):
            doc = store.get_document(doc_id)
            if not doc:
                logger.warning("Document %s not found, skipping", doc_id)
                continue

            store.set_task_progress(session_id, {
                "status": "processing",
                "progress": i,
                "total": len(doc_ids),
                "current_file": doc.filename,
                "entity_count": 0,
                "edge_count": 0,
                "documents_with_no_text": documents_with_no_text,
                "documents_skipped_for_extraction": documents_skipped_for_extraction,
                "warnings": warning_messages,
            })

            if not doc.text.strip():
                documents_with_no_text += 1
                if doc.extraction_status != "ok":
                    documents_skipped_for_extraction += 1
                    msg = (
                        f"{doc.filename}: {doc.extraction_message or doc.extraction_status}"
                    )
                    warning_messages.append(msg)
                continue

            ner_raw = ner_engine.predict(
                doc.text,
                labels=labels,
                threshold=confidence_threshold,
            )
            regex_raw = extract_regex_entities(doc.text)
            doc_raw = ner_raw + regex_raw
            all_raw_entities.extend(doc_raw)
            per_doc_raw[doc_id] = doc_raw
            all_texts.append((doc_id, doc.filename, doc.text))

            doc_faces = extract_faces_for_document(
                file_path=doc.file_path,
                document_id=doc_id,
                output_dir=face_thumb_dir,
            )
            all_faces.extend(doc_faces)

        store.set_task_progress(session_id, {
            "status": "finalizing",
            "progress": len(doc_ids),
            "total": len(doc_ids),
            "current_file": "Building graph & evidence...",
            "entity_count": 0,
            "edge_count": 0,
            "documents_with_no_text": documents_with_no_text,
            "documents_skipped_for_extraction": documents_skipped_for_extraction,
            "warnings": warning_messages,
        })

        if not all_texts:
            raise RuntimeError(
                "No extractable text found in selected documents. "
                "Install ffmpeg/whisper for media and OCR dependencies for scanned PDFs."
            )

        entities = normalize_entities(all_raw_entities)
        store.set_entities(entities, document_ids=doc_ids)
        if enable_osint and _should_run_osint(labels):
            store.set_task_progress(session_id, {
                "status": "investigating",
                "progress": len(doc_ids),
                "total": len(doc_ids),
                "current_file": "Running background investigation...",
                "entity_count": len(entities),
                "edge_count": 0,
                "documents_with_no_text": documents_with_no_text,
                "documents_skipped_for_extraction": documents_skipped_for_extraction,
                "warnings": warning_messages,
            })
            osint_results = enrich_entities(
                entities=entities,
                selected_labels=labels,
                timeout_seconds=osint_timeout_seconds,
                session_id=session_id,
            )
            store.set_investigation_results(osint_results, session_id=session_id)
        else:
            store.set_investigation_results({}, session_id=session_id)
        store.clear_faces(session_id)
        if all_faces:
            assign_face_clusters(all_faces)
            store.set_faces(all_faces, session_id=session_id)

        _record_per_doc_occurrences(entities, per_doc_raw, doc_ids)

        combined_text = "\n\n".join(t for _, _, t in all_texts)
        graph_data = build_graph(combined_text, entities)
        store.set_graph(graph_data)

        for doc_id, doc_name, doc_text in all_texts:
            doc_entities = _doc_scoped_entities_for_evidence(
                entities,
                per_doc_raw.get(doc_id, []),
                doc_text,
            )
            ev = build_evidence(doc_text, doc_entities, doc_id, doc_name)
            store.set_evidence(ev["entity_evidence"], ev["edge_evidence"])

        store.processed = True
        store.update_session_counts(session_id, len(entities), len(graph_data["edges"]))

        store.set_task_progress(session_id, {
            "status": "completed",
            "progress": len(doc_ids),
            "total": len(doc_ids),
            "current_file": "",
            "entity_count": len(entities),
            "edge_count": len(graph_data["edges"]),
            "documents_with_no_text": documents_with_no_text,
            "documents_skipped_for_extraction": documents_skipped_for_extraction,
            "warnings": warning_messages,
        })

        logger.info(
            "Processing completed: session=%s entities=%d edges=%d",
            session_id, len(entities), len(graph_data["edges"]),
        )

    except Exception as exc:
        logger.exception("Processing failed for session %s", session_id)
        store.set_task_progress(session_id, {
            "status": "error",
            "progress": 0,
            "total": len(doc_ids),
            "current_file": "",
            "entity_count": 0,
            "edge_count": 0,
            "documents_with_no_text": 0,
            "documents_skipped_for_extraction": 0,
            "warnings": [],
            "error": str(exc) or "Processing failed. Check server logs for details.",
        })


def _should_run_osint(labels: list[str] | None) -> bool:
    if not labels:
        return True
    return any(label in SUPPORTED_LABELS for label in labels)


def _record_per_doc_occurrences(
    entities: list[dict],
    per_doc_raw: dict[str, list],
    doc_ids: list[str],
) -> None:
    """Create explicit per-document occurrence records for cross-doc linking."""
    for ent in entities:
        ent_variants = {v.lower() for v in ent.get("variants", [ent["text"]])}
        for doc_id in doc_ids:
            raw_list = per_doc_raw.get(doc_id, [])
            doc_positions = []
            for raw_ent in raw_list:
                if raw_ent.text.lower() in ent_variants or raw_ent.text == ent["text"]:
                    doc_positions.append({"start": raw_ent.start, "end": raw_ent.end})
            if doc_positions:
                store.set_entity_occurrences(
                    ent["id"], doc_id, doc_positions, ent["text"]
                )


def _doc_scoped_entities_for_evidence(
    entities: list[dict],
    raw_entities: list,
    doc_text: str,
) -> list[dict]:
    by_text: dict[str, list[dict[str, int]]] = {}
    for raw_ent in raw_entities:
        raw_text = getattr(raw_ent, "text", "")
        start = int(getattr(raw_ent, "start", -1))
        end = int(getattr(raw_ent, "end", -1))
        if not raw_text or start < 0 or end <= start or end > len(doc_text):
            continue
        # Strict exact entity evidence: keep only true exact substrings.
        if doc_text[start:end] != raw_text:
            continue
        by_text.setdefault(raw_text, []).append({"start": start, "end": end})

    doc_entities: list[dict] = []
    for ent in entities:
        ent_text = str(ent.get("text", ""))
        positions = by_text.get(ent_text, [])
        if not positions:
            continue
        doc_entities.append(
            {
                **ent,
                "positions": positions,
            }
        )
    return doc_entities
