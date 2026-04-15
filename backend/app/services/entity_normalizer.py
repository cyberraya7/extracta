from __future__ import annotations

import re
import uuid
from difflib import SequenceMatcher

from dateutil import parser as date_parser

from app.services.ner_engine import ExtractedEntity

FUZZY_THRESHOLD = 0.85

_CURRENCY_RE = re.compile(
    r"[\$€£¥]\s?[\d,]+(?:\.\d+)?(?:\s?(?:million|billion|thousand|[MBKmk]))?",
)


def normalize_entities(entities: list[ExtractedEntity]) -> list[dict]:
    """Normalize and deduplicate a list of extracted entities.

    Returns a list of dicts with canonical text, label, best score,
    occurrence count, all variants, and all positions.
    """
    groups: dict[str, dict] = {}

    for ent in entities:
        canonical = _find_canonical(ent, groups)

        if canonical:
            group = groups[canonical]
            group["occurrences"] += 1
            group["score"] = max(group["score"], ent.score)
            if ent.text not in group["variants"]:
                group["variants"].append(ent.text)
            group["positions"].append({"start": ent.start, "end": ent.end})
        else:
            normalized_text = _normalize_text(ent.text, ent.label)
            key = normalized_text.lower()
            groups[key] = {
                "id": f"ent_{uuid.uuid4().hex[:8]}_{len(groups)}",
                "text": normalized_text,
                "label": ent.label,
                "score": ent.score,
                "occurrences": 1,
                "variants": [ent.text],
                "positions": [{"start": ent.start, "end": ent.end}],
            }

    return list(groups.values())


def _find_canonical(
    entity: ExtractedEntity, groups: dict[str, dict]
) -> str | None:
    """Find an existing group key this entity belongs to."""
    normalized = _normalize_text(entity.text, entity.label).lower()

    if normalized in groups:
        return normalized

    for key, group in groups.items():
        if group["label"] != entity.label:
            continue

        if _is_fuzzy_match(normalized, key):
            return key

        if _is_abbreviation_match(entity.text, group["text"]):
            return key

    return None


def _is_fuzzy_match(a: str, b: str) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= FUZZY_THRESHOLD


def _is_abbreviation_match(short: str, full: str) -> bool:
    """Check if short is an abbreviation of full (e.g., 'A. Hassan' vs 'Ali Hassan')."""
    short_parts = short.replace(".", "").split()
    full_parts = full.replace(".", "").split()

    if len(short_parts) >= len(full_parts):
        return False

    matched = 0
    for sp in short_parts:
        for fp in full_parts:
            if fp.lower().startswith(sp.lower()):
                matched += 1
                break

    return matched == len(short_parts)


def _normalize_text(text: str, label: str) -> str:
    """Normalize entity text based on its label type."""
    text = text.strip()

    if label == "date":
        return _normalize_date(text)
    if label == "money":
        return _normalize_currency(text)
    if label in ("person", "organization"):
        return _normalize_name(text)

    return text


def _normalize_name(text: str) -> str:
    parts = text.split()
    return " ".join(p.capitalize() for p in parts)


def _normalize_date(text: str) -> str:
    try:
        dt = date_parser.parse(text, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        return text


def _normalize_currency(text: str) -> str:
    cleaned = text.replace(",", "").strip()
    return cleaned
