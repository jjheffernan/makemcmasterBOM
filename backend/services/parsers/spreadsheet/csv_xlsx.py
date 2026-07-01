"""CSV and XLSX BOM file parser."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from backend.models.part import Part
from backend.services.parsers.helpers.spec_metadata import normalize_part_specification
from backend.services.parsers.spreadsheet.columns import COLUMN_ALIASES, map_columns, normalize_column_name


def _read_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    buffer = io.BytesIO(content)

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(buffer)
    if suffix == ".csv":
        return pd.read_csv(buffer)
    try:
        buffer.seek(0)
        return pd.read_csv(buffer)
    except Exception:
        buffer.seek(0)
        return pd.read_excel(buffer)


def dataframe_to_parts(df: pd.DataFrame) -> list[Part]:
    mapping = map_columns(list(df.columns))
    parts: list[Part] = []

    name_col = mapping.get("name")
    if not name_col:
        for col in df.columns:
            if normalize_column_name(col) not in COLUMN_ALIASES["quantity"]:
                name_col = col
                break

    for _, row in df.iterrows():
        qty_raw = row.get(mapping["quantity"], 1) if "quantity" in mapping else 1
        try:
            quantity = float(qty_raw) if pd.notna(qty_raw) else 1.0
        except (TypeError, ValueError):
            quantity = 1.0

        original_name = ""
        if name_col is not None and pd.notna(row.get(name_col)):
            original_name = str(row[name_col]).strip()

        if not original_name:
            continue

        spec = ""
        if "specification" in mapping and pd.notna(row.get(mapping["specification"])):
            spec = str(row[mapping["specification"]]).strip()

        notes = ""
        if "notes" in mapping and pd.notna(row.get(mapping["notes"])):
            notes = str(row[mapping["notes"]]).strip()

        parts.append(
            normalize_part_specification(
                Part(
                    quantity=quantity,
                    original_name=original_name,
                    normalized_name=original_name,
                    specification=spec,
                    notes=notes,
                )
            )
        )

    return parts


def parse_bom_bytes(content: bytes, filename: str) -> list[Part]:
    df = _read_dataframe(content, filename)
    df = df.dropna(how="all")
    return dataframe_to_parts(df)
