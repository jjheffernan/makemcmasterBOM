"""API rematch with exact|lazy guess_mode."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.models.part import MatchAlternative, Part


@pytest.mark.asyncio
async def test_rematch_passes_guess_mode():
    transport = ASGITransport(app=app)
    part = Part(original_name="M3 10mm screw", quantity=2)

    def _fake_match(parts, *, guess_mode="lazy"):
        alts = [
            MatchAlternative(
                mcmaster_url="https://www.mcmaster.com/products/screws/same/",
                guess_scope="same_size",
                confidence=0.8,
            ),
            MatchAlternative(
                mcmaster_url="https://www.mcmaster.com/products/screws/wider/",
                guess_scope="wider_scope",
                confidence=0.4,
            ),
        ]
        scoped = (
            [a for a in alts if a.guess_scope == "same_size"]
            if guess_mode == "exact"
            else alts
        )
        return [
            p.model_copy(
                update={
                    "mcmaster_url": "https://www.mcmaster.com/products/screws/",
                    "match_alternatives": scoped,
                    "confidence": 0.9,
                    "mcmaster_status": "likely",
                    "match_tier": "filtered_browse",
                }
            )
            for p in parts
        ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("backend.routers.bom_router.match_parts", side_effect=_fake_match):
            lazy = await client.post(
                "/api/bom/rematch",
                json={"parts": [part.model_dump()], "guess_mode": "lazy"},
            )
            exact = await client.post(
                "/api/bom/rematch",
                json={"parts": [part.model_dump()], "guess_mode": "exact"},
            )

    assert lazy.status_code == 200
    assert exact.status_code == 200
    lazy_body = lazy.json()
    exact_body = exact.json()
    assert lazy_body["guess_mode"] == "lazy"
    assert exact_body["guess_mode"] == "exact"
    assert any(a["guess_scope"] == "wider_scope" for a in lazy_body["parts"][0]["match_alternatives"])
    assert all(a["guess_scope"] == "same_size" for a in exact_body["parts"][0]["match_alternatives"])
