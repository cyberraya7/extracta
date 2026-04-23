from __future__ import annotations

import json
import logging
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from os import getenv

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    status: str
    findings: list[dict]
    notes: list[str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_log_value(value: str) -> str:
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}***{value[-2:]}"


def _run_command_template(command_template: str, value: str, timeout_seconds: int) -> tuple[str, str]:
    if not command_template.strip():
        return "", ""
    cmd = command_template.format(value=value)
    args = shlex.split(cmd)
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        logger.info("OSINT provider command failed for %s", _safe_log_value(value))
        return "", stderr[:500]
    return stdout, ""


def _parse_finding_payload(stdout: str, category: str) -> list[dict]:
    if not stdout:
        return []
    collected_at = _utc_now()
    try:
        parsed = json.loads(stdout)
        if isinstance(parsed, list):
            return [
                {
                    "title": "Public record match",
                    "category": category,
                    "confidence": 0.6,
                    "attributes": {"result": item} if not isinstance(item, dict) else item,
                    "collected_at": collected_at,
                }
                for item in parsed[:10]
            ]
        if isinstance(parsed, dict):
            sites = parsed.get("registered_sites")
            if isinstance(sites, list):
                normalized_sites = [
                    str(site).strip()
                    for site in sites
                    if isinstance(site, (str, int, float)) and str(site).strip()
                ]
                return [
                    {
                        "title": "Registered websites",
                        "category": category,
                        "confidence": 0.75 if normalized_sites else 0.55,
                        "attributes": {
                            "registered_sites": normalized_sites,
                        },
                        "collected_at": _json_safe_timestamp(parsed.get("collected_at"), collected_at),
                    }
                ]
            found_sites = parsed.get("found_sites")
            if isinstance(found_sites, list):
                normalized_sites = [
                    str(site).strip()
                    for site in found_sites
                    if isinstance(site, (str, int, float)) and str(site).strip()
                ]
                attrs: dict[str, object] = {
                    "found_sites": normalized_sites,
                }
                site_profiles = parsed.get("site_profiles")
                if isinstance(site_profiles, list):
                    attrs["site_profiles"] = site_profiles[:20]
                normalized_username = parsed.get("normalized_username")
                if isinstance(normalized_username, str) and normalized_username.strip():
                    attrs["normalized_username"] = normalized_username.strip()
                return [
                    {
                        "title": "Username matches",
                        "category": category,
                        "confidence": 0.75 if normalized_sites else 0.55,
                        "attributes": attrs,
                        "collected_at": _json_safe_timestamp(parsed.get("collected_at"), collected_at),
                    }
                ]
            records = parsed.get("records")
            if isinstance(records, list) and records:
                first = records[0] if isinstance(records[0], dict) else {}
                attrs = first.get("attributes") if isinstance(first, dict) else {}
                if isinstance(attrs, dict) and isinstance(attrs.get("telegram_matches"), list):
                    return [
                        {
                            "title": str(first.get("title") or "Telegram account lookup"),
                            "category": category,
                            "confidence": float(first.get("confidence") or 0.75),
                            "attributes": attrs,
                            "collected_at": _json_safe_timestamp(first.get("collected_at"), collected_at),
                        }
                    ]
            return [
                {
                    "title": "Public record match",
                    "category": category,
                    "confidence": 0.6,
                    "attributes": parsed,
                    "collected_at": collected_at,
                }
            ]
    except json.JSONDecodeError:
        pass

    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()][:10]
    return [
        {
            "title": "Public record match",
            "category": category,
            "confidence": 0.5,
            "attributes": {"line": ln},
            "collected_at": collected_at,
        }
        for ln in lines
    ]


def _json_safe_timestamp(value: object, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return fallback


def run_email_lookup(email: str, timeout_seconds: int) -> AdapterResult:
    """Legacy / batch OSINT: prefer sites command, fall back to EXTRACTA_OSINT_EMAIL_CMD."""
    cmd = getenv("EXTRACTA_OSINT_EMAIL_SITES_CMD", "") or getenv("EXTRACTA_OSINT_EMAIL_CMD", "")
    return _run_lookup(cmd, email, "email", timeout_seconds)


def run_email_registered_sites(email: str, timeout_seconds: int) -> AdapterResult:
    cmd = getenv("EXTRACTA_OSINT_EMAIL_SITES_CMD", "") or getenv("EXTRACTA_OSINT_EMAIL_CMD", "")
    return _run_lookup(cmd, email, "email", timeout_seconds)


def run_phone_lookup(phone: str, timeout_seconds: int) -> AdapterResult:
    cmd = getenv("EXTRACTA_OSINT_PHONE_CMD", "")
    return _run_lookup(cmd, phone, "phone", timeout_seconds)


def run_username_lookup(username: str, timeout_seconds: int) -> AdapterResult:
    cmd = getenv("EXTRACTA_OSINT_USERNAME_CMD", "")
    return _run_lookup(cmd, username, "username", timeout_seconds)


def run_organization_lookup(organization: str, timeout_seconds: int) -> AdapterResult:
    cmd = getenv("EXTRACTA_OSINT_ORG_CMD", "")
    return _run_lookup(cmd, organization, "organization", timeout_seconds)


def _run_lookup(command_template: str, value: str, category: str, timeout_seconds: int) -> AdapterResult:
    if not command_template.strip():
        return AdapterResult(status="not_configured", findings=[], notes=["Investigation source is not configured."])
    try:
        stdout, stderr = _run_command_template(command_template, value, timeout_seconds)
    except subprocess.TimeoutExpired:
        return AdapterResult(status="failed", findings=[], notes=["Investigation timed out."])
    except Exception:
        logger.exception("OSINT provider execution failed for %s", category)
        return AdapterResult(status="failed", findings=[], notes=["Investigation failed due to runtime error."])

    combined = (stdout or "").strip()
    if not combined and stderr:
        return AdapterResult(
            status="partial",
            findings=[],
            notes=[stderr[:500] if stderr else "Investigation source returned no usable records."],
        )

    findings = _parse_finding_payload(combined, category)
    notes: list[str] = []
    if stderr and not findings:
        notes.append(stderr[:500])
    if not findings:
        return AdapterResult(
            status="completed",
            findings=[],
            notes=notes or ["No public records found."],
        )
    return AdapterResult(status="completed", findings=findings, notes=notes)
