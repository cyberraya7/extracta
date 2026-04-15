from fastapi import APIRouter, Query

from app.models.schemas import EntityOut
from app.store.memory_store import store

router = APIRouter()


@router.get("/entities", response_model=list[EntityOut])
async def list_entities(
    type: str | None = Query(None, description="Filter by entity type"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    search: str | None = Query(None, description="Search entity text"),
):
    return store.get_entities(
        entity_type=type,
        min_confidence=min_confidence,
        search=search,
    )


@router.get("/entities/linked")
async def get_linked_entities():
    """Return entities that appear in 2 or more documents."""
    return store.get_linked_entities()
