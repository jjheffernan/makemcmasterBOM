"""Spreadsheet column alias mapping for uploaded BOM files."""

from __future__ import annotations

COLUMN_ALIASES: dict[str, list[str]] = {
    "quantity": ["qty", "quantity", "count", "amount", "q'ty", "qnty", "#", "no.", "number"],
    "name": [
        "name",
        "part",
        "part name",
        "part_name",
        "item",
        "item name",
        "component",
        "description",
        "part description",
        "product",
        "product name",
        "material",
    ],
    "specification": [
        "spec",
        "specification",
        "size",
        "dimensions",
        "details",
        "remark",
        "remarks",
        "model",
        "sku",
    ],
    "notes": ["notes", "comment", "comments", "extra", "link", "url", "source"],
}


def normalize_column_name(col: str) -> str:
    return col.strip().lower().replace("_", " ")


def map_columns(columns: list[str]) -> dict[str, str]:
    normalized = {normalize_column_name(c): c for c in columns}
    mapping: dict[str, str] = {}

    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[target] = normalized[alias]
                break

    return mapping
