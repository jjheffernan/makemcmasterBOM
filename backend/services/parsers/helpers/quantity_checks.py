"""Runtime checks that BOM quantities were parsed correctly."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.models.part import Part
from backend.services.parsers.helpers.bom_quantities import QTY_LEADING, parse_quantity_and_name
from backend.services.parsers.helpers.hardware_signals import has_hardware_signal

QTY_PREFIX_IN_TEXT = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*[x×]\s+",
    re.I,
)


@dataclass(frozen=True)
class QuantityIssue:
    part_index: int
    original_name: str
    quantity: float
    specification: str
    notes: str
    code: str
    message: str
    source_line: str | None = None


def _qty_leading_in_text(text: str) -> re.Match[str] | None:
    text = (text or "").strip()
    if not text:
        return None
    return QTY_PREFIX_IN_TEXT.match(text)


def check_parsed_line(line: str) -> list[str]:
    """
    Validate a raw BOM line against parse_quantity_and_name output.

    Returns human-readable issue strings (empty when OK).
    """
    issues: list[str] = []
    quantity, name, specification, context_note = parse_quantity_and_name(line)

    right_after_colon = ""
    if ":" in line:
        right_after_colon = line.split(":", 1)[1].strip()

    qty_match = QTY_LEADING.match(right_after_colon) if right_after_colon else None
    if qty_match and (
        re.search(
            r"\b(?:against|module|modules|side|sides|attaching|gear|holder|holders|"
            r"hub|motor|pcb|sleeve|spool|roller|block|blocks)\b",
            line.split(":", 1)[0],
            re.I,
        )
        or len(line.split(":", 1)[0]) > 55
    ):
        expected_qty = float(qty_match.group(1))
        if quantity != expected_qty:
            issues.append(
                f"expected quantity {expected_qty:g} from '{right_after_colon[:40]}…'"
                if len(right_after_colon) > 40
                else f"expected quantity {expected_qty:g} from '{right_after_colon}'"
            )
        if not has_hardware_signal(name):
            issues.append("hardware should be part name, not assembly note")
        if context_note and context_note not in (specification, ""):
            pass  # context routed to notes downstream
        elif not context_note and ":" in line:
            issues.append("assembly note should be captured as context, not part name")

    spec_qty = _qty_leading_in_text(specification)
    if spec_qty and quantity == 1:
        embedded = float(spec_qty.group(1))
        issues.append(
            f"quantity is 1 but specification embeds {embedded:g} "
            f"('{specification[:50]}')"
        )

    if (
        specification
        and has_hardware_signal(specification)
        and not has_hardware_signal(name)
        and len(name) > 24
    ):
        issues.append(
            "part name looks like prose/location but specification contains hardware"
        )

    return issues


def check_part(
    part: Part,
    *,
    index: int = 0,
    source_line: str | None = None,
) -> list[QuantityIssue]:
    """Validate a Part for common quantity / field-placement mistakes."""
    found: list[QuantityIssue] = []

    spec_qty = _qty_leading_in_text(part.specification)
    if spec_qty and part.quantity == 1:
        embedded = float(spec_qty.group(1))
        found.append(
            QuantityIssue(
                part_index=index,
                original_name=part.original_name,
                quantity=part.quantity,
                specification=part.specification,
                notes=part.notes,
                code="qty_in_specification",
                message=(
                    f"quantity is 1 but specification starts with "
                    f"{embedded:g} x — likely misparsed"
                ),
                source_line=source_line,
            )
        )

    if (
        part.specification
        and has_hardware_signal(part.specification)
        and not has_hardware_signal(part.original_name)
        and len(part.original_name) > 24
    ):
        found.append(
            QuantityIssue(
                part_index=index,
                original_name=part.original_name,
                quantity=part.quantity,
                specification=part.specification,
                notes=part.notes,
                code="hardware_in_specification",
                message="hardware appears in specification while part name looks like prose",
                source_line=source_line,
            )
        )

    if source_line:
        for msg in check_parsed_line(source_line):
            code = "parse_mismatch"
            if "expected quantity" in msg:
                code = "wrong_quantity"
            elif "assembly note" in msg:
                code = "note_in_name"
            found.append(
                QuantityIssue(
                    part_index=index,
                    original_name=part.original_name,
                    quantity=part.quantity,
                    specification=part.specification,
                    notes=part.notes,
                    code=code,
                    message=msg,
                    source_line=source_line,
                )
            )

    return found


def check_parts(
    parts: list[Part],
    *,
    source_lines: list[str] | None = None,
) -> list[QuantityIssue]:
    """Validate a list of parts; optional parallel source lines for deeper checks."""
    issues: list[QuantityIssue] = []
    for i, part in enumerate(parts):
        line = source_lines[i] if source_lines and i < len(source_lines) else None
        issues.extend(check_part(part, index=i, source_line=line))
    return issues


def format_issues(issues: list[QuantityIssue]) -> str:
    if not issues:
        return "No quantity issues found."
    lines = [f"Found {len(issues)} quantity issue(s):", ""]
    for issue in issues:
        loc = f"line {issue.part_index + 1}" if issue.source_line else f"part {issue.part_index + 1}"
        lines.append(f"[{issue.code}] {loc}: {issue.message}")
        lines.append(f"  name: {issue.original_name!r}  qty: {issue.quantity:g}")
        if issue.specification:
            lines.append(f"  spec: {issue.specification!r}")
        if issue.notes:
            lines.append(f"  notes: {issue.notes!r}")
        if issue.source_line:
            lines.append(f"  source: {issue.source_line!r}")
        lines.append("")
    return "\n".join(lines).rstrip()
