import logging
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import ProcessRequest, ProcessResponse, ProcessStatusResponse
from app.services.entity_normalizer import normalize_entities
from app.services.link_analyzer import build_graph
from app.services.evidence_mapper import build_evidence
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
    })

    thread = threading.Thread(
        target=_run_processing,
        args=(ner_engine, session_id, doc_ids, body.labels, body.confidence_threshold),
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
) -> None:
    """Heavy processing that runs in a background thread."""
    try:
        store.clear_results()

        all_raw_entities = []
        all_texts: list[tuple[str, str, str]] = []
        per_doc_raw: dict[str, list] = {}

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
            })

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

        store.set_task_progress(session_id, {
            "status": "finalizing",
            "progress": len(doc_ids),
            "total": len(doc_ids),
            "current_file": "Building graph & evidence...",
            "entity_count": 0,
            "edge_count": 0,
        })

        entities = normalize_entities(all_raw_entities)
        store.set_entities(entities, document_ids=doc_ids)

        _record_per_doc_occurrences(entities, per_doc_raw, doc_ids)

        combined_text = "\n\n".join(t for _, _, t in all_texts)
        graph_data = build_graph(combined_text, entities)
        store.set_graph(graph_data)

        for doc_id, doc_name, doc_text in all_texts:
            ev = build_evidence(doc_text, entities, doc_id, doc_name)
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
        })

        logger.info(
            "Processing completed: session=%s entities=%d edges=%d",
            session_id, len(entities), len(graph_data["edges"]),
        )

    except Exception:
        logger.exception("Processing failed for session %s", session_id)
        store.set_task_progress(session_id, {
            "status": "error",
            "progress": 0,
            "total": len(doc_ids),
            "current_file": "",
            "entity_count": 0,
            "edge_count": 0,
            "error": "Processing failed. Check server logs for details.",
        })


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
