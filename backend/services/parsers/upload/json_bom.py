"""Parse JSON BOM uploads — Part arrays or MakerWorld design JSON."""

from __future__ import annotations

import json

from backend.models.part import Part
from backend.services.parsers.makerworld.embedded import parts_from_design
from backend.services.parsers.makerworld.page_json import extract_design


def _parts_from_json_list(items: list) -> list[Part]:
    parts: list[Part] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("JSON array items must be objects with part fields")
        parts.append(Part.model_validate(item))
    return parts


def parse_json_bom(content: bytes) -> list[Part]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("JSON file must be UTF-8 encoded") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if isinstance(data, list):
        return _parts_from_json_list(data)

    if isinstance(data, dict):
        if "parts" in data and isinstance(data["parts"], list):
            return _parts_from_json_list(data["parts"])

        design = extract_design(data)
        if design:
            parts = parts_from_design(design)
            if parts:
                return parts

        if "designExtension" in data or "boms_v2" in data or "boms" in data:
            parts = parts_from_design(data)
            if parts:
                return parts

    raise ValueError(
        "JSON must be a parts array, an object with a \"parts\" array, "
        "or MakerWorld __NEXT_DATA__ / design JSON"
    )
