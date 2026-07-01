"""MakerWorld-specific BOM parsers."""

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
from backend.services.parsers.makerworld.embedded import (
    best_attachment,
    find_attachment_urls,
    parts_from_design,
    score_attachment,
)
from backend.services.parsers.makerworld.page_json import extract_design, extract_next_data

__all__ = [
    "DESCRIPTION_NOTE",
    "best_attachment",
    "description_summary",
    "extract_candidate_lines",
    "extract_design",
    "extract_next_data",
    "find_attachment_urls",
    "find_bom_section_lines",
    "html_to_text",
    "merge_parts",
    "normalize_prose",
    "parse_bom_line",
    "parts_from_description",
    "parts_from_design",
    "resolve_description_text",
    "score_attachment",
]
