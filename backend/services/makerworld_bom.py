"""Backward-compatible re-exports — prefer backend.services.parsers.makerworld."""

from backend.services.parsers.makerworld.embedded import (
    best_attachment,
    find_attachment_urls,
    parts_from_design,
    score_attachment,
)
from backend.services.parsers.makerworld.page_json import extract_design, extract_next_data

__all__ = [
    "best_attachment",
    "extract_design",
    "extract_next_data",
    "find_attachment_urls",
    "parts_from_design",
    "score_attachment",
]
