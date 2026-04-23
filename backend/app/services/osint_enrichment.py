from __future__ import annotations

import os
from typing import Callable

from app.services.osint_adapters import (
    AdapterResult,
    run_email_lookup,
    run_organization_lookup,
    run_phone_lookup,
    run_username_lookup,
)

SUPPORTED_LABELS = {"email", "phone", "username", "organization"}


def _entity_summary(entity_text: str, findings_count: int) -> str:
    if findings_count == 0:
        return f"No public investigation records were found for {entity_text}."
    if findings_count == 1:
        return f"One public investigation record was found for {entity_text}."
    return f"{findings_count} public investigation records were found for {entity_text}."


def _adapter_for_label(label: str) -> Callable[[str, int], AdapterResult] | None:
    return {
        "email": run_email_lookup,
        "phone": run_phone_lookup,
        "username": run_username_lookup,
        "organization": run_organization_lookup,
    }.get(label)


def enrich_entities(
    entities: list[dict],
    selected_labels: list[str] | None,
    timeout_seconds: int,
    session_id: str,
) -> dict[str, dict]:
    _ = session_id  # reserved for future per-session adapter context
    selected = set(selected_labels or [])
    max_entities = int(os.environ.get("EXTRACTA_OSINT_MAX_ENTITIES", "100"))
    results: dict[str, dict] = {}

    candidates = [
        ent for ent in entities
        if ent.get("label") in SUPPORTED_LABELS and (not selected or ent.get("label") in selected)
    ][:max_entities]

    for ent in candidates:
        ent_id = str(ent["id"])
        label = str(ent["label"])
        text = str(ent["text"])
        adapter = _adapter_for_label(label)
        if adapter is None:
            continue
        adapter_result = adapter(text, timeout_seconds)
        results[ent_id] = {
            "status": adapter_result.status,
            "summary": _entity_summary(text, len(adapter_result.findings)),
            "findings": adapter_result.findings,
            "notes": adapter_result.notes,
        }

    return results
