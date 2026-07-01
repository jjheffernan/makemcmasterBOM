import json
from pathlib import Path

import pytest

from backend.services.makerworld_bom import (
    best_attachment,
    extract_next_data,
    parts_from_design,
    score_attachment,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parts_from_kumiko_fixture():
    design = json.loads((FIXTURES / "makerworld_kumiko_design.json").read_text())
    parts = parts_from_design(design)
    names = [p.original_name for p in parts]
    assert "LED Lamp Kit (1pcs) - MH001" in names
    assert "Matte Charcoal (11101) / Refill / 1kg" in names
    assert "E27-light-socket" in names
    assert "led-light-bulb-low-lumen" in names
    assert sum(1 for p in parts if p.original_name == "led-light-bulb-low-lumen") == 1
    bulb = next(p for p in parts if p.original_name == "led-light-bulb-low-lumen")
    assert bulb.quantity == 2


def test_parts_from_magnet_fixture():
    design = json.loads((FIXTURES / "makerworld_magnet_design.json").read_text())
    parts = parts_from_design(design)
    assert len(parts) == 1
    assert parts[0].original_name == "D10x3 mm Round Magnet (20PCS) - CA009"
    assert parts[0].quantity == 2


def test_extract_next_data_from_html():
    payload = {"props": {"pageProps": {"design": {"title": "Test"}}}}
    html = f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></html>'
    data = extract_next_data(html)
    assert data is not None
    assert data["props"]["pageProps"]["design"]["title"] == "Test"


def test_score_attachment_prefers_bom_csv():
    assert score_attachment("https://x.com/bom.csv", "bom.csv") > score_attachment(
        "https://x.com/data.xlsx", "data.xlsx"
    )


def test_best_attachment():
    winner = best_attachment(
        [
            ("https://cdn.example.com/data.xlsx", "data.xlsx"),
            ("https://cdn.example.com/project-bom.csv", "project-bom.csv"),
        ]
    )
    assert winner == ("https://cdn.example.com/project-bom.csv", "project-bom.csv")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_makerworld_description_bom():
    """Requires network — run with: pytest -m integration"""
    from backend.services.pipeline import import_from_url

    project = await import_from_url(
        "https://makerworld.com/en/models/972938-mega-python-ultimate-bambu-lab-ams#profileId-1092318"
    )
    assert project.bom_status == "description"
    assert len(project.parts) >= 10
    m3_16 = next((p for p in project.parts if "m3-16" in p.original_name.lower()), None)
    assert m3_16 is not None
    assert m3_16.quantity == 75
