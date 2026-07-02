"""Structured pandas DataFrames for notebook analysis — consistent column schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from backend.models.part import Part
from backend.services.vendors.mcmaster.browse_parse import BrowseRow

if TYPE_CHECKING:
    from backend.models.project import Project

PART_COLUMNS: tuple[str, ...] = (
    "quantity",
    "original_name",
    "specification",
    "notes",
    "normalized_name",
    "mcmaster_category",
    "mcmaster_metacategory",
    "mcmaster_metacategory_label",
    "match_tier",
    "mcmaster_status",
    "confidence",
    "confidence_low",
    "confidence_high",
    "mcmaster_part_number",
    "mcmaster_url",
    "mcmaster_reason",
    "hardware_match_status",
    "hardware_diameter_mm",
    "hardware_length_mm",
    "selected_finish_id",
    "match_option_count",
    "same_size_alts",
    "wider_scope_alts",
    "finish_options_count",
    "price_min_qty",
    "price_batch_cost",
    "unit_cost",
)

ALT_COLUMNS: tuple[str, ...] = (
    "original_name",
    "guess_scope",
    "guess_label",
    "match_tier",
    "confidence",
    "mcmaster_part_number",
    "mcmaster_url",
    "mcmaster_reason",
)

BROWSE_ROW_COLUMNS: tuple[str, ...] = (
    "part_number",
    "product_type",
    "product_subtype",
)


def part_to_row(part: Part) -> dict[str, Any]:
    same_size = sum(
        1 for alt in part.match_alternatives if alt.guess_scope == "same_size"
    )
    wider_scope = sum(
        1 for alt in part.match_alternatives if alt.guess_scope != "same_size"
    )
    return {
        "quantity": part.quantity,
        "original_name": part.original_name,
        "specification": part.specification,
        "notes": part.notes,
        "normalized_name": part.normalized_name,
        "mcmaster_category": part.mcmaster_category,
        "mcmaster_metacategory": part.mcmaster_metacategory,
        "mcmaster_metacategory_label": part.mcmaster_metacategory_label,
        "match_tier": part.match_tier,
        "mcmaster_status": part.mcmaster_status,
        "confidence": part.confidence,
        "confidence_low": part.confidence_low,
        "confidence_high": part.confidence_high,
        "mcmaster_part_number": part.mcmaster_part_number,
        "mcmaster_url": part.mcmaster_url,
        "mcmaster_reason": part.mcmaster_reason,
        "hardware_match_status": part.hardware_match_status,
        "hardware_diameter_mm": part.hardware_diameter_mm,
        "hardware_length_mm": part.hardware_length_mm,
        "selected_finish_id": part.selected_finish_id,
        "match_option_count": part.match_option_count,
        "same_size_alts": same_size,
        "wider_scope_alts": wider_scope,
        "finish_options_count": len(part.browse_finish_options),
        "price_min_qty": part.price_min_qty,
        "price_batch_cost": part.price_batch_cost,
        "unit_cost": part.unit_cost,
    }


def parts_to_dataframe(parts: list[Part]) -> pd.DataFrame:
    """BOM + McMaster match fields as a typed DataFrame for notebooks."""
    if not parts:
        return pd.DataFrame(columns=list(PART_COLUMNS))
    df = pd.DataFrame([part_to_row(part) for part in parts])
    return df.reindex(columns=list(PART_COLUMNS))


def alternatives_to_dataframe(parts: list[Part]) -> pd.DataFrame:
    """Flatten primary + secondary McMaster guesses for notebook inspection."""
    records: list[dict[str, Any]] = []
    for part in parts:
        for alt in part.match_alternatives:
            records.append(
                {
                    "original_name": part.original_name,
                    "guess_scope": alt.guess_scope,
                    "guess_label": alt.guess_label,
                    "match_tier": alt.match_tier,
                    "confidence": alt.confidence,
                    "mcmaster_part_number": alt.mcmaster_part_number,
                    "mcmaster_url": alt.mcmaster_url,
                    "mcmaster_reason": alt.mcmaster_reason,
                }
            )
    if not records:
        return pd.DataFrame(columns=list(ALT_COLUMNS))
    return pd.DataFrame(records).reindex(columns=list(ALT_COLUMNS))


def project_parts_dataframe(project: Project) -> pd.DataFrame:
    return parts_to_dataframe(project.parts)


def browse_rows_to_dataframe(rows: list[BrowseRow]) -> pd.DataFrame:
    """Flatten McMaster browse table rows with dynamic spec columns."""
    if not rows:
        return pd.DataFrame(columns=list(BROWSE_ROW_COLUMNS))
    records: list[dict[str, Any]] = []
    for row in rows:
        record: dict[str, Any] = {
            "part_number": row.part_number,
            "product_type": row.product_type,
            "product_subtype": row.product_subtype,
        }
        for key, value in row.fields.items():
            record[str(key)] = value
        records.append(record)
    df = pd.DataFrame(records)
    for col in BROWSE_ROW_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df
