"""Tests for live finish hydration and lowest-price row selection."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.models.part import BrowseFinishOption, Part
from backend.services.vendors.mcmaster.browse_finish_hydrate import (
    apply_finish_selection,
    hydrate_part_from_browse,
)
from backend.services.vendors.mcmaster.browse_parse import BrowseRow
from backend.services.vendors.mcmaster.browse_row_select import pick_lowest_price_row


def test_pick_lowest_price_row():
    part = Part(original_name="M3x8 socket head cap screw", quantity=1)
    rows = [
        BrowseRow(
            part_number="91290A110",
            fields={"Length": "8 mm", "Thread Size": "M3", "Price": "0.42"},
        ),
        BrowseRow(
            part_number="91290A111",
            fields={"Length": "8 mm", "Thread Size": "M3", "Price": "0.18"},
        ),
    ]
    picked = pick_lowest_price_row(part, rows)
    assert picked is not None
    assert picked.part_number == "91290A111"


@pytest.mark.asyncio
async def test_hydrate_part_defaults_to_lowest_price(monkeypatch):
    monkeypatch.setattr(
        "backend.services.vendors.mcmaster.browse_finish_hydrate.config.MCMASTER_BROWSE_RESOLVE_ENABLED",
        True,
    )
    part = Part(
        original_name="M3x8 socket head cap screw",
        match_selection_policy="lowest_price",
        match_tier="filtered_browse",
        mcmaster_url=(
            "https://www.mcmaster.com/products/screws/socket-head-screws-2~/"
            "system-of-measurement~metric/thread-size~m3/length~8-mm/"
        ),
        browse_finish_options=[
            BrowseFinishOption(
                finish_id="zinc",
                label="Zinc",
                mcmaster_url="https://example.com/zinc",
            ),
            BrowseFinishOption(
                finish_id="black_oxide",
                label="Black Oxide",
                mcmaster_url="https://example.com/black",
            ),
        ],
    )

    async def fake_fetch(url: str):
        if "zinc" in url:
            return [
                BrowseRow(
                    part_number="91290A110",
                    fields={"Length": "8 mm", "Thread Size": "M3", "Price": "0.42"},
                )
            ]
        return [
            BrowseRow(
                part_number="91290A111",
                fields={"Length": "8 mm", "Thread Size": "M3", "Price": "0.18"},
            )
        ]

    with patch(
        "backend.services.vendors.mcmaster.browse_finish_hydrate.fetch_browse_rows",
        new=AsyncMock(side_effect=fake_fetch),
    ):
        updated = await hydrate_part_from_browse(part)

    assert updated.mcmaster_part_number == "91290A111"
    assert updated.match_selection_policy == "lowest_price"
    assert updated.unit_cost == pytest.approx(0.18)
    assert len(updated.browse_finish_options) == 2
    assert updated.browse_finish_options[0].unit_cost == pytest.approx(0.42)
    assert updated.browse_finish_options[1].unit_cost == pytest.approx(0.18)


def test_apply_finish_selection_uses_hydrated_option():
    part = Part(
        original_name="M3x8 screw",
        mcmaster_part_number="91290A110",
        unit_cost=0.42,
        browse_finish_options=[
            BrowseFinishOption(
                finish_id="zinc",
                label="Zinc",
                mcmaster_url="https://example.com/zinc",
                mcmaster_part_number="91290A110",
                product_url="https://www.mcmaster.com/91290A110",
                unit_cost=0.42,
            ),
            BrowseFinishOption(
                finish_id="black_oxide",
                label="Black Oxide",
                mcmaster_url="https://example.com/black",
                mcmaster_part_number="91290A111",
                product_url="https://www.mcmaster.com/91290A111",
                unit_cost=0.18,
            ),
        ],
    )
    updated = apply_finish_selection(part, "black_oxide")
    assert updated.mcmaster_part_number == "91290A111"
    assert updated.unit_cost == pytest.approx(0.18)
    assert updated.match_selection_policy == "finish"
    assert updated.selected_finish_id == "black_oxide"
