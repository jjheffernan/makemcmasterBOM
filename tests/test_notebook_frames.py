"""Tests for structured notebook DataFrames."""

from backend.models.part import MatchAlternative, Part
from backend.notebook_frames import (
    ALT_COLUMNS,
    PART_COLUMNS,
    alternatives_to_dataframe,
    parts_to_dataframe,
)


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
    assert df.loc[0, "same_size_alts"] == 0
    assert df.loc[0, "wider_scope_alts"] == 0


def test_alternatives_to_dataframe():
    part = Part(
        original_name="M3 Nut",
        match_alternatives=[
            MatchAlternative(
                mcmaster_url="https://example.com/zinc",
                guess_scope="same_size",
                guess_label="Zinc plated",
                match_tier="filtered_browse",
                confidence=0.72,
                mcmaster_reason="Same size — zinc",
            )
        ],
    )
    df = alternatives_to_dataframe([part])
    assert list(df.columns) == list(ALT_COLUMNS)
    assert df.loc[0, "guess_scope"] == "same_size"
    assert df.loc[0, "guess_label"] == "Zinc plated"
