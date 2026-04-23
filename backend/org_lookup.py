#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duckduckgo_html(query: str, timeout: int = 20) -> tuple[bool, str]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return False, str(e)
    return True, data[:6000]


def _opencorporates(org: str, timeout: int = 20) -> tuple[bool, str]:
    # Optional if jq exists; still works without it (raw JSON truncated).
    cmd = [
        "curl",
        "-sS",
        "--max-time",
        str(timeout),
        f"https://api.opencorporates.com/v0.4/companies/search?q={quote_plus(org)}",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as e:
        return False, str(e)
    if p.returncode != 0:
        return False, (p.stderr or p.stdout or "").strip()
    return True, (p.stdout or "").strip()[:6000]


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: org_lookup.py <organization>"}))
        return 1

    org = sys.argv[1].strip()
    findings: list[dict] = []
    notes: list[str] = []

    ok_ddg, out_ddg = _duckduckgo_html(f"{org} company registration number")
    findings.append(
        {
            "title": "Public web records lookup",
            "category": "organization",
            "confidence": 0.55 if ok_ddg else 0.2,
            "attributes": {"source": "provider_a", "ok": ok_ddg, "output": out_ddg},
            "collected_at": _now(),
        }
    )

    ok_oc, out_oc = _opencorporates(org)
    findings.append(
        {
            "title": "Corporate registry lookup",
            "category": "organization",
            "confidence": 0.7 if ok_oc else 0.2,
            "attributes": {"source": "provider_b", "ok": ok_oc, "output": out_oc},
            "collected_at": _now(),
        }
    )
    if not ok_oc:
        notes.append("OpenCorporates request did not return usable data")

    print(
        json.dumps(
            {
                "summary": f"Organization investigation completed for {org}",
                "records": findings,
                "notes": notes,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
