"""Tests for structured notebook DataFrames."""

from backend.models.part import Part
from backend.notebook_frames import PART_COLUMNS, parts_to_dataframe


def test_parts_to_dataframe_empty():
    df = parts_to_dataframe([])
    assert list(df.columns) == list(PART_COLUMNS)
    assert len(df) == 0


def test_parts_to_dataframe_schema():
    part = Part(
        original_name="M3 screw",
        notes="MakerWorld BOM (description)",
        match_tier="filtered_browse",
        confidence=0.9,
    )
    df = parts_to_dataframe([part])
    assert list(df.columns) == list(PART_COLUMNS)
    assert df.loc[0, "original_name"] == "M3 screw"
    assert df.loc[0, "notes"] == "MakerWorld BOM (description)"
    assert df.loc[0, "match_tier"] == "filtered_browse"
    assert df.loc[0, "alternatives_count"] == 0
