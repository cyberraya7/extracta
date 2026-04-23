from os import getenv

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import EntityOut, InvestigationOut, InvestigationRunRequest
from app.services.instagram_leak import scan_instagram_leak
from app.services.osint_adapters import run_email_registered_sites
from app.services.osint_enrichment import enrich_entities, SUPPORTED_LABELS
from app.store.memory_store import store

router = APIRouter()


def _investigation_summary(entity_text: str, findings_count: int) -> str:
    if findings_count == 0:
        return f"No public investigation records were found for {entity_text}."
    if findings_count == 1:
        return f"One public investigation record was found for {entity_text}."
    return f"{findings_count} public investigation records were found for {entity_text}."


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


@router.get("/entities/{entity_id}/investigation", response_model=InvestigationOut)
async def get_entity_investigation(
    entity_id: str,
    variant: str | None = Query(None, description="optional investigation variant key"),
):
    entity = store.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    result = store.get_entity_investigation(entity_id, variant)
    if result is None:
        return InvestigationOut(entity_id=entity_id, variant=variant)
    return InvestigationOut(entity_id=entity_id, variant=variant, **result)


@router.post("/entities/{entity_id}/investigation/run", response_model=InvestigationOut)
async def run_entity_investigation(
    entity_id: str,
    body: InvestigationRunRequest | None = None,
):
    entity = store.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    label = str(entity.get("label", ""))
    if label not in SUPPORTED_LABELS:
        return InvestigationOut(
            entity_id=entity_id,
            status="not_requested",
            summary="Investigation is not available for this entity type.",
            findings=[],
            notes=[],
            variant=None,
        )

    req = body or InvestigationRunRequest()
    source = req.source
    entity_text = str(entity.get("text", ""))

    if source == "instagram_leak":
        if label not in {"email", "phone", "username"}:
            return InvestigationOut(
                entity_id=entity_id,
                status="not_requested",
                summary="Leak database lookup is only available for email, phone, and username entities.",
                findings=[],
                notes=[],
                variant="instagram_leak",
            )
        summary, findings, notes = scan_instagram_leak(label, entity_text)
        status = "completed"
        if notes and not findings:
            status = "partial"
        elif not findings and not notes:
            status = "completed"
        payload = {
            "status": status,
            "summary": summary,
            "findings": findings,
            "notes": notes,
        }
        store.set_investigation_variant(
            entity_id,
            "instagram_leak",
            payload,
            session_id=store.current_session_id,
        )
        return InvestigationOut(entity_id=entity_id, variant="instagram_leak", **payload)

    # source == "tools"
    timeout_seconds = int(getenv("EXTRACTA_OSINT_TIMEOUT_SECONDS", "20"))
    if label == "username":
        timeout_seconds = int(getenv("EXTRACTA_OSINT_USERNAME_TIMEOUT_SECONDS", str(timeout_seconds)))

    if label == "email":
        adapter_result = run_email_registered_sites(entity_text, timeout_seconds)
        payload = {
            "status": adapter_result.status,
            "summary": _investigation_summary(entity_text, len(adapter_result.findings)),
            "findings": adapter_result.findings,
            "notes": adapter_result.notes,
        }
        store.set_investigation_variant(entity_id, "tools", payload, session_id=store.current_session_id)
        return InvestigationOut(entity_id=entity_id, variant="tools", **payload)

    result_map = enrich_entities(
        entities=[entity],
        selected_labels=[label],
        timeout_seconds=timeout_seconds,
        session_id=store.current_session_id or "",
    )
    payload = result_map.get(
        entity_id,
        {
            "status": "completed",
            "summary": f"No public investigation records were found for {entity_text}.",
            "findings": [],
            "notes": [],
        },
    )
    store.set_investigation_variant(
        entity_id,
        "tools",
        payload,
        session_id=store.current_session_id,
    )
    return InvestigationOut(entity_id=entity_id, variant="tools", **payload)
