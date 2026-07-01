"""Backward-compatible re-exports — prefer backend.services.parsers.makerworld.description."""

from backend.services.parsers.makerworld.description import *  # noqa: F403
from backend.services.parsers.makerworld.description import (
    DESCRIPTION_NOTE,
    description_summary,
    extract_candidate_lines,
    find_bom_section_lines,
    html_to_text,
    merge_parts,
    normalize_prose,
    parse_bom_line,
    parts_from_description,
    resolve_description_text,
)

__all__ = [
    "DESCRIPTION_NOTE",
    "description_summary",
    "extract_candidate_lines",
    "find_bom_section_lines",
    "html_to_text",
    "merge_parts",
    "normalize_prose",
    "parse_bom_line",
    "parts_from_description",
    "resolve_description_text",
]
