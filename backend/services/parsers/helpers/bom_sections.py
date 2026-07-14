"""Generic BOM section scanning — site parsers supply header/stop patterns."""

from __future__ import annotations

import re
from collections.abc import Callable


def find_section_lines(
    text: str,
    *,
    section_start: re.Pattern[str],
    section_stop: re.Pattern[str],
    expand_line: Callable[[str], list[str]] | None = None,
) -> list[str]:
    """
    Collect lines under a BOM-related section header.

    `expand_line` optionally splits long inline lists (MakerWorld prose Parts blocks).
    """
    lines = [ln.strip() for ln in text.splitlines()]
    bom_lines: list[str] = []
    in_section = False

    for line in lines:
        if not line:
            continue
        if section_stop.match(line):
            in_section = False
            continue
        if section_start.match(line):
            in_section = True
            continue
        if in_section:
            if expand_line:
                bom_lines.extend(expand_line(line))
            else:
                bom_lines.append(line)

    return bom_lines
