#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], timeout: int = 60) -> tuple[bool, str]:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as e:
        return False, str(e)
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        return False, err or out or f"exit_code={p.returncode}"
    return True, out


def _normalize_msisdn(phone: str) -> str:
    raw = re.sub(r"[^\d+]", "", phone.strip())
    if raw.startswith("+"):
        return raw
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0"):
        # Malaysia local format (0xxxxxxxxx -> +60xxxxxxxxx)
        return f"+6{digits}"
    if digits.startswith("60"):
        return f"+{digits}"
    return f"+{digits}" if digits else phone


def _extract_telegram_matches(raw_output: str) -> list[dict]:
    text = (raw_output or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        candidates: list[object]
        if isinstance(parsed, list):
            candidates = parsed
        elif isinstance(parsed, dict):
            if isinstance(parsed.get("results"), list):
                candidates = parsed["results"]
            else:
                # telegram-phone-number-checker commonly returns:
                # {"+6012...": {...user fields...}}
                # Convert keyed mapping to a list preserving queried phone.
                keyed_rows: list[dict] = []
                for k, v in parsed.items():
                    if isinstance(v, dict):
                        row = dict(v)
                        row.setdefault("queried_phone", str(k))
                        keyed_rows.append(row)
                candidates = keyed_rows or [parsed]
        else:
            candidates = []

        out: list[dict] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            # Treat checker "error-only" records as not found.
            # Example: {"error": "No response, the phone number is not on Telegram ..."}
            if "error" in item and not any(k in item for k in ("id", "user_id", "username", "first_name", "last_name", "phone")):
                continue
            row: dict[str, str] = {}
            username = item.get("username") or item.get("telegram_username")
            full_name = (
                item.get("name")
                or item.get("full_name")
                or " ".join(
                    x for x in [item.get("first_name"), item.get("last_name")] if isinstance(x, str) and x.strip()
                ).strip()
            )
            user_id = item.get("id") or item.get("user_id")
            status = item.get("status") or item.get("result")
            was_online = item.get("user_was_online")
            queried_phone = item.get("queried_phone") or item.get("phone")
            if username:
                row["username"] = str(username)
            if full_name:
                row["name"] = str(full_name)
            if user_id:
                row["id"] = str(user_id)
            if was_online:
                row["last_seen"] = str(was_online)
            if queried_phone:
                row["phone"] = str(queried_phone)
            if status and not row:
                row["status"] = str(status)
            if row:
                out.append(row)
        return out
    except json.JSONDecodeError:
        return []


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: phone_lookup.py <phone>"}))
        return 1

    phone = sys.argv[1].strip()
    normalized_phone = _normalize_msisdn(phone)
    findings: list[dict] = []
    notes: list[str] = []

    checker_bin = shutil.which("telegram-phone-number-checker")
    if not checker_bin:
        notes.append("telegram-phone-number-checker not found on PATH")
    else:
        fd, out_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            ok, output = _run([checker_bin, "--phone-numbers", normalized_phone, "--output", out_path])
            file_payload = ""
            if os.path.isfile(out_path):
                try:
                    with open(out_path, encoding="utf-8", errors="replace") as f:
                        file_payload = f.read().strip()
                except OSError:
                    file_payload = ""
            payload = file_payload or output
            matches = _extract_telegram_matches(payload)
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass
        found = len(matches) > 0
        findings.append(
            {
                "title": "Telegram account lookup",
                "category": "phone",
                "confidence": 0.8 if found else (0.55 if ok else 0.2),
                "attributes": {
                    "normalized_phone": normalized_phone,
                    "telegram_found": found,
                    "telegram_matches": matches,
                },
                "collected_at": _now(),
            }
        )
        if not ok and not found:
            notes.append("Telegram checker returned no usable records.")

    print(
        json.dumps(
            {
                "summary": (
                    f"Telegram account details found for {normalized_phone}."
                    if findings and findings[0]["attributes"].get("telegram_found")
                    else f"No Telegram account details found for {normalized_phone}."
                ),
                "records": findings,
                "notes": notes,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
