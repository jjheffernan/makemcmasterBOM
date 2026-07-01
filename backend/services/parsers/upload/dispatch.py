"""Detect upload format and route to the appropriate BOM parser."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from backend.models.part import Part
from backend.services.parsers.spreadsheet.csv_xlsx import dataframe_to_parts, parse_bom_bytes
from backend.services.parsers.upload.json_bom import parse_json_bom
from backend.services.parsers.upload.text_bom import parse_text_bom

SPREADSHEET_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls"}
TEXT_EXTENSIONS = {".md", ".markdown", ".html", ".htm", ".txt"}

ALLOWED_UPLOAD_EXTENSIONS = frozenset(
    SPREADSHEET_EXTENSIONS | TEXT_EXTENSIONS | {".json"}
)

SUPPORTED_FORMAT_LABELS = (
    "CSV",
    "TSV",
    "XLSX",
    "JSON",
    "Markdown",
    "HTML",
    "plain text",
)


def _decode_preview(content: bytes, limit: int = 4096) -> str:
    try:
        return content[:limit].decode("utf-8-sig", errors="replace").strip()
    except Exception:
        return ""


def _looks_like_json(preview: str) -> bool:
    return bool(preview) and preview[0] in "[{"


def _looks_like_html(preview: str) -> bool:
    lower = preview.lower()
    return lower.startswith("<!doctype") or lower.startswith("<html") or "<body" in lower[:500]


def _looks_like_spreadsheet(preview: str) -> bool:
    lines = [line for line in preview.splitlines() if line.strip()][:5]
    if len(lines) < 2:
        return False
    header = lines[0].lower()
    if any(
        token in header
        for token in ("qty", "quantity", "part", "name", "item", "component", "amount")
    ):
        return "," in lines[0] or "\t" in lines[0] or ";" in lines[0]
    return False


def detect_upload_format(content: bytes, filename: str) -> str:
    """Return parser id: spreadsheet | json | text."""
    suffix = Path(filename).suffix.lower()
    if suffix in SPREADSHEET_EXTENSIONS:
        return "spreadsheet"
    if suffix == ".json":
        return "json"
    if suffix in TEXT_EXTENSIONS:
        preview = _decode_preview(content)
        if _looks_like_json(preview):
            return "json"
        if _looks_like_spreadsheet(preview) and suffix == ".txt":
            return "spreadsheet"
        return "text"

    preview = _decode_preview(content)
    if _looks_like_json(preview):
        return "json"
    if _looks_like_html(preview):
        return "text"
    if _looks_like_spreadsheet(preview):
        return "spreadsheet"
    if preview:
        return "text"
    raise ValueError("Could not detect file format — file may be empty")


def _parse_spreadsheet(content: bytes, filename: str) -> list[Part]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".tsv":
        buffer = io.BytesIO(content)
        df = pd.read_csv(buffer, sep="\t")
        df = df.dropna(how="all")
        return dataframe_to_parts(df)
    return parse_bom_bytes(content, filename)


def parse_upload_bytes(content: bytes, filename: str) -> list[Part]:
    """Parse an uploaded BOM file of any supported format."""
    fmt = detect_upload_format(content, filename)
    if fmt == "spreadsheet":
        return _parse_spreadsheet(content, filename)
    if fmt == "json":
        return parse_json_bom(content)
    return parse_text_bom(content)


def format_hint_for_extension(suffix: str) -> str:
    labels = ", ".join(SUPPORTED_FORMAT_LABELS)
    if suffix and suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        return f"Unsupported type '{suffix}'. Supported: {labels}."
    return f"Supported formats: {labels}."
