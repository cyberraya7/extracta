#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], timeout: int = 90) -> tuple[bool, str]:
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


def _extract_registered_sites(raw_output: str) -> list[str]:
    sites: list[str] = []
    text = (raw_output or "").strip()
    if not text:
        return sites

    # Remove ANSI color/control codes if present.
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)

    # Prefer JSON payloads when possible.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                if item.get("exists") is True:
                    name = item.get("name") or item.get("domain") or item.get("website")
                    if isinstance(name, str) and name.strip():
                        sites.append(name.strip())
        elif isinstance(parsed, dict):
            # Some versions return {"sites":[...]} or keyed dictionaries.
            # Common list containers seen across versions/tools.
            for list_key in ("sites", "services", "results", "accounts"):
                site_list = parsed.get(list_key)
                if isinstance(site_list, list):
                    for item in site_list:
                        if isinstance(item, dict) and item.get("exists") is True:
                            name = (
                                item.get("name")
                                or item.get("domain")
                                or item.get("website")
                                or item.get("site")
                                or item.get("service")
                            )
                            if isinstance(name, str) and name.strip():
                                sites.append(name.strip())

            # Keyed dict fallback: {"twitter": {"exists": true, ...}, ...}
            for key, value in parsed.items():
                if not isinstance(value, dict):
                    continue
                if value.get("exists") is True:
                    name = value.get("name") or key
                    if isinstance(name, str) and name.strip():
                        sites.append(name.strip())
    except json.JSONDecodeError:
        # If output includes logs + JSON, try extracting the JSON segment.
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            try:
                return _extract_registered_sites(text[start_obj : end_obj + 1])
            except Exception:
                pass

    if sites:
        return sorted(set(sites), key=str.lower)

    # Strong fallback: extract all Holehe "[+] domain" occurrences anywhere in output.
    plus_domain_matches = re.findall(r"\[\+\]\s*([A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    if plus_domain_matches:
        return sorted(set(plus_domain_matches), key=str.lower)

    # Fallback for plain text output lines (best effort).
    # Holehe classic output example:
    # [+] firefox.com
    # [+] twitter.com
    for line in text.splitlines():
        ln = line.strip()
        if not ln:
            continue
        if ln.startswith("[+] "):
            candidate = ln[4:].strip()
            lower_candidate = candidate.lower()
            # Skip legend and non-site lines.
            if (
                not candidate
                or "email used" in lower_candidate
                or "websites checked" in lower_candidate
                or lower_candidate.startswith("twitter :")
                or lower_candidate.startswith("github :")
                or lower_candidate.startswith("for btc")
            ):
                continue
            sites.append(candidate)
            continue
        lowered = ln.lower()
        if "exists" in lowered or "found" in lowered or "true" in lowered or "registered" in lowered:
            candidate = ln.replace("[+]", "").replace("[*]", "").strip(" -:\t")
            if candidate:
                sites.append(candidate)
    return sorted(set(sites), key=str.lower)


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: email_lookup.py <email>"}))
        return 1

    email = sys.argv[1].strip()
    notes: list[str] = []
    registered_sites: list[str] = []

    if shutil.which("holehe"):
        ok, output = _run(["holehe", email, "--only-used"])
        registered_sites = _extract_registered_sites(output)
        if not registered_sites and not ok:
            notes.append("Holehe returned no usable output.")
    else:
        notes.append("holehe not found on PATH")

    if registered_sites:
        summary = "This email has been registered on these websites."
    else:
        summary = "No registered websites found for this email."

    print(
        json.dumps(
            {
                "summary": summary,
                "registered_sites": registered_sites,
                "notes": notes,
                "collected_at": _now(),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
