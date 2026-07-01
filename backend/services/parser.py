"""Backward-compatible re-exports — prefer backend.services.parsers.upload."""

from backend.services.parsers.upload import (
    ALLOWED_UPLOAD_EXTENSIONS,
    parse_upload_bytes,
)
from backend.services.parsers.spreadsheet import (
    COLUMN_ALIASES,
    dataframe_to_parts,
    map_columns,
    normalize_column_name,
)

ALLOWED_BOM_EXTENSIONS = ALLOWED_UPLOAD_EXTENSIONS


def parse_bom_bytes(content: bytes, filename: str):
    return parse_upload_bytes(content, filename)


__all__ = [
    "ALLOWED_BOM_EXTENSIONS",
    "COLUMN_ALIASES",
    "dataframe_to_parts",
    "map_columns",
    "normalize_column_name",
    "parse_bom_bytes",
    "parse_upload_bytes",
]
