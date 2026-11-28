"""
Minimal, dependency-free User-Agent classifier -- used ONLY to label a login session
(device type / operating system / browser) for the per-user activity page.

It is deliberately small and conservative: when a part cannot be recognised it returns
None for that part (the UI then shows it as "not recorded") instead of guessing.
The raw (truncated) User-Agent string is stored next to the parsed parts, so a better
parser can be applied later without losing information.
"""
from __future__ import annotations

import re

MAX_UA_LENGTH = 300

# order matters: the first match wins (Edge/Opera/Samsung/Firefox-iOS all contain "Chrome"/"Safari")
_BROWSERS: list[tuple[str, re.Pattern[str]]] = [
    ("Edge", re.compile(r"\b(?:Edg|EdgA|EdgiOS|Edge)/", re.I)),
    ("Opera", re.compile(r"\b(?:OPR|Opera)/", re.I)),
    ("Samsung Internet", re.compile(r"SamsungBrowser/", re.I)),
    ("Firefox", re.compile(r"\b(?:Firefox|FxiOS)/", re.I)),
    ("Chrome", re.compile(r"\b(?:Chrome|CriOS)/", re.I)),
    ("Safari", re.compile(r"\bSafari/", re.I)),
]
_OS: list[tuple[str, re.Pattern[str]]] = [
    ("Windows", re.compile(r"Windows NT", re.I)),
    ("Android", re.compile(r"Android", re.I)),
    ("iOS", re.compile(r"iPhone|iPad|iPod", re.I)),
    ("macOS", re.compile(r"Mac OS X|Macintosh", re.I)),
    ("ChromeOS", re.compile(r"CrOS", re.I)),
    ("Linux", re.compile(r"Linux|X11", re.I)),
]


def clean_user_agent(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    return raw[:MAX_UA_LENGTH] if raw else None


def parse_user_agent(raw: str | None) -> dict[str, str | None]:
    """-> {"device_type": mobile|tablet|desktop|None, "os": ..., "browser": ...}"""
    ua = clean_user_agent(raw)
    if ua is None:
        return {"device_type": None, "os": None, "browser": None}

    browser = next((name for name, rx in _BROWSERS if rx.search(ua)), None)
    os_name = next((name for name, rx in _OS if rx.search(ua)), None)

    device_type: str | None
    if re.search(r"iPad|Tablet", ua, re.I) or (os_name == "Android" and not re.search(r"Mobile", ua, re.I)):
        device_type = "tablet"
    elif re.search(r"Mobile|iPhone|iPod", ua, re.I):
        device_type = "mobile"
    elif os_name in {"Windows", "macOS", "Linux", "ChromeOS"}:
        device_type = "desktop"
    else:
        device_type = None
    return {"device_type": device_type, "os": os_name, "browser": browser}
