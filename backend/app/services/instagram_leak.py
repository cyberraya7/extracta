"""Scan NDJSON Instagram leak dump for email / phone / username matches."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from datetime import datetime, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_leak_path() -> Path:
    return _backend_root() / "Instagram-leak.json"


def leak_file_path() -> Path:
    raw = os.environ.get("EXTRACTA_INSTAGRAM_LEAK_PATH", "").strip()
    if raw:
        p = Path(raw).expanduser()
        return p if p.is_absolute() else (_backend_root() / p)
    return _default_leak_path()


def _normalize_phone(phone: str) -> str:
    """Align with phone_lookup: MY 0… → +60…, strip non-digits except leading +."""
    raw = re.sub(r"[^\d+]", "", phone.strip())
    if raw.startswith("+"):
        return raw
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0"):
        return f"+6{digits}"
    if digits.startswith("60"):
        return f"+{digits}"
    return f"+{digits}" if digits else phone


def _normalize_leak_phone(t: str | None) -> str:
    if not t or not isinstance(t, str):
        return ""
    return _normalize_phone(t.strip())


def scan_instagram_leak(
    label: str,
    entity_text: str,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """
    Stream NDJSON file; return (summary, findings, notes).
    Each finding: InvestigationFinding-shaped dict with attributes.formatted_line and attributes.row.
    """
    path = leak_file_path()
    notes: list[str] = []
    if not path.is_file():
        notes.append("Leak database file is not available on the server.")
        return (
            "No leak database lookup could be performed.",
            [],
            notes,
        )

    label_l = label.lower().strip()
    if label_l not in ("email", "phone", "username"):
        notes.append("Leak lookup is only supported for email, phone, and username.")
        return ("Leak lookup not applicable.", [], notes)

    needle_e = entity_text.strip().lower() if label_l == "email" else ""
    needle_u = entity_text.strip().lower() if label_l == "username" else ""
    needle_p = _normalize_phone(entity_text) if label_l == "phone" else ""

    matches: list[dict[str, Any]] = []

    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue

                hit = False
                if label_l == "email":
                    e = (row.get("e") or "")
                    if isinstance(e, str) and e.strip().lower() == needle_e:
                        hit = True
                elif label_l == "username":
                    u = (row.get("u") or "")
                    if isinstance(u, str) and u.strip().lower() == needle_u:
                        hit = True
                elif label_l == "phone":
                    t_raw = row.get("t")
                    if isinstance(t_raw, str) and t_raw.strip():
                        t_norm = _normalize_leak_phone(t_raw)
                        if t_norm == needle_p or t_raw.strip() == entity_text.strip():
                            hit = True

                if hit:
                    matches.append(row)
    except OSError as e:
        notes.append(f"Could not read leak database: {e!s}")
        return ("Leak database read failed.", [], notes)

    collected_at = _utc_now()
    findings: list[dict[str, Any]] = []
    display_label = label  # e.g. "email", "phone", "username"

    for row in matches:
        row_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
        formatted = f"{display_label} was found in instagram leak: {row_json}"
        findings.append(
            {
                "title": "Leak database match",
                "category": label_l,
                "confidence": 0.95,
                "attributes": {
                    "formatted_line": formatted,
                    "row": row,
                },
                "collected_at": collected_at,
            }
        )

    if not findings:
        return (
            f"No leak database matches were found for {entity_text}.",
            [],
            notes,
        )

    n = len(findings)
    summary = (
        f"Found {n} leak database match{'es' if n != 1 else ''} for {entity_text}."
        if n > 1
        else f"Found one leak database match for {entity_text}."
    )
    return (summary, findings, notes)
