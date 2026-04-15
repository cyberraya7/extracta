from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    entity_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)
    labels: Mapped[dict | list] = mapped_column(JSON, default=list)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.3)

    session_documents: Mapped[list["SessionDocumentModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    entities: Mapped[list["EntityModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    relationships: Mapped[list["RelationshipModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class SessionDocumentModel(Base):
    __tablename__ = "session_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    session: Mapped["SessionModel"] = relationship(back_populates="session_documents")
    document: Mapped["DocumentModel"] = relationship(back_populates="session_links")


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[str] = mapped_column(String(1024))
    file_type: Mapped[str] = mapped_column(String(32), default="text")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    session_links: Mapped[list["SessionDocumentModel"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    occurrences: Mapped[list["EntityOccurrenceModel"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    evidence_snippets: Mapped[list["EvidenceSnippetModel"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class EntityModel(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(String(1024))
    label: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    variants: Mapped[dict | list] = mapped_column(JSON, default=list)

    session: Mapped["SessionModel | None"] = relationship(back_populates="entities")
    occurrence_records: Mapped[list["EntityOccurrenceModel"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan"
    )


class EntityOccurrenceModel(Base):
    __tablename__ = "entity_occurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    start_pos: Mapped[int] = mapped_column(Integer, default=0)
    end_pos: Mapped[int] = mapped_column(Integer, default=0)
    raw_text: Mapped[str] = mapped_column(String(1024), default="")

    entity: Mapped["EntityModel"] = relationship(back_populates="occurrence_records")
    document: Mapped["DocumentModel"] = relationship(back_populates="occurrences")


class RelationshipModel(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    relationship_type: Mapped[str] = mapped_column(String(128), default="")
    source_label: Mapped[str] = mapped_column(String(1024), default="")
    target_label: Mapped[str] = mapped_column(String(1024), default="")

    session: Mapped["SessionModel | None"] = relationship(back_populates="relationships")


class EvidenceSnippetModel(Base):
    __tablename__ = "evidence_snippets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_entity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=True
    )
    target_entity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    snippet_text: Mapped[str] = mapped_column(Text, default="")
    entity_text: Mapped[str] = mapped_column(String(1024), default="")
    start_pos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_pos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped["DocumentModel"] = relationship(back_populates="evidence_snippets")
