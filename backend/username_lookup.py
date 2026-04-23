#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], timeout: int = 120) -> tuple[bool, str]:
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


def _extract_found_sites(raw_output: str) -> list[str]:
    text = (raw_output or "").strip()
    if not text:
        return []

    # Remove ANSI control sequences if any.
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)

    sites: list[str] = []
    try:
        parsed = json.loads(text)
        # Generic object/list walk: gather plausible site/url fields.
        def walk(obj: object) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    key = str(k).lower()
                    if key in {"site", "domain", "host", "url", "website", "platform"} and isinstance(v, str):
                        value = v.strip()
                        if value:
                            sites.append(value)
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(parsed)
    except json.JSONDecodeError:
        pass

    def is_low_value(value: str) -> bool:
        lowered = value.lower()
        if lowered.endswith((".json", ".csv", ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return True
        noisy_hosts = (
            "tiktokcdn.com/",
            "pbs.twimg.com/",
            "yt3.googleusercontent.com/",
            "rbxcdn.com/",
        )
        return any(host in lowered for host in noisy_hosts)

    if sites:
        # Normalize URLs to host-ish display while preserving originals if already simple.
        normalized: list[str] = []
        for s in sites:
            value = s.strip()
            value = re.sub(r"^https?://", "", value, flags=re.I)
            value = value.rstrip("/")
            if value and not is_low_value(value):
                normalized.append(value)
        return sorted(set(normalized), key=str.lower)

    # Text fallback: catch URL/domain-like tokens and drop obvious local filenames.
    candidates = re.findall(r"(https?://[^\s]+|[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    if not candidates:
        return []
    normalized = []
    for c in candidates:
        val = re.sub(r"^https?://", "", c, flags=re.I).rstrip("/")
        if val and not is_low_value(val):
            normalized.append(val)
    return sorted(set(normalized), key=str.lower)


def _extract_report_file(raw_output: str) -> str:
    text = (raw_output or "").strip()
    if not text:
        return ""
    match = re.search(r"saved in\s+(.+report_[^\s]+_simple\.json)", text)
    if not match:
        return ""
    candidate = match.group(1).strip().strip("'\"")
    return candidate if os.path.isfile(candidate) else ""


def _is_low_value_url(value: str) -> bool:
    lowered = value.lower()
    if lowered.endswith((".json", ".csv", ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return True
    noisy_hosts = (
        "tiktokcdn.com/",
        "pbs.twimg.com/",
        "yt3.googleusercontent.com/",
        "rbxcdn.com/",
        "paypalobjects.com/",
    )
    return any(host in lowered for host in noisy_hosts)


def _extract_maigret_profiles(raw_output: str) -> tuple[list[str], list[dict]]:
    text = (raw_output or "").strip()
    if not text:
        return [], []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [], []
    if not isinstance(parsed, dict):
        return [], []

    found_sites: list[str] = []
    profiles: list[dict] = []
    for site_name, site_data in parsed.items():
        if not isinstance(site_data, dict):
            continue
        status = site_data.get("status")
        if not isinstance(status, dict):
            continue
        if str(status.get("status", "")).lower() != "claimed":
            continue
        url = str(status.get("url") or site_data.get("url_user") or "").strip()
        if not url:
            continue
        normalized_url = re.sub(r"^https?://", "", url, flags=re.I).rstrip("/")
        if normalized_url and not _is_low_value_url(normalized_url):
            found_sites.append(normalized_url)

        ids = status.get("ids")
        detail_map: dict[str, str] = {}
        if isinstance(ids, dict):
            for key, val in ids.items():
                key_text = str(key).strip()
                if not key_text:
                    continue
                if isinstance(val, (str, int, float, bool)):
                    value_text = str(val).strip()
                    if not value_text or value_text.lower() in {"none", "null"}:
                        continue
                    if len(value_text) > 400:
                        continue
                    detail_map[key_text] = value_text
        profiles.append(
            {
                "site": str(site_name),
                "url": url,
                "details": detail_map,
            }
        )

    dedup_sites = sorted(set(found_sites), key=str.lower)
    return dedup_sites, profiles


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: username_lookup.py <username>"}))
        return 1

    username = sys.argv[1].strip()
    notes: list[str] = []
    found_sites: list[str] = []
    site_profiles: list[dict] = []

    maigret_cmd = os.environ.get("EXTRACTA_MAIGRET_CMD", "").strip()
    legacy_cmd = os.environ.get("EXTRACTA_BLACKBIRD_CMD", "").strip()
    tool_cmd = maigret_cmd or legacy_cmd

    if not tool_cmd:
        notes.append("username tool command is not configured.")
    else:
        has_value_placeholder = "{value}" in tool_cmd
        has_output_placeholder = "{output}" in tool_cmd
        # Run via shell string for easier command templating.
        fd, out_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            if has_value_placeholder or has_output_placeholder:
                full_cmd = tool_cmd.format(value=username, output=out_path)
            else:
                # Default Maigret style: machine-readable output to stdout.
                full_cmd = f"{tool_cmd} \"{username}\" --json simple"
            ok, output = _run(["bash", "-lc", full_cmd], timeout=240)

            file_payload = ""
            if os.path.isfile(out_path):
                try:
                    with open(out_path, encoding="utf-8", errors="replace") as f:
                        file_payload = f.read().strip()
                except OSError:
                    file_payload = ""

            report_file = _extract_report_file(output)
            report_payload = ""
            if report_file:
                try:
                    report_payload = Path(report_file).read_text(encoding="utf-8", errors="replace").strip()
                except OSError:
                    report_payload = ""

            payload = report_payload or file_payload or output
            found_sites, site_profiles = _extract_maigret_profiles(payload)
            if not found_sites:
                found_sites = _extract_found_sites(payload)
            if not ok and not found_sites:
                notes.append("username checker returned no usable records.")
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass

    summary = (
        f"This username was found on {len(found_sites)} website(s)."
        if found_sites
        else "No username matches found on checked websites."
    )

    print(
        json.dumps(
            {
                "summary": summary,
                "found_sites": found_sites,
                "site_profiles": site_profiles,
                "normalized_username": username,
                "notes": notes,
                "collected_at": _now(),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
