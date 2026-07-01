"""Parse a single BOM text line into a Part."""

from __future__ import annotations

import re
from collections.abc import Callable

from backend.models.part import Part
from backend.services.parsers.helpers.bom_quantities import parse_quantity_and_name
from backend.services.parsers.helpers.hardware_signals import has_hardware_signal
from backend.services.parsers.helpers.marketplace import (
    SKIP_PROSE_LINE,
    clean_name_and_spec,
    marketplace_note_suffix,
)
from backend.services.parsers.helpers.spec_metadata import normalize_part_specification


def _compose_notes(
    line: str,
    *,
    default_notes: str,
    context_note: str,
) -> str:
    if context_note:
        base = f"{context_note} ({default_notes})" if default_notes else context_note
    else:
        base = default_notes
    return marketplace_note_suffix(line, base)


def parse_hardware_line(
    line: str,
    *,
    default_notes: str,
    require_hardware_signal: bool = True,
    clean_name: Callable[[str], str] | None = None,
) -> Part | None:
    """Shared line parser used by site-specific description parsers."""
    if not line or SKIP_PROSE_LINE.match(line):
        return None

    quantity, name, specification, context_note = parse_quantity_and_name(line)
    if not name or len(name) < 2:
        return None

    name, specification = clean_name_and_spec(name, specification)
    if clean_name:
        name = clean_name(name)
    if len(name) < 2:
        return None

    name = re.split(r"\.\s+i['']?m\s+using\b", name, maxsplit=1, flags=re.I)[0].strip()
    specification = re.split(
        r"\.\s+i['']?m\s+using\b", specification, maxsplit=1, flags=re.I
    )[0].strip()

    if require_hardware_signal and not has_hardware_signal(f"{name} {specification}"):
        return None

    return normalize_part_specification(
        Part(
            quantity=quantity,
            original_name=name,
            specification=specification[:400],
            notes=_compose_notes(line, default_notes=default_notes, context_note=context_note),
        )
    )
