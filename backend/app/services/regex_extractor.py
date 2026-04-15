from __future__ import annotations

import re

from app.services.ner_engine import ExtractedEntity

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+?\d{1,3}[\s\-.]?)?"
    r"(?:\(?\d{2,4}\)?[\s\-.]?)"
    r"(?:\d[\d\s\-.]{4,}\d)"
    r"(?!\d)"
)

_MALAYSIA_IC_RE = re.compile(
    r"\b(\d{6})-?(\d{2})-?(\d{4})\b"
)

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (_EMAIL_RE, "email"),
    (_MALAYSIA_IC_RE, "ic number"),
    (_PHONE_RE, "phone"),
]


def extract_regex_entities(text: str) -> list[ExtractedEntity]:
    """Extract emails, phone numbers, and Malaysia IC numbers via regex."""
    entities: list[ExtractedEntity] = []
    used_spans: list[tuple[int, int]] = []

    for pattern, label in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()

            overlaps = any(
                not (end <= s or start >= e) for s, e in used_spans
            )
            if overlaps:
                continue

            matched_text = match.group().strip()
            if not matched_text:
                continue

            if label == "phone" and len(re.sub(r"\D", "", matched_text)) < 7:
                continue

            entities.append(
                ExtractedEntity(
                    text=matched_text,
                    label=label,
                    score=1.0,
                    start=start,
                    end=end,
                )
            )
            used_spans.append((start, end))

    return sorted(entities, key=lambda e: e.start)
