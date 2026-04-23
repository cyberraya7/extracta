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
        # International (must be explicit country prefix)
        r"(?:\+[1-9]\d{1,3}|00[1-9]\d{1,3})[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}"
    r")"
    r"(?!\d)"
)

# IPv4 (word-boundary style: avoid matching dotted version numbers in prose)
_OCTET = r"(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})"
_DOT = r"(?:\.|\[\.\])"  # defanged dots: 89.117.79[.]31 or 89[.]117[.]79[.]31

# Defanged IPv4 (IOC paste / evasion): same validation after normalizing [.] → .
_IPV4_DEFANGED_RE = re.compile(
    rf"(?<![.\d]){_OCTET}(?:{_DOT}{_OCTET}){{3}}(?![.\d])"
)

# Port after defanged IPv4, e.g. 104[.]18[.]120[.]34:443
_IPV4_DEFANGED_PORT_RE = re.compile(
    rf"(?<![.\d]){_OCTET}(?:{_DOT}{_OCTET}){{3}}:(\d{{1,5}})\b"
)

_IPV4_RE = re.compile(
    r"(?<![.\d])"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})"
    r"(?:\.(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})){3}"
    r"(?![.\d])"
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

# Port after IPv4 only (avoids false positives like times "12:30")
_IPV4_PORT_RE = re.compile(
    r"\b(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})(?:\.(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})){3}:(\d{1,5})\b"
)

_PORT_KW_RE = re.compile(r"(?i)\bport\s*(?:number\s*)?[:#]?\s*(\d{1,5})\b")

_ASN_WORD_RE = re.compile(r"(?i)\bASN\s*[#:]?\s*(\d{1,10})\b")
# Uppercase AS + digits only (avoid matching the English word "as")
_ASN_AS_NUM_RE = re.compile(r"\bAS(\d{2,10})\b")

# Messaging / chat apps (communication platform)
_COMM_PLATFORM_RE = re.compile(
    r"(?i)\b(?:"
    r"WhatsApp|Telegram|Signal|Discord(?:\s+Messenger)?|Slack|"
    r"WeChat|Weixin|LINE(?:\s+Messenger)?|Viber|Google\s+Chat|"
    r"Microsoft\s+Teams|Zoom|Skype|Facebook\s+Messenger"
    r")\b"
)

# Social networks (distinct from messaging apps above)
_SOCIAL_PLATFORM_RE = re.compile(
    r"(?i)\b(?:"
    r"Facebook|Instagram|Twitter|LinkedIn|TikTok|YouTube|Snapchat|"
    r"Pinterest|Reddit|Threads|Bluesky|Mastodon"
    r")\b"
)


def _valid_port(port_str: str) -> bool:
    try:
        p = int(port_str)
    except ValueError:
        return False
    return 1 <= p <= 65535


def _valid_asn(asn_str: str) -> bool:
    try:
        n = int(asn_str)
    except ValueError:
        return False
    return 1 <= n <= 4294967295


def _valid_defanged_ipv4(full_match: str) -> bool:
    normalized = re.sub(r"\[\.\]", ".", full_match.strip())
    octets = normalized.split(".")
    if len(octets) != 4:
        return False
    try:
        nums = [int(o) for o in octets]
    except ValueError:
        return False
    return all(0 <= n <= 255 for n in nums)


# (pattern, label, group_index or None for full match)
_PATTERN_DEFS: list[tuple[re.Pattern[str], str, int | None]] = [
    (_EMAIL_RE, "email", None),
    (_IPV4_DEFANGED_PORT_RE, "port number", 1),
    (_IPV4_PORT_RE, "port number", 1),
    (_IPV4_DEFANGED_RE, "ip address", None),
    (_IPV4_RE, "ip address", None),
    (_MALAYSIA_IC_RE, "ic number", None),
    (_PHONE_RE, "phone", None),
    (_PORT_KW_RE, "port number", 1),
    (_ASN_WORD_RE, "asn number", 1),
    (_ASN_AS_NUM_RE, "asn number", 1),
    (_COMM_PLATFORM_RE, "communication platform", None),
    (_SOCIAL_PLATFORM_RE, "social media platform", None),
]


def extract_regex_entities(text: str) -> list[ExtractedEntity]:
    """Extract structured entities via regex (emails, IPs, ASN, ports, known platform names, etc.)."""
    entities: list[ExtractedEntity] = []
    used_spans: list[tuple[int, int]] = []

    for pattern, label, group_idx in _PATTERN_DEFS:
        for match in pattern.finditer(text):
            if group_idx is None:
                start, end = match.span()
                matched_text = match.group().strip()
            else:
                try:
                    start, end = match.span(group_idx)
                    matched_text = match.group(group_idx).strip()
                except IndexError:
                    continue

            overlaps = any(not (end <= s or start >= e) for s, e in used_spans)
            if overlaps:
                continue

            if not matched_text:
                continue

            if label == "phone" and len(re.sub(r"\D", "", matched_text)) < 7:
                continue

            if label == "port number" and not _valid_port(matched_text):
                continue

            if label == "asn number" and not _valid_asn(matched_text):
                continue

            if label == "ip address" and group_idx is None:
                if "[" in matched_text or "]" in matched_text:
                    if not _valid_defanged_ipv4(matched_text):
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
