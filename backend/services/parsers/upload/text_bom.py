"""Parse text, markdown, and HTML BOM uploads via description rules."""

from __future__ import annotations

from backend.models.part import Part
from backend.services.parsers.makerworld.description import parts_from_description


def parse_text_bom(content: bytes) -> list[Part]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Text file must be UTF-8 encoded") from exc

    if not text.strip():
        raise ValueError("File is empty")

    parts = parts_from_description(text)
    if not parts:
        raise ValueError(
            "No hardware lines found — use a BOM section (Material required, BOM, etc.) "
            "or upload CSV/JSON instead"
        )
    return parts
