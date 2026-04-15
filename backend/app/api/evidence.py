from fastapi import APIRouter, HTTPException

from app.models.schemas import EvidenceOut, EvidenceSnippet
from app.store.memory_store import store

router = APIRouter()


@router.get("/evidence/{entity_id}", response_model=EvidenceOut)
async def get_entity_evidence(entity_id: str):
    snippets = store.get_entity_evidence(entity_id)
    if not snippets:
        raise HTTPException(
            status_code=404, detail=f"No evidence found for entity {entity_id}"
        )
    return EvidenceOut(entity_id=entity_id, snippets=snippets)


@router.get("/evidence/edge/{source}/{target}", response_model=EvidenceOut)
async def get_edge_evidence(source: str, target: str):
    snippets = store.get_edge_evidence(source, target)
    edge_key = "|".join(sorted([source, target]))
    if not snippets:
        raise HTTPException(
            status_code=404,
            detail=f"No evidence found for edge {source} - {target}",
        )
    return EvidenceOut(edge_key=edge_key, snippets=snippets)
