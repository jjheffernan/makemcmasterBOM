"""HTML and plain-text normalization helpers for BOM parsers."""

from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    """Convert HTML or plain text to normalized plain text with paragraph breaks."""
    raw = unescape(html or "").strip()
    if not raw:
        return ""
    if "<" not in raw:
        return collapse_blank_lines(raw)
    text = BeautifulSoup(raw, "lxml").get_text("\n", strip=True)
    return collapse_blank_lines(text)


def collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def collapse_inline_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()
