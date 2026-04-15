from __future__ import annotations

import re

from app.services.ner_engine import ExtractedEntity

_EMAIL_RE = re.compile(
    r"\b"
    r"(?![._%+\-])"                         # no leading special char
    r"[A-Za-z0-9._%+\-]{1,64}"              # local part
    r"(?<![._%+\-])"                        # no trailing special char
    r"@"
    r"(?:[A-Za-z0-9-]+\.)+"                 # domain labels
    r"[A-Za-z]{2,24}"                       # TLD
    r"\b"
)

_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:"
        # Malaysia mobile
        r"(?:\+?60|0)1[0-46-9][\s\-]?\d{3,4}[\s\-]?\d{3,4}"
        r"|"
        # Malaysia landline
        r"(?:\+?60|0)[3-9][\s\-]?\d{3,4}[\s\-]?\d{3,4}"
        r"|"
        # International (structured)
        r"\+?[1-9]\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}"
        r"|"
        # Loose fallback (OSINT / messy text)
        r"\+?\d[\d\-\s()]{6,}\d"
    r")"
    r"(?!\d)"
)

_MALAYSIA_IC_RE = re.compile(
    r"\b"
    r"(?:"
        # YYMMDD (basic date validation)
        r"(?:\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01]))"
        r"-?"
        # State code (01–16, 21–24, 71–72)
        r"(?:0[1-9]|1[0-6]|2[1-4]|7[1-2])"
        r"-?"
        # Last 4 digits
        r"\d{4}"
    r")"
    r"\b"
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
