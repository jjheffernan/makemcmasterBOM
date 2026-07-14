"""MakerWorld project description BOM parser (rule-based, no AI)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.models.part import Part
from backend.services.parsers.helpers.bom_line import parse_hardware_line
from backend.services.parsers.helpers.bom_sections import find_section_lines
from backend.services.parsers.helpers.hardware_signals import has_hardware_signal
from backend.services.parsers.helpers.html_text import (
    collapse_blank_lines,
    collapse_inline_whitespace,
    html_to_text,
)
from backend.services.parsers.helpers.marketplace import strip_marketplace_tokens
from backend.services.parsers.helpers.parts_merge import merge_parts

DESCRIPTION_NOTE = "MakerWorld BOM (description)"

SECTION_START = re.compile(
    r"^(?:"
    r"bom|bill\s+of\s+materials(?:\s*\(bom\))?|parts(?:\s+list)?|hardware(?:\s+list)?|"
    r"materials?(?:\s+required|\s+needed|\s+list)?|shopping\s+list|"
    r"components?(?:\s+required|\s+needed|\s+list)?|"
    r"supplies(?:\s+list)?|fasteners(?:\s+needed|\s+list)?|"
    r"you\s+will\s+need|tools?\s+(?:and\s+)?materials?|"
    r"parts?\s+you\s+need|required\s+(?:parts?|materials?|hardware)|"
    r"non[-\s]?printed\s+parts?|additional\s+parts?"
    r")\s*:?\s*$",
    re.I,
)

SECTION_STOP = re.compile(
    r"^(?:"
    r"settings?|print\s+settings?|assembl(?:y|ing)|instructions?|"
    r"printing|support|license|licence|features?|key[-\s]?features?|"
    r"reason|background|overview|credits?|thanks|note|next\s+steps|"
    r"downloads?|files?|make\s+notes?|tips?|personalization|tools?|"
    r"applications?"
    r")\s*:?\s*$",
    re.I,
)

INLINE_PARTS_BLOCK = re.compile(
    r"\bParts\s*:\s*(.+?)"
    r"(?=\b(?:Personalization|Assembly\s+Tips?|Tools\s+Pro[-\s]?Tip|"
    r"Pro[-\s]?Tip|Support|License|Download|Make\s+notes?)\b|$)",
    re.I | re.S,
)

PROSE_ITEM_START = re.compile(
    r"(?:^|(?<=\s))(?:"
    r"M\d+x?\s*screws?\s+\d+mm|"
    r"M\d[^:]{0,40}(?:heat\s+inserts?|screws?)|"
    r"PC\s+screws(?:\s+and\s+mainboard\s+standoffs)?|"
    r"Tubes?\s+\d[\d/]*mm|"
    r"Carbon\s+Fiber\s+Tube|"
    r"Power\s+Button[^:]{0,48}|"
    r"Front\s+IO\s+Panel(?:\s+[^\s:(]+){0,6}|"
    r"Magnets?\s*\(\d+x\d+\)|"
    r"Acrly[^:]{4,}|Acrylic[^:]{4,}|"
    r"\d+mm"
    r")",
    re.I,
)

PROSE_PCS_TERMINATOR = re.compile(
    r":\s*(?:min\s+)?(\d+(?:/\d+)?)\s*pcs(?:\s*(\([^)]*\)))?",
    re.I,
)

PROSE_NAMED_ITEM = re.compile(
    r"((?:"
    r"M\d[^:]{4,}(?:heat\s+insert|insert)|"
    r"PC\s+screws[^:]{4,}|"
    r"Acrly[^:]{4,}|Acrylic[^:]{4,}"
    r"))\s*:\s*(.+?)(?="
    r"\s+(?:M\d|Tubes?\s|Magnets?\s*\(|Power\s+Button|Front\s+IO|PC\s+screws|Acrly|Personalization)\b|$)",
    re.I | re.S,
)


def normalize_prose(text: str) -> str:
    """Fix run-on MakerWorld description text before parsing."""
    text = html_to_text(text)
    if not text:
        return ""

    text = _split_inline_bom_headers(text)
    text = _split_glued_section_headers(text)

    text = re.sub(r"([a-z])(Parts:)", r"\1 \2", text, flags=re.I)
    text = re.sub(r"(Parts:)(\S)", r"\1 \2", text, flags=re.I)
    text = re.sub(r"screws(\d)", r"screws \1", text, flags=re.I)
    text = re.sub(r"(\d)mm:", r"\1mm:", text)
    text = re.sub(r"mountsif\b", "mounts if", text, flags=re.I)
    text = re.sub(r"dimensionYou\b", "dimension You", text, flags=re.I)
    text = re.sub(r"PersonalizationThis\b", "Personalization This", text, flags=re.I)
    text = re.sub(r"joint\.Parts:", "joint.\nParts:", text, flags=re.I)

    for label in (
        "Parts",
        "Tools",
        "Tools Pro-Tip",
        "Pro-Tip",
        "Assembly Tips",
        "Personalization",
    ):
        text = re.sub(rf"(?<=[.!?])\s*({label})\s*:", rf"\n\1:", text, flags=re.I)
        text = re.sub(rf"\b({label})\s*:", rf"\n\1:\n", text, flags=re.I)

    text = collapse_inline_whitespace(text)
    return collapse_blank_lines(text)


def _split_inline_bom_headers(text: str) -> str:
    """Break inline BOM headers onto their own lines (with or without a colon)."""
    text = re.sub(
        r"(?<=\S)\s+(?=(?:bill\s+of\s+materials(?:\s*\(bom\))?|bom)\s*:?)",
        "\n",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"(?<=[.!?])\s*(bill\s+of\s+materials(?:\s*\(bom\))?)\s*:?\s*",
        r"\n\1\n",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"(bill\s+of\s+materials(?:\s*\(bom\))?)\s*:?\s*(?=\S)",
        r"\n\1\n",
        text,
        flags=re.I,
    )
    out: list[str] = []
    header_with_items = re.compile(
        r"^(?P<header>(?:bill\s+of\s+materials(?:\s*\(bom\))?|bom))\s*:\s*(?P<items>.+)$",
        re.I,
    )
    for line in text.splitlines():
        stripped = line.strip()
        match = header_with_items.match(stripped)
        if match:
            out.append(match.group("header"))
            out.append(match.group("items").strip())
        else:
            out.append(line)
    return "\n".join(out)


def _split_glued_section_headers(text: str) -> str:
    """Split MakerWorld section titles glued to the following paragraph (BOM pages)."""
    if not re.search(r"bill\s+of\s+materials(?:\s*\(bom\))?|\bbom\b", text, re.I):
        return text
    for label in (
        "Overview",
        "Applications",
        "Settings",
        "Assembly",
        "Printing",
        "License",
        "Features",
        "Key-Features",
    ):
        text = re.sub(rf"\b({label})(?=[A-Z])", r"\n\1\n", text)
    return text


GLUED_PRODUCT_NAME = re.compile(r"(?<=\bCard)(?=[A-Z])")
HARDWARE_BUNDLE_SPLIT = re.compile(
    r"(?<=[a-zA-Z)])(?=\d+\s+(?:M\d|18650))",
)
METRIC_QTY_ITEM = re.compile(r"\d+\s+M\d")
URL_ONLY_LINE = re.compile(r"^-?\s*https?://\S+$", re.I)


def _split_metric_hardware_runs(line: str) -> list[str]:
    if len(METRIC_QTY_ITEM.findall(line)) < 2:
        return [line]
    return [part.strip() for part in re.split(r"(?<=\S)\s+(?=\d+\s+M\d)", line) if part.strip()]


def _expand_runon_bom_line(line: str) -> list[str]:
    """Split a single run-on MakerWorld BOM line into item rows."""
    if "\xa0" in line or "\u00a0" in line:
        chunks = [part.strip() for part in re.split(r"[\xa0\u00a0]+", line) if part.strip()]
    else:
        chunks = [line.strip()] if line.strip() else []

    expanded: list[str] = []
    for chunk in chunks:
        chunk = GLUED_PRODUCT_NAME.sub("\n", chunk)
        for piece in chunk.splitlines():
            piece = piece.strip()
            if not piece:
                continue
            for part in HARDWARE_BUNDLE_SPLIT.split(piece):
                part = part.strip()
                if part:
                    expanded.extend(_split_metric_hardware_runs(part))

    if not expanded:
        return [line.strip()] if line.strip() else []

    merged: list[str] = []
    for chunk in expanded:
        if URL_ONLY_LINE.match(chunk):
            if merged:
                merged[-1] = f"{merged[-1]} {chunk.lstrip('- ').strip()}"
            continue
        merged.append(chunk)
    return merged


def _section_line_needs_expand(line: str) -> bool:
    return bool(
        len(line) > 120
        or "\xa0" in line
        or "\u00a0" in line
        or len(re.findall(r"\bpcs\b", line, re.I)) > 1
        or len(METRIC_QTY_ITEM.findall(line)) > 1
        or GLUED_PRODUCT_NAME.search(line)
        or HARDWARE_BUNDLE_SPLIT.search(line)
    )


def _expand_section_line(line: str) -> list[str]:
    """Expand long or run-on section lines."""
    if len(line) > 120 or len(re.findall(r"\bpcs\b", line, re.I)) > 1:
        inline = _extract_inline_parts_chunks(f"Parts: {line}")
        if inline:
            return inline
        expanded = _expand_runon_bom_line(line)
        if expanded and (len(expanded) > 1 or expanded[0] != line):
            return expanded
        return []

    expanded = _expand_runon_bom_line(line)
    return expanded or [line]


def _expand_section_line_gate(line: str) -> list[str]:
    if _section_line_needs_expand(line) or len(line) > 120:
        return _expand_section_line(line)
    return [line]


def resolve_description_text(soup_description: str, design: dict | None) -> str:
    """Pick the richest description source and return plain text for display."""
    candidates: list[str] = []
    if soup_description.strip():
        candidates.append(soup_description.strip())
    if design:
        for key in ("summary", "description", "detail", "content"):
            value = design.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())
    if not candidates:
        return ""
    richest = max(candidates, key=lambda c: len(html_to_text(c)))
    return normalize_prose(richest)


def description_summary(text: str, max_len: int = 220) -> str:
    """Short preview for UI — omit embedded Parts prose."""
    normalized = normalize_prose(text)
    if not normalized:
        return ""
    before_parts = re.split(r"\bParts\s*:", normalized, maxsplit=1, flags=re.I)[0].strip()
    preview = before_parts or normalized
    if len(preview) > max_len:
        return preview[: max_len - 1].rstrip() + "…"
    return preview


def _last_item_segment(name_part: str) -> str:
    name_part = name_part.strip()
    if not name_part:
        return ""

    screw_mm = re.search(r"M\d+x?\s*screws?\s+\d+mm", name_part, re.I)
    if screw_mm:
        return screw_mm.group(0).strip()

    starts = [m.start() for m in PROSE_ITEM_START.finditer(name_part)]
    if starts:
        return name_part[starts[-1] :].strip()
    return name_part


def _extract_pcs_chunks(block: str) -> list[str]:
    chunks: list[str] = []
    pos = 0
    for m in PROSE_PCS_TERMINATOR.finditer(block):
        name = _last_item_segment(block[pos : m.start()])
        if not name:
            pos = m.end()
            continue
        qty = m.group(1)
        entry = f"{name}: {qty}pcs"
        if m.group(2):
            entry = f"{entry} {m.group(2)}"
        chunks.append(entry.strip())
        pos = m.end()
    return chunks


def _clean_chunk_name(name: str) -> str:
    name = re.sub(
        r"^(?:DIY\s*&\s*Tools\s*|AliExpress\s*\d+\s*|Amazon\.de\s*|xpress\s*\d+\s*)",
        "",
        name,
        flags=re.I,
    )
    name = re.sub(
        r"^min\s+\d+pcs\s*\([^)]*\)\s*",
        "",
        name,
        flags=re.I,
    )
    name = re.sub(r"^r\s+Hand\b", "Hand", name, flags=re.I)
    return collapse_inline_whitespace(name).strip(" .,;:-")


def _extract_inline_parts_chunks(text: str) -> list[str]:
    match = INLINE_PARTS_BLOCK.search(text)
    if not match:
        return []

    block = strip_marketplace_tokens(collapse_inline_whitespace(match.group(1).strip()))

    chunks: list[str] = []
    seen: set[str] = set()

    for entry in _extract_pcs_chunks(block):
        if entry not in seen:
            seen.add(entry)
            chunks.append(entry)

    for m in PROSE_NAMED_ITEM.finditer(block):
        entry = f"{m.group(1).strip()}: {m.group(2).strip()}"
        entry = collapse_inline_whitespace(entry)[:220]
        base = entry.split(":", 1)[0].strip().lower()
        if any(base in c.lower() for c in chunks):
            continue
        if entry not in seen:
            seen.add(entry)
            chunks.append(entry)

    for m in re.finditer(
        r"(Acrly\s+Glas\s+[\d.x]+cm|Acrylic[^:]{4,60})\s*(?:can'?t\s+find|cannot\s+find|local\s+hardware)",
        block,
        re.I,
    ):
        entry = m.group(1).strip()
        if entry not in seen:
            seen.add(entry)
            chunks.append(entry)

    return chunks


def find_bom_section_lines(text: str) -> list[str]:
    return find_section_lines(
        text,
        section_start=SECTION_START,
        section_stop=SECTION_STOP,
        expand_line=_expand_section_line_gate,
    )


def parse_bom_line(line: str, *, require_hardware_keyword: bool = True) -> Part | None:
    return parse_hardware_line(
        line,
        default_notes=DESCRIPTION_NOTE,
        require_hardware_signal=require_hardware_keyword,
        clean_name=_clean_chunk_name,
    )


def _fallback_hardware_lines(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > 220:
            continue
        if has_hardware_signal(line) and parse_bom_line(line, require_hardware_keyword=True):
            found.append(line)
    return found[:25]


def extract_candidate_lines(description: str) -> tuple[list[str], bool]:
    text = normalize_prose(description)
    if not text:
        return [], False

    section_lines = find_bom_section_lines(text)
    if section_lines:
        return section_lines, True

    prose_chunks = _extract_inline_parts_chunks(text)
    if prose_chunks:
        return prose_chunks, True

    return _fallback_hardware_lines(text), False


@dataclass(frozen=True)
class DescriptionBomParse:
    parts: list[Part]
    from_explicit_section: bool


def parse_description_bom(description: str) -> DescriptionBomParse:
    """Parse description BOM lines and whether they came from a labeled section."""
    lines, from_section = extract_candidate_lines(description)
    require_keyword = not from_section

    parts: list[Part] = []
    seen: set[tuple[str, float, str]] = set()

    for line in lines:
        part = parse_bom_line(line, require_hardware_keyword=require_keyword)
        if not part:
            continue
        if re.fullmatch(r"https?", part.original_name, re.I):
            continue
        key = (
            part.original_name.strip().lower(),
            part.quantity,
            part.notes.strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        parts.append(part)

    return DescriptionBomParse(parts=parts, from_explicit_section=from_section)


def parts_from_description(description: str) -> list[Part]:
    return parse_description_bom(description).parts


__all__ = [
    "DESCRIPTION_NOTE",
    "description_summary",
    "extract_candidate_lines",
    "find_bom_section_lines",
    "html_to_text",
    "merge_parts",
    "DescriptionBomParse",
    "normalize_prose",
    "parse_bom_line",
    "parse_description_bom",
    "parts_from_description",
    "resolve_description_text",
]
