"""Tests for in-house McMaster browse scrape and parse."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.vendors.mcmaster.browse_parse import parse_product_presentations
from backend.services.vendors.mcmaster.browse_scrape import _extract_json_from_response

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_product_presentations_min_fixture():
    payload = json.loads(
        (FIXTURES / "mcmaster_product_presentations_min.json").read_text(encoding="utf-8")
    )
    rows = parse_product_presentations(payload)
    assert len(rows) == 1
    assert rows[0].part_number == "91290A120"
    assert rows[0].fields.get("Length") == "16 mm"


def test_extract_json_from_response():
    payload = {"Name": "ProductPresentations", "Data": []}
    body = f"  prefix {json.dumps(payload)} suffix "
    assert _extract_json_from_response(body) == payload


def test_extract_json_from_response_raises_when_missing():
    with pytest.raises(ValueError, match="No JSON"):
        _extract_json_from_response("not json")


@pytest.mark.asyncio
async def test_fetch_product_presentations_rejects_non_mcmaster_url():
    from backend.services.vendors.mcmaster.browse_scrape import fetch_product_presentations

    with pytest.raises(ValueError, match="McMaster"):
        await fetch_product_presentations("https://example.com/parts")


@pytest.mark.asyncio
async def test_live_browse_fetch_disabled_by_default():
    from backend.services.vendors.mcmaster.browse_fetch import fetch_browse_rows

    url = (
        "https://www.mcmaster.com/products/screws/socket-head-screws-2~/"
        "black-oxide-alloy-steel-socket-head-screws~~/"
        "system-of-measurement~metric/thread-size~m3/length~16-mm/"
    )
    with pytest.raises(RuntimeError, match="MCMASTER_BROWSE_RESOLVE_ENABLED"):
        await fetch_browse_rows(url)
