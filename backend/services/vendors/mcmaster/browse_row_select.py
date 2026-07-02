"""Pick the best McMaster browse table row for a BOM line."""

from __future__ import annotations

import re

from backend.models.part import Part
from backend.services.hardware_spec import MetricFastenerSpec, primary_fastener_spec
from backend.services.pricing_listing import effective_unit_cost_for_row
from backend.services.vendors.mcmaster.browse_parse import BrowseRow, find_row_by_part_number

_THREAD_FIELD_KEYS = ("Thread Size", "Thread", "Size")
_LENGTH_FIELD_KEYS = ("Length", "Overall Length", "Lg.")
_TYPE_FIELD_KEYS = ("Type", "Fastener Type", "Nut Type", "Washer Type", "Head Type")

_COMPLEX_SUBTYPE_RE = re.compile(
    r"\b(jam|lock|nyloc|nylock|flange|cap|wing|coupling|prevailing|"
    r"fender|sealing|left[\s-]*hand|venting|thread[\s-]*locking)\b",
    re.I,
)
_FLAT_HEAD_RE = re.compile(r"\b(flat|countersunk?)\b", re.I)
_SOCKET_HEAD_RE = re.compile(r"\b(socket|cap)\b", re.I)


def _row_field(row: BrowseRow, keys: tuple[str, ...]) -> str:
    for key in keys:
        if key in row.fields and row.fields[key] not in ("", None):
            return str(row.fields[key])
    lowered = {str(k).lower(): v for k, v in row.fields.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return str(value)
    return ""


def _length_mm_from_text(text: str) -> float | None:
    match = re.search(r"([\d.]+)\s*mm\b", text, re.I)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _thread_matches(spec: MetricFastenerSpec, thread_text: str) -> bool:
    if not thread_text.strip():
        return True
    normalized = thread_text.lower().replace(" ", "")
    target = f"m{spec.diameter_mm:g}".lower().replace(".", "-")
    return target in normalized or f"m{int(spec.diameter_mm)}" in normalized


def _row_matches_spec(row: BrowseRow, spec: MetricFastenerSpec) -> bool:
    thread_text = _row_field(row, _THREAD_FIELD_KEYS)
    if thread_text and not _thread_matches(spec, thread_text):
        return False

    if spec.length_mm is not None:
        length_text = _row_field(row, _LENGTH_FIELD_KEYS)
        if length_text:
            row_length = _length_mm_from_text(length_text)
            if row_length is not None and int(row_length) != int(spec.length_mm):
                return False
    return True


def _row_text_blob(row: BrowseRow) -> str:
    chunks = [row.product_type, row.product_subtype, *map(str, row.fields.values())]
    return " ".join(chunk for chunk in chunks if chunk).lower()


def _row_simplicity_score(part: Part, row: BrowseRow) -> float:
    """Higher score = simpler default hardware (standard hex nut, flat washer, etc.)."""
    blob = _row_text_blob(row)
    score = 0.0
    spec = primary_fastener_spec(part)
    if spec and spec.kind == "nut":
        if re.search(r"\bhex nut\b", blob):
            score += 4.0
        if re.search(r"\bstandard\b", blob):
            score += 2.0
    if spec and spec.kind == "washer":
        if re.search(r"\bflat washer\b", blob):
            score += 4.0
    if _COMPLEX_SUBTYPE_RE.search(blob):
        score -= 5.0
    return score


def _pick_simplest_row(part: Part, rows: list[BrowseRow]) -> BrowseRow | None:
    if not rows:
        return None
    ranked = sorted(
        rows,
        key=lambda row: (_row_simplicity_score(part, row), row.part_number),
        reverse=True,
    )
    best_score = _row_simplicity_score(part, ranked[0])
    if best_score <= 0:
        return None
    return ranked[0]


def pick_simplest_browse_row(
    part: Part,
    rows: list[BrowseRow],
    *,
    browse_url: str = "",
    part_number_hint: str = "",
) -> BrowseRow | None:
    """Default match: simplest catalog row that satisfies BOM specs."""
    if not rows:
        return None

    hint = part_number_hint.strip() or part.mcmaster_part_number.strip()
    if hint:
        matched = find_row_by_part_number(rows, hint)
        if matched:
            return matched

    candidates = _candidate_rows(part, rows)
    simplest = _pick_simplest_row(part, candidates)
    if simplest:
        return simplest

    return pick_best_browse_row(
        part,
        rows,
        browse_url=browse_url,
        part_number_hint=hint,
    )


def _url_pre_filtered(browse_url: str) -> bool:
    lower = browse_url.lower()
    return "thread-size~" in lower or "length~" in lower


def _candidate_rows(part: Part, rows: list[BrowseRow]) -> list[BrowseRow]:
    spec = primary_fastener_spec(part)
    if not spec:
        return rows
    matching = [row for row in rows if _row_matches_spec(row, spec)]
    return matching or rows


def pick_best_browse_row(
    part: Part,
    rows: list[BrowseRow],
    *,
    browse_url: str = "",
    part_number_hint: str = "",
) -> BrowseRow | None:
    """Choose a browse row using BOM specs, catalog hints, or pre-filtered URL context."""
    if not rows:
        return None

    hint = part_number_hint.strip() or part.mcmaster_part_number.strip()
    if hint:
        matched = find_row_by_part_number(rows, hint)
        if matched:
            return matched

    spec = primary_fastener_spec(part)
    if spec:
        matching = [row for row in rows if _row_matches_spec(row, spec)]
        if len(matching) == 1:
            return matching[0]
        if len(matching) > 1 and spec.length_mm is not None:
            for row in matching:
                length_text = _row_field(row, _LENGTH_FIELD_KEYS)
                row_length = _length_mm_from_text(length_text)
                if row_length is not None and int(row_length) == int(spec.length_mm):
                    return row
        if matching:
            simplest = _pick_simplest_row(part, matching)
            if simplest:
                return simplest
            return matching[0]

    if _url_pre_filtered(browse_url) and rows:
        return rows[0]

    if len(rows) == 1:
        return rows[0]

    return None


def pick_lowest_price_row(
    part: Part,
    rows: list[BrowseRow],
    *,
    browse_url: str = "",
) -> BrowseRow | None:
    """Pick the cheapest per-unit row that matches BOM specs (MVP default)."""
    if not rows:
        return None

    hint = part.mcmaster_part_number.strip()
    if hint:
        matched = find_row_by_part_number(rows, hint)
        if matched:
            return matched

    candidates = _candidate_rows(part, rows)
    bom_qty = float(part.quantity or 1)
    best_row: BrowseRow | None = None
    best_cost: float | None = None

    for row in candidates:
        unit_cost = effective_unit_cost_for_row(row, bom_qty=bom_qty)
        if unit_cost is None:
            continue
        if best_cost is None or unit_cost < best_cost:
            best_cost = unit_cost
            best_row = row

    if best_row:
        return best_row

    simplest = _pick_simplest_row(part, candidates)
    if simplest:
        return simplest

    return pick_best_browse_row(
        part,
        rows,
        browse_url=browse_url,
        part_number_hint=hint,
    )
