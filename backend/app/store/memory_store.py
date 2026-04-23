from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    SessionModel,
    SessionDocumentModel,
    DocumentModel,
    EntityModel,
    EntityOccurrenceModel,
    RelationshipModel,
    EvidenceSnippetModel,
    FaceInstanceModel,
    FaceClusterLabelModel,
)


@dataclass
class DocumentRecord:
    document_id: str
    filename: str
    file_path: str
    file_type: str = "text"
    text: str = ""
    size: int = 0
    extraction_status: str = "ok"
    extraction_message: str = ""
    extractor_used: str = ""
    exif_metadata: dict | None = None


class MemoryStore:
    """Database-backed store scoped by analysis session."""

    def __init__(self) -> None:
        self.processed: bool = False
        self.current_session_id: str | None = None
        self._task_progress: dict[str, dict] = {}
        # session_id -> entity_id -> variant_key -> investigation payload dict
        self._investigation_results: dict[str, dict[str, dict[str, dict]]] = {}

    def set_task_progress(self, session_id: str, progress: dict) -> None:
        self._task_progress[session_id] = progress

    def get_task_progress(self, session_id: str) -> dict | None:
        return self._task_progress.get(session_id)

    def clear_task_progress(self, session_id: str) -> None:
        self._task_progress.pop(session_id, None)

    def _session(self) -> Session:
        return SessionLocal()

    # ── Sessions ──

    def create_session(
        self,
        name: str,
        document_ids: list[str],
        labels: list[str] | None = None,
        confidence_threshold: float = 0.3,
    ) -> str:
        session_id = str(uuid.uuid4())
        with self._session() as s:
            sess = SessionModel(
                id=session_id,
                name=name,
                created_at=datetime.now(timezone.utc),
                document_count=len(document_ids),
                labels=labels or [],
                confidence_threshold=confidence_threshold,
            )
            s.add(sess)
            for doc_id in document_ids:
                s.add(SessionDocumentModel(session_id=session_id, document_id=doc_id))
            s.commit()
        self.current_session_id = session_id
        return session_id

    def get_sessions(self) -> list[dict]:
        with self._session() as s:
            rows = s.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "document_count": r.document_count,
                    "entity_count": r.entity_count,
                    "edge_count": r.edge_count,
                }
                for r in rows
            ]

    def get_session_info(self, session_id: str) -> dict | None:
        with self._session() as s:
            row = s.get(SessionModel, session_id)
            if not row:
                return None
            doc_links = (
                s.query(SessionDocumentModel)
                .filter(SessionDocumentModel.session_id == session_id)
                .all()
            )
            doc_ids = [dl.document_id for dl in doc_links]
            docs = []
            for did in doc_ids:
                doc = s.get(DocumentModel, did)
                if doc:
                    docs.append({
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "size": doc.size,
                        "text_length": len(doc.extracted_text),
                        "extraction_status": doc.extraction_status,
                        "extraction_message": doc.extraction_message,
                        "extractor_used": doc.extractor_used,
                        "exif_metadata": doc.exif_metadata,
                    })
            return {
                "id": row.id,
                "name": row.name,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "document_count": row.document_count,
                "entity_count": row.entity_count,
                "edge_count": row.edge_count,
                "documents": docs,
            }

    def load_session(self, session_id: str) -> bool:
        with self._session() as s:
            row = s.get(SessionModel, session_id)
            if not row:
                return False
        self.current_session_id = session_id
        self.processed = True
        return True

    def rename_session(self, session_id: str, name: str) -> bool:
        with self._session() as s:
            row = s.get(SessionModel, session_id)
            if not row:
                return False
            row.name = name
            s.commit()
            return True

    def delete_session(self, session_id: str) -> bool:
        with self._session() as s:
            row = s.get(SessionModel, session_id)
            if not row:
                return False
            s.delete(row)
            s.commit()
        self._investigation_results.pop(session_id, None)
        if self.current_session_id == session_id:
            self.current_session_id = None
            self.processed = False
        return True

    def delete_sessions_bulk(self, session_ids: list[str]) -> tuple[list[str], list[str]]:
        unique_ids = list(dict.fromkeys(session_ids))
        if not unique_ids:
            return [], []
        deleted: list[str] = []
        with self._session() as s:
            rows = (
                s.query(SessionModel)
                .filter(SessionModel.id.in_(unique_ids))
                .all()
            )
            existing_ids = {row.id for row in rows}
            for row in rows:
                deleted.append(row.id)
                s.delete(row)
            s.commit()
        if self.current_session_id and self.current_session_id in deleted:
            self.current_session_id = None
            self.processed = False
        for sid in deleted:
            self._investigation_results.pop(sid, None)
        not_found = [sid for sid in unique_ids if sid not in set(deleted)]
        return deleted, not_found

    def update_session_counts(self, session_id: str, entity_count: int, edge_count: int) -> None:
        with self._session() as s:
            row = s.get(SessionModel, session_id)
            if row:
                row.entity_count = entity_count
                row.edge_count = edge_count
                s.commit()

    def get_session_document_ids(self, session_id: str) -> list[str]:
        with self._session() as s:
            links = (
                s.query(SessionDocumentModel)
                .filter(SessionDocumentModel.session_id == session_id)
                .all()
            )
            return [l.document_id for l in links]

    # ── Documents ──

    def add_document(self, record: DocumentRecord) -> None:
        with self._session() as s:
            s.add(DocumentModel(
                id=record.document_id,
                filename=record.filename,
                file_path=record.file_path,
                file_type=record.file_type,
                extracted_text=record.text,
                extraction_status=record.extraction_status,
                extraction_message=record.extraction_message,
                extractor_used=record.extractor_used,
                size=record.size,
                exif_metadata=record.exif_metadata,
            ))
            s.commit()

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        with self._session() as s:
            row = s.get(DocumentModel, doc_id)
            if not row:
                return None
            return DocumentRecord(
                document_id=row.id,
                filename=row.filename,
                file_path=row.file_path,
                file_type=row.file_type,
                text=row.extracted_text,
                size=row.size,
                extraction_status=row.extraction_status,
                extraction_message=row.extraction_message,
                extractor_used=row.extractor_used,
                exif_metadata=row.exif_metadata,
            )

    def get_all_documents(self) -> list[DocumentRecord]:
        with self._session() as s:
            rows = s.query(DocumentModel).all()
            return [
                DocumentRecord(
                    document_id=r.id,
                    filename=r.filename,
                    file_path=r.file_path,
                    file_type=r.file_type,
                    text=r.extracted_text,
                    size=r.size,
                    extraction_status=r.extraction_status,
                    extraction_message=r.extraction_message,
                    extractor_used=r.extractor_used,
                    exif_metadata=r.exif_metadata,
                )
                for r in rows
            ]

    def get_all_document_ids(self) -> list[str]:
        with self._session() as s:
            return [r.id for r in s.query(DocumentModel.id).all()]

    def delete_document(self, doc_id: str) -> bool:
        with self._session() as s:
            doc = s.get(DocumentModel, doc_id)
            if not doc:
                return False
            s.delete(doc)
            s.commit()
            return True

    # ── Entities (session-scoped) ──

    def set_entities(self, entities: list[dict], document_ids: list[str] | None = None) -> None:
        """Store entity records. Per-document occurrences are handled separately
        by _record_per_doc_occurrences to avoid incorrect cross-product linking."""
        sid = self.current_session_id
        with self._session() as s:
            for ent in entities:
                db_ent = EntityModel(
                    id=ent["id"],
                    session_id=sid,
                    text=ent["text"],
                    label=ent["label"],
                    score=ent["score"],
                    occurrences=ent["occurrences"],
                    variants=ent.get("variants", []),
                )
                s.add(db_ent)
            s.commit()

    def set_entity_occurrences(
        self, entity_id: str, document_id: str, positions: list[dict], raw_text: str
    ) -> None:
        sid = self.current_session_id
        with self._session() as s:
            for pos in positions:
                s.add(EntityOccurrenceModel(
                    entity_id=entity_id,
                    document_id=document_id,
                    session_id=sid,
                    start_pos=pos["start"],
                    end_pos=pos["end"],
                    raw_text=raw_text,
                ))
            s.commit()

    def get_entities(
        self,
        entity_type: str | None = None,
        min_confidence: float = 0.0,
        search: str | None = None,
    ) -> list[dict]:
        sid = self.current_session_id
        with self._session() as s:
            q = s.query(EntityModel)
            if sid:
                q = q.filter(EntityModel.session_id == sid)
            if entity_type:
                q = q.filter(EntityModel.label == entity_type)
            if min_confidence > 0:
                q = q.filter(EntityModel.score >= min_confidence)
            if search:
                q = q.filter(EntityModel.text.ilike(f"%{search}%"))
            rows = q.all()
            result = []
            for r in rows:
                occ_q = s.query(EntityOccurrenceModel).filter(
                    EntityOccurrenceModel.entity_id == r.id
                )
                if sid:
                    occ_q = occ_q.filter(EntityOccurrenceModel.session_id == sid)
                occs = occ_q.all()
                positions = [{"start": o.start_pos, "end": o.end_pos} for o in occs]
                result.append({
                    "id": r.id,
                    "text": r.text,
                    "label": r.label,
                    "score": r.score,
                    "occurrences": r.occurrences,
                    "variants": r.variants if isinstance(r.variants, list) else [],
                    "positions": positions,
                })
            return result

    def get_entity(self, entity_id: str) -> dict | None:
        sid = self.current_session_id
        with self._session() as s:
            q = s.query(EntityModel).filter(EntityModel.id == entity_id)
            if sid:
                q = q.filter(EntityModel.session_id == sid)
            row = q.first()
            if not row:
                return None
            return {
                "id": row.id,
                "text": row.text,
                "label": row.label,
                "score": row.score,
                "occurrences": row.occurrences,
                "variants": row.variants if isinstance(row.variants, list) else [],
            }

    def _normalize_entity_investigation_map(self, stored: dict | None) -> dict[str, dict]:
        """Convert legacy flat payload to variant-keyed map."""
        if stored is None:
            return {}
        if not isinstance(stored, dict):
            return {}
        variant_keys = (
            "registered_websites",
            "tools",
            "instagram_leak",
            "email_information",
        )
        if any(k in stored for k in variant_keys):
            return {k: v for k, v in stored.items() if k in variant_keys and isinstance(v, dict)}
        if "registered_websites" in stored:
            return {k: v for k, v in stored.items() if isinstance(v, dict)}
        # Legacy: single investigation payload per entity
        if "findings" in stored or "status" in stored:
            return {"registered_websites": stored}
        return {}

    def set_investigation_variant(
        self,
        entity_id: str,
        variant: str,
        payload: dict,
        session_id: str | None = None,
    ) -> None:
        sid = session_id or self.current_session_id
        if not sid:
            return
        bucket = self._investigation_results.setdefault(sid, {})
        current = bucket.get(entity_id)
        norm = self._normalize_entity_investigation_map(current) if isinstance(current, dict) else {}
        norm[variant] = payload
        bucket[entity_id] = norm

    def set_investigation_results(
        self,
        results_by_entity: dict[str, dict],
        session_id: str | None = None,
        merge: bool = False,
        variant: str = "registered_websites",
    ) -> None:
        sid = session_id or self.current_session_id
        if not sid:
            return
        if merge:
            for ent_id, payload in results_by_entity.items():
                self.set_investigation_variant(ent_id, variant, payload, session_id=sid)
            return
        self._investigation_results[sid] = {}
        for ent_id, payload in results_by_entity.items():
            self.set_investigation_variant(ent_id, variant, payload, session_id=sid)

    def get_entity_investigation(self, entity_id: str, variant: str | None = None) -> dict | None:
        sid = self.current_session_id
        if not sid:
            return None
        raw = self._investigation_results.get(sid, {}).get(entity_id)
        if raw is None:
            return None
        norm = self._normalize_entity_investigation_map(raw)
        if not norm and isinstance(raw, dict):
            norm = {"registered_websites": raw}
        if variant:
            out = norm.get(variant)
            if out is None and variant == "tools":
                out = norm.get("registered_websites")
            return out
        prefer = norm.get("tools") or norm.get("registered_websites")
        if prefer is not None:
            return prefer
        if norm:
            return next(iter(norm.values()))
        return None

    def list_entity_investigation_variants(self, entity_id: str) -> list[str]:
        sid = self.current_session_id
        if not sid:
            return []
        raw = self._investigation_results.get(sid, {}).get(entity_id)
        if raw is None:
            return []
        norm = self._normalize_entity_investigation_map(raw)
        return list(norm.keys())

    # ── Graph (session-scoped) ──

    def set_graph(self, graph: dict) -> None:
        sid = self.current_session_id
        with self._session() as s:
            for edge in graph.get("edges", []):
                s.add(RelationshipModel(
                    session_id=sid,
                    source_entity_id=edge["source"],
                    target_entity_id=edge["target"],
                    weight=edge.get("weight", 1.0),
                    relationship_type=edge.get("relationship", ""),
                    source_label=edge.get("source_label", ""),
                    target_label=edge.get("target_label", ""),
                ))
            s.commit()

    def get_graph(self, type_filter: str | None = None) -> dict:
        sid = self.current_session_id
        with self._session() as s:
            ent_q = s.query(EntityModel)
            if sid:
                ent_q = ent_q.filter(EntityModel.session_id == sid)
            if type_filter:
                ent_q = ent_q.filter(EntityModel.label == type_filter)

            ent_rows = ent_q.all()
            ent_ids = {r.id for r in ent_rows}

            rel_q = s.query(RelationshipModel)
            if sid:
                rel_q = rel_q.filter(RelationshipModel.session_id == sid)
            if type_filter:
                rel_q = rel_q.filter(
                    (RelationshipModel.source_entity_id.in_(ent_ids))
                    | (RelationshipModel.target_entity_id.in_(ent_ids))
                )
            edges = rel_q.all()

            connected_ids = set()
            for e in edges:
                connected_ids.add(e.source_entity_id)
                connected_ids.add(e.target_entity_id)

            if type_filter:
                all_ent_rows = (
                    s.query(EntityModel)
                    .filter(EntityModel.id.in_(connected_ids))
                    .all()
                )
            else:
                all_ent_rows = ent_rows

            nodes = []
            for r in all_ent_rows:
                conn_count = sum(
                    1 for e in edges
                    if e.source_entity_id == r.id or e.target_entity_id == r.id
                )
                nodes.append({
                    "id": r.id,
                    "label": r.text,
                    "type": r.label,
                    "score": r.score,
                    "occurrences": r.occurrences,
                    "connections": conn_count,
                })

            edge_list = [
                {
                    "source": e.source_entity_id,
                    "target": e.target_entity_id,
                    "weight": round(e.weight, 2),
                    "relationship": e.relationship_type,
                    "source_label": e.source_label,
                    "target_label": e.target_label,
                }
                for e in edges
            ]

            return {"nodes": nodes, "edges": edge_list}

    # ── Evidence (session-scoped) ──

    def set_evidence(
        self,
        entity_evidence: dict[str, list[dict]],
        edge_evidence: dict[str, list[dict]],
    ) -> None:
        sid = self.current_session_id
        with self._session() as s:
            for ent_id, snippets in entity_evidence.items():
                for snip in snippets:
                    s.add(EvidenceSnippetModel(
                        session_id=sid,
                        entity_id=ent_id,
                        document_id=snip["document_id"],
                        snippet_text=snip["text"],
                        entity_text=snip.get("entity_text", ""),
                        highlight_ranges=snip.get("highlight_ranges", []),
                        start_pos=snip.get("start"),
                        end_pos=snip.get("end"),
                    ))
            for edge_key, snippets in edge_evidence.items():
                parts = edge_key.split("|")
                src_id = parts[0] if len(parts) > 0 else None
                tgt_id = parts[1] if len(parts) > 1 else None
                for snip in snippets:
                    s.add(EvidenceSnippetModel(
                        session_id=sid,
                        source_entity_id=src_id,
                        target_entity_id=tgt_id,
                        document_id=snip["document_id"],
                        snippet_text=snip["text"],
                        entity_text=", ".join(snip.get("entities", [])),
                        highlight_ranges=snip.get("highlight_ranges", []),
                    ))
            s.commit()

    def get_entity_evidence(self, entity_id: str) -> list[dict]:
        with self._session() as s:
            q = s.query(EvidenceSnippetModel).filter(
                EvidenceSnippetModel.entity_id == entity_id
            )
            sid = self.current_session_id
            if sid:
                q = q.filter(EvidenceSnippetModel.session_id == sid)
            rows = q.all()
            return self._snippets_to_dicts(s, rows, is_entity=True)

    def get_edge_evidence(self, source: str, target: str) -> list[dict]:
        key_parts = sorted([source, target])
        with self._session() as s:
            q = s.query(EvidenceSnippetModel).filter(
                EvidenceSnippetModel.source_entity_id == key_parts[0],
                EvidenceSnippetModel.target_entity_id == key_parts[1],
            )
            sid = self.current_session_id
            if sid:
                q = q.filter(EvidenceSnippetModel.session_id == sid)
            rows = q.all()
            return self._snippets_to_dicts(s, rows, is_entity=False)

    def _snippets_to_dicts(
        self, s: Session, rows: list[EvidenceSnippetModel], is_entity: bool
    ) -> list[dict]:
        results = []
        for r in rows:
            doc = s.get(DocumentModel, r.document_id)
            doc_name = doc.filename if doc else "unknown"
            d: dict = {
                "text": r.snippet_text,
                "document_id": r.document_id,
                "document_name": doc_name,
            }
            if is_entity:
                entity_text = (r.entity_text or "").strip()
                raw_ranges = r.highlight_ranges if isinstance(r.highlight_ranges, list) else []
                valid_ranges: list[dict[str, int]] = []
                if entity_text:
                    for item in raw_ranges:
                        if not isinstance(item, dict):
                            continue
                        start = int(item.get("start", -1))
                        end = int(item.get("end", -1))
                        if start < 0 or end <= start or end > len(r.snippet_text or ""):
                            continue
                        span = (r.snippet_text or "")[start:end]
                        if span.casefold() != entity_text.casefold():
                            continue
                        valid_ranges.append({"start": start, "end": end})
                    # Drop stale/incorrect snippets that have no exact highlight for the entity.
                    if not valid_ranges:
                        continue
                d["entity_text"] = r.entity_text
                d["highlight_ranges"] = valid_ranges
                d["start"] = r.start_pos
                d["end"] = r.end_pos
            else:
                d["entities"] = [x.strip() for x in r.entity_text.split(",") if x.strip()]
                d["highlight_ranges"] = (
                    r.highlight_ranges if isinstance(r.highlight_ranges, list) else []
                )
            results.append(d)
        return results

    # ── Linked entities (session-scoped) ──

    # ── Faces (session-scoped) ──

    def clear_faces(self, session_id: str | None = None) -> None:
        sid = session_id or self.current_session_id
        with self._session() as s:
            q = s.query(FaceInstanceModel)
            if sid:
                q = q.filter(FaceInstanceModel.session_id == sid)
            else:
                q = q.filter(FaceInstanceModel.session_id.is_(None))
            q.delete()
            s.commit()

    def set_faces(self, faces: list[dict], session_id: str | None = None) -> None:
        sid = session_id or self.current_session_id
        with self._session() as s:
            for face in faces:
                bbox = face.get("bbox", [0, 0, 0, 0])
                s.add(
                    FaceInstanceModel(
                        id=face["id"],
                        session_id=sid,
                        document_id=face["document_id"],
                        source_type=face.get("source_type", "image"),
                        source_ref=face.get("source_ref", ""),
                        bbox_x1=float(bbox[0]) if len(bbox) > 0 else 0.0,
                        bbox_y1=float(bbox[1]) if len(bbox) > 1 else 0.0,
                        bbox_x2=float(bbox[2]) if len(bbox) > 2 else 0.0,
                        bbox_y2=float(bbox[3]) if len(bbox) > 3 else 0.0,
                        confidence=face.get("confidence", 0.0),
                        embedding=face.get("embedding", []),
                        cluster_id=face.get("cluster_id", ""),
                        thumbnail_path=face.get("thumbnail_path", ""),
                    )
                )
            s.commit()

    def get_faces(self) -> list[dict]:
        sid = self.current_session_id
        with self._session() as s:
            q = s.query(FaceInstanceModel)
            if sid:
                q = q.filter(FaceInstanceModel.session_id == sid)
            rows = q.all()
            return [
                {
                    "id": r.id,
                    "document_id": r.document_id,
                    "source_type": r.source_type,
                    "source_ref": r.source_ref,
                    "bbox": [r.bbox_x1, r.bbox_y1, r.bbox_x2, r.bbox_y2],
                    "confidence": r.confidence,
                    "cluster_id": r.cluster_id,
                    "thumbnail_path": r.thumbnail_path,
                }
                for r in rows
            ]

    def get_similar_faces(self, face_id: str) -> list[dict]:
        sid = self.current_session_id
        with self._session() as s:
            seed = s.get(FaceInstanceModel, face_id)
            if not seed:
                return []
            q = s.query(FaceInstanceModel).filter(
                FaceInstanceModel.cluster_id == seed.cluster_id
            )
            if sid:
                q = q.filter(FaceInstanceModel.session_id == sid)
            rows = q.all()
            return [
                {
                    "id": r.id,
                    "document_id": r.document_id,
                    "source_type": r.source_type,
                    "source_ref": r.source_ref,
                    "bbox": [r.bbox_x1, r.bbox_y1, r.bbox_x2, r.bbox_y2],
                    "confidence": r.confidence,
                    "cluster_id": r.cluster_id,
                    "thumbnail_path": r.thumbnail_path,
                }
                for r in rows
            ]

    def get_face(self, face_id: str) -> dict | None:
        sid = self.current_session_id
        with self._session() as s:
            q = s.query(FaceInstanceModel).filter(FaceInstanceModel.id == face_id)
            if sid:
                q = q.filter(FaceInstanceModel.session_id == sid)
            row = q.first()
            if not row:
                return None
            return {
                "id": row.id,
                "document_id": row.document_id,
                "source_type": row.source_type,
                "source_ref": row.source_ref,
                "bbox": [row.bbox_x1, row.bbox_y1, row.bbox_x2, row.bbox_y2],
                "confidence": row.confidence,
                "cluster_id": row.cluster_id,
                "thumbnail_path": row.thumbnail_path,
            }

    def compare_faces(
        self,
        face_id_a: str,
        face_id_b: str,
        threshold: float | None = None,
    ) -> dict | None:
        sid = self.current_session_id
        if threshold is None:
            threshold = float(
                os.environ.get("EXTRACTA_FACE_SIMILARITY_THRESHOLD", "0.38")
            )

        with self._session() as s:
            q_a = s.query(FaceInstanceModel).filter(FaceInstanceModel.id == face_id_a)
            q_b = s.query(FaceInstanceModel).filter(FaceInstanceModel.id == face_id_b)
            if sid:
                q_a = q_a.filter(FaceInstanceModel.session_id == sid)
                q_b = q_b.filter(FaceInstanceModel.session_id == sid)
            row_a = q_a.first()
            row_b = q_b.first()
            if not row_a or not row_b:
                return None

            emb_a = np.array(row_a.embedding or [], dtype=np.float32)
            emb_b = np.array(row_b.embedding or [], dtype=np.float32)
            if emb_a.size == 0 or emb_b.size == 0:
                return None

            norm_a = np.linalg.norm(emb_a)
            norm_b = np.linalg.norm(emb_b)
            if norm_a == 0 or norm_b == 0:
                return None

            similarity = float(np.dot(emb_a, emb_b) / (norm_a * norm_b))
            return {
                "face_id_a": face_id_a,
                "face_id_b": face_id_b,
                "similarity": similarity,
                "threshold": threshold,
                "match": similarity >= threshold,
            }

    def get_linked_faces(self) -> list[dict]:
        sid = self.current_session_id
        with self._session() as s:
            q = s.query(FaceInstanceModel)
            if sid:
                q = q.filter(FaceInstanceModel.session_id == sid)
            rows = q.all()

            grouped: dict[str, list[FaceInstanceModel]] = {}
            for row in rows:
                if not row.cluster_id:
                    continue
                grouped.setdefault(row.cluster_id, []).append(row)

            linked: list[dict] = []
            for cluster_id, cluster_rows in grouped.items():
                doc_ids = sorted({r.document_id for r in cluster_rows})
                if len(doc_ids) < 2:
                    continue
                suggested_name = self._suggest_face_cluster_name(s, sid, doc_ids)
                display_name = self._get_face_cluster_display_name(s, sid, cluster_id)
                doc_names = {}
                for did in doc_ids:
                    doc = s.get(DocumentModel, did)
                    doc_names[did] = doc.filename if doc else "unknown"
                linked.append(
                    {
                        "cluster_id": cluster_id,
                        "face_count": len(cluster_rows),
                        "document_count": len(doc_ids),
                        "document_ids": doc_ids,
                        "document_names": doc_names,
                        "suggested_name": suggested_name,
                        "display_name": display_name,
                        "faces": [
                            {
                                "id": r.id,
                                "document_id": r.document_id,
                                "source_type": r.source_type,
                                "source_ref": r.source_ref,
                                "bbox": [r.bbox_x1, r.bbox_y1, r.bbox_x2, r.bbox_y2],
                                "confidence": r.confidence,
                                "cluster_id": r.cluster_id,
                                "thumbnail_path": r.thumbnail_path,
                            }
                            for r in cluster_rows
                        ],
                    }
                )
            return linked

    def _get_face_cluster_display_name(
        self,
        s: Session,
        session_id: str | None,
        cluster_id: str,
    ) -> str | None:
        q = s.query(FaceClusterLabelModel).filter(
            FaceClusterLabelModel.cluster_id == cluster_id
        )
        if session_id:
            q = q.filter(FaceClusterLabelModel.session_id == session_id)
        else:
            q = q.filter(FaceClusterLabelModel.session_id.is_(None))
        row = q.first()
        if not row or not row.display_name.strip():
            return None
        return row.display_name.strip()

    def _suggest_face_cluster_name(
        self,
        s: Session,
        session_id: str | None,
        document_ids: list[str],
    ) -> str | None:
        if not document_ids:
            return None
        q = (
            s.query(EntityModel.text, func.count(EntityOccurrenceModel.id).label("hits"))
            .join(
                EntityOccurrenceModel,
                EntityOccurrenceModel.entity_id == EntityModel.id,
            )
            .filter(
                EntityModel.label == "person",
                EntityOccurrenceModel.document_id.in_(document_ids),
            )
        )
        if session_id:
            q = q.filter(
                EntityModel.session_id == session_id,
                EntityOccurrenceModel.session_id == session_id,
            )
        else:
            q = q.filter(
                EntityModel.session_id.is_(None),
                EntityOccurrenceModel.session_id.is_(None),
            )
        row = (
            q.group_by(EntityModel.text)
            .order_by(func.count(EntityOccurrenceModel.id).desc(), EntityModel.text.asc())
            .first()
        )
        if not row:
            return None
        text = (row[0] or "").strip()
        return text or None

    def set_face_cluster_display_name(
        self,
        cluster_id: str,
        display_name: str,
        session_id: str | None = None,
    ) -> dict:
        sid = session_id or self.current_session_id
        clean_name = display_name.strip()
        with self._session() as s:
            q = s.query(FaceClusterLabelModel).filter(
                FaceClusterLabelModel.cluster_id == cluster_id
            )
            if sid:
                q = q.filter(FaceClusterLabelModel.session_id == sid)
            else:
                q = q.filter(FaceClusterLabelModel.session_id.is_(None))
            row = q.first()
            if row is None:
                row = FaceClusterLabelModel(
                    session_id=sid,
                    cluster_id=cluster_id,
                    display_name=clean_name,
                )
                s.add(row)
            else:
                row.display_name = clean_name
                row.updated_at = datetime.now(timezone.utc)
            s.commit()
            return {
                "cluster_id": cluster_id,
                "display_name": clean_name,
            }

    def get_linked_entities(self) -> list[dict]:
        sid = self.current_session_id
        with self._session() as s:
            occ_q = s.query(EntityOccurrenceModel)
            if sid:
                occ_q = occ_q.filter(EntityOccurrenceModel.session_id == sid)

            subq = (
                occ_q.with_entities(
                    EntityOccurrenceModel.entity_id,
                    func.count(distinct(EntityOccurrenceModel.document_id)).label("doc_count"),
                )
                .group_by(EntityOccurrenceModel.entity_id)
                .having(func.count(distinct(EntityOccurrenceModel.document_id)) >= 2)
                .subquery()
            )
            rows = (
                s.query(EntityModel, subq.c.doc_count)
                .join(subq, EntityModel.id == subq.c.entity_id)
                .all()
            )

            results = []
            for ent, doc_count in rows:
                occ_filter = s.query(EntityOccurrenceModel).filter(
                    EntityOccurrenceModel.entity_id == ent.id
                )
                if sid:
                    occ_filter = occ_filter.filter(EntityOccurrenceModel.session_id == sid)
                occ_rows = occ_filter.all()
                doc_ids = list({o.document_id for o in occ_rows})
                doc_names = {}
                for did in doc_ids:
                    doc = s.get(DocumentModel, did)
                    doc_names[did] = doc.filename if doc else "unknown"

                results.append({
                    "entity_id": ent.id,
                    "text": ent.text,
                    "label": ent.label,
                    "score": ent.score,
                    "document_count": doc_count,
                    "document_ids": doc_ids,
                    "document_names": doc_names,
                })
            return results


    # ── Cleanup (session-scoped) ──

    def clear_results(self) -> None:
        """Clear processed results for the current session only."""
        sid = self.current_session_id
        with self._session() as s:
            if sid:
                self._investigation_results.pop(sid, None)
                s.query(FaceClusterLabelModel).filter(FaceClusterLabelModel.session_id == sid).delete()
                s.query(FaceInstanceModel).filter(FaceInstanceModel.session_id == sid).delete()
                s.query(EvidenceSnippetModel).filter(EvidenceSnippetModel.session_id == sid).delete()
                s.query(RelationshipModel).filter(RelationshipModel.session_id == sid).delete()
                s.query(EntityOccurrenceModel).filter(EntityOccurrenceModel.session_id == sid).delete()
                s.query(EntityModel).filter(EntityModel.session_id == sid).delete()
            else:
                s.query(FaceClusterLabelModel).filter(FaceClusterLabelModel.session_id.is_(None)).delete()
                s.query(FaceInstanceModel).filter(FaceInstanceModel.session_id.is_(None)).delete()
                s.query(EvidenceSnippetModel).filter(EvidenceSnippetModel.session_id.is_(None)).delete()
                s.query(RelationshipModel).filter(RelationshipModel.session_id.is_(None)).delete()
                s.query(EntityOccurrenceModel).filter(EntityOccurrenceModel.session_id.is_(None)).delete()
                s.query(EntityModel).filter(EntityModel.session_id.is_(None)).delete()
            s.commit()
            self.processed = False

    def clear(self) -> None:
        self._investigation_results.clear()
        with self._session() as s:
            s.query(FaceClusterLabelModel).delete()
            s.query(FaceInstanceModel).delete()
            s.query(EvidenceSnippetModel).delete()
            s.query(RelationshipModel).delete()
            s.query(EntityOccurrenceModel).delete()
            s.query(EntityModel).delete()
            s.query(SessionDocumentModel).delete()
            s.query(SessionModel).delete()
            s.query(DocumentModel).delete()
            s.commit()
            self.processed = False
            self.current_session_id = None


store = MemoryStore()
