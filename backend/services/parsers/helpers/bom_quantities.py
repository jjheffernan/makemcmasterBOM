"""Quantity and unit parsing patterns shared across site BOM parsers."""

from __future__ import annotations

import re

from backend.services.parsers.helpers.hardware_signals import DIMENSION_AXIAL_RE

BULLET_PREFIX = re.compile(r"^[-*•●▪]\s+")
NUMBER_PREFIX = re.compile(r"^\d+[\.\)]\s+")

QTY_LEADING = re.compile(
    r"^(\d+(?:\.\d+)?)\s*[x×]\s+(.+)$",
    re.I,
)
QTY_TRAILING = re.compile(
    r"^(.+?)\s*[\(\[]?\s*[x×]\s*(\d+(?:\.\d+)?)\s*[\)\]]?\s*$",
    re.I,
)
QTY_EXPLICIT = re.compile(
    r"^(?:qty|quantity)\s*[:.]?\s*(\d+(?:\.\d+)?)\s*[-–—]?\s*(.+)$",
    re.I,
)
QTY_PCS = re.compile(
    r"^(?:min\s+)?(\d+(?:\.\d+)?)\s*pcs?\b",
    re.I,
)
QTY_PCS_LEADING = re.compile(
    r"^(\d+(?:\.\d+)?)\s*pcs?\s+(.+)$",
    re.I,
)

# Left side of ``<note>: N x hardware`` assembly-location lines (MakerWorld fastener lists)
ASSEMBLY_NOTE_HINT = re.compile(
    r"\b(?:against|module|modules|side|sides|attaching|gear|holder|holders|"
    r"hub|motor|pcb|sleeve|spool|roller|block|blocks)\b",
    re.I,
)

DIMENSION_FRAGMENT = DIMENSION_AXIAL_RE


def strip_line_prefix(line: str) -> str:
    line = BULLET_PREFIX.sub("", line.strip())
    return NUMBER_PREFIX.sub("", line).strip()


def parse_quantity_and_name(line: str) -> tuple[float, str, str, str]:
    """
    Return (quantity, name, specification, context_note) from a single BOM line.

    `context_note` holds assembly-location prose when the line uses the pattern
    ``<location note>: <qty> x <hardware>`` (common in MakerWorld fastener lists).
    """
    line = strip_line_prefix(line)
    line = re.sub(r"\s+", " ", line).strip()
    if not line:
        return 1.0, "", "", ""

    m = QTY_EXPLICIT.match(line)
    if m:
        return float(m.group(1)), m.group(2).strip(), "", ""

    m = QTY_LEADING.match(line)
    if m:
        qty = float(m.group(1))
        rest = m.group(2).strip()
        if rest and (
            not DIMENSION_FRAGMENT.search(rest)
            or re.search(r"\b(screw|bolt|nut|washer|bearing|magnet|tube)\b", rest, re.I)
        ):
            return qty, rest, "", ""

    m = QTY_PCS_LEADING.match(line)
    if m:
        return float(m.group(1)), m.group(2).strip(), "", ""

    m = QTY_TRAILING.match(line)
    if m:
        name, qty = m.group(1).strip(), float(m.group(2))
        return qty, name, "", ""

    if ":" in line:
        left, right = line.split(":", 1)
        left = left.strip()
        right = right.strip()
        if left and right and len(left) < 120:
            pcs = QTY_PCS.match(right)
            if pcs:
                spec = QTY_PCS.sub("", right).strip(" ()")
                qty = float(pcs.group(1).split("/")[0])
                return qty, left, spec, ""

            # Assembly note: N x hardware (e.g. "Left module: 13 x M3-16 mm")
            m = QTY_LEADING.match(right)
            if m and (ASSEMBLY_NOTE_HINT.search(left) or len(left) > 55):
                qty = float(m.group(1))
                hardware = m.group(2).strip()
                return qty, hardware, "", left

            if DIMENSION_FRAGMENT.search(right) or not re.match(
                r"^\d+(?:\.\d+)?(?:\s*(?:x|pcs?|pieces?|units?))?\s*$",
                right,
                re.I,
            ):
                return 1.0, left, right, ""
            m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:x|pcs?|pieces?|units?)?\s*$", right, re.I)
            if m:
                return float(m.group(1)), left, "", ""

    return 1.0, line, "", ""
