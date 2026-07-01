"""MakerWorld __NEXT_DATA__ page JSON extraction."""

from __future__ import annotations

import json
import re
from typing import Any

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    re.DOTALL,
)


def extract_next_data(html: str) -> dict[str, Any] | None:
    match = NEXT_DATA_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def extract_design(next_data: dict[str, Any]) -> dict[str, Any] | None:
    design = next_data.get("props", {}).get("pageProps", {}).get("design")
    return design if isinstance(design, dict) else None
