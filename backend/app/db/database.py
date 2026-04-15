import os
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./yose.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _migrate_add_columns() -> None:
    """Add session_id columns to existing tables if missing (lightweight migration)."""
    insp = inspect(engine)
    migrations: list[tuple[str, str, str]] = [
        ("entities", "session_id", "VARCHAR(36)"),
        ("entity_occurrences", "session_id", "VARCHAR(36)"),
        ("relationships", "session_id", "VARCHAR(36)"),
        ("evidence_snippets", "session_id", "VARCHAR(36)"),
    ]
    with engine.begin() as conn:
        for table, column, col_type in migrations:
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            if column not in existing:
                logger.info("Adding column %s.%s", table, column)
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))


def create_all() -> None:
    from app.db.models import (  # noqa: F401
        SessionModel,
        SessionDocumentModel,
        DocumentModel,
        EntityModel,
        EntityOccurrenceModel,
        RelationshipModel,
        EvidenceSnippetModel,
    )
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
