"""Tests for hydration deduplication within a batch."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.models.part import BrowseFinishOption, Part
from backend.services.vendors.mcmaster.browse_finish_hydrate import hydrate_part_from_browse
from backend.services.vendors.mcmaster.browse_parse import BrowseRow
from backend.services.vendors.mcmaster.hydration_session import HydrationSession


@pytest.mark.asyncio
async def test_hydration_session_reuses_group_template(monkeypatch):
    monkeypatch.setattr(
        "backend.services.vendors.mcmaster.browse_finish_hydrate.config.MCMASTER_BROWSE_RESOLVE_ENABLED",
        True,
    )
    session = HydrationSession()
    base = Part(
        original_name="M3 Nut",
        match_tier="filtered_browse",
        mcmaster_category="nut",
        mcmaster_url=(
            "https://www.mcmaster.com/products/hex-nuts/metric-hex-nuts~~/"
            "system-of-measurement~metric/thread-size~m3/"
        ),
        browse_finish_options=[
            BrowseFinishOption(
                finish_id="metric",
                label="Metric hex nuts",
                mcmaster_url=(
                    "https://www.mcmaster.com/products/hex-nuts/metric-hex-nuts~~/"
                    "system-of-measurement~metric/thread-size~m3/"
                ),
            ),
        ],
    )
    row = BrowseRow(
        part_number="90591A110",
        fields={"Thread Size": "M3", "Price": "0.12"},
    )

    with patch(
        "backend.services.vendors.mcmaster.browse_finish_hydrate.fetch_browse_rows",
        new=AsyncMock(return_value=[row]),
    ) as fetch_mock:
        first = await hydrate_part_from_browse(base, session=session)
        duplicate = await hydrate_part_from_browse(
            base.model_copy(update={"quantity": 8}),
            session=session,
        )

    assert fetch_mock.await_count == 1
    assert first.mcmaster_part_number == "90591A110"
    assert duplicate.mcmaster_part_number == "90591A110"
    assert duplicate.unit_cost == pytest.approx(0.12)
