"""Marketplace noise stripping and skip-line filters for prose BOM parsers."""

from __future__ import annotations

import re

MARKETPLACE_NOISE = re.compile(
    r"\b(?:Amazon(?:\.\w+)?|AliExpress|eBay|Etsy|DigiKey|Mouser)\b.*$",
    re.I,
)

SKIP_PROSE_LINE = re.compile(
    r"^(?:"
    r"i['']?m\s+using|i\s+am\s+using|see\s+link|buy\s+from|https?://|www\.|"
    r"however|although|that['']?s\s+why|feel\s+free|don['']?t\s+sell|"
    r"now\s+just|please\s+share|come\s+up\s+with|"
    r"can['']?t\s+find\s+a\s+link|local\s+hardware\s+store|"
    r"to\s+summarize|the\s+following|here\s+is\s+a\s+list"
    r")\b",
    re.I,
)


def strip_marketplace_tokens(block: str) -> str:
    """Remove marketplace tokens that break colon-based prose parsing."""
    block = re.sub(r"\bAmazon\.de\b", " ", block, flags=re.I)
    block = re.sub(r"\bAliExpress\s+\d+\b", " ", block, flags=re.I)
    block = re.sub(r"\bDIY\s*&\s*Tools\b", " ", block, flags=re.I)
    return re.sub(r"\s+", " ", block).strip()


def clean_name_and_spec(name: str, specification: str) -> tuple[str, str]:
    name = MARKETPLACE_NOISE.sub("", name).strip(" .,;:-")
    specification = MARKETPLACE_NOISE.sub("", specification).strip()
    if len(name) > 90:
        words = name.split()
        if len(words) > 12:
            specification = name if not specification else f"{name}; {specification}"
            name = " ".join(words[:8]) + "…"
    return name.strip(), specification[:400]


def marketplace_note_suffix(line: str, base_note: str) -> str:
    match = MARKETPLACE_NOISE.search(line)
    if not match:
        return base_note
    return f"{base_note} ({match.group(0).split()[0]})"
