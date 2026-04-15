from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

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
)


@dataclass
class DocumentRecord:
    document_id: str
    filename: str
    file_path: str
    file_type: str = "text"
    text: str = ""
    size: int = 0


class MemoryStore:
    """Database-backed store scoped by analysis session."""

    def __init__(self) -> None:
        self.processed: bool = False
        self.current_session_id: str | None = None

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
        if self.current_session_id == session_id:
            self.current_session_id = None
            self.processed = False
        return True

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
                size=record.size,
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

                doc_ids = document_ids or []
                for pos in ent.get("positions", []):
                    for did in doc_ids:
                        s.add(EntityOccurrenceModel(
                            entity_id=ent["id"],
                            document_id=did,
                            session_id=sid,
                            start_pos=pos["start"],
                            end_pos=pos["end"],
                            raw_text=ent["text"],
                        ))
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
                d["entity_text"] = r.entity_text
                d["start"] = r.start_pos
                d["end"] = r.end_pos
            else:
                d["entities"] = [x.strip() for x in r.entity_text.split(",") if x.strip()]
            results.append(d)
        return results

    # ── Linked entities (session-scoped) ──

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
                s.query(EvidenceSnippetModel).filter(EvidenceSnippetModel.session_id == sid).delete()
                s.query(RelationshipModel).filter(RelationshipModel.session_id == sid).delete()
                s.query(EntityOccurrenceModel).filter(EntityOccurrenceModel.session_id == sid).delete()
                s.query(EntityModel).filter(EntityModel.session_id == sid).delete()
            else:
                s.query(EvidenceSnippetModel).filter(EvidenceSnippetModel.session_id.is_(None)).delete()
                s.query(RelationshipModel).filter(RelationshipModel.session_id.is_(None)).delete()
                s.query(EntityOccurrenceModel).filter(EntityOccurrenceModel.session_id.is_(None)).delete()
                s.query(EntityModel).filter(EntityModel.session_id.is_(None)).delete()
            s.commit()
            self.processed = False

    def clear(self) -> None:
        with self._session() as s:
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
