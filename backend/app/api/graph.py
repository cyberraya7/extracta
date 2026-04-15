from fastapi import APIRouter, Query

from app.models.schemas import GraphOut
from app.store.memory_store import store

router = APIRouter()


@router.get("/graph", response_model=GraphOut)
async def get_graph(
    type: str | None = Query(None, description="Filter by entity type"),
):
    return store.get_graph(type_filter=type)
