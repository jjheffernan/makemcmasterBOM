"""Tests for sync-pricing rate limit, part caps, and URL checks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from backend import config
from backend.main import app
from backend.models.part import Part
from backend.rate_limit import check_sync_pricing_rate_limit, reset_rate_limits_for_tests


def _mock_request(host: str = "127.0.0.1") -> MagicMock:
    req = MagicMock()
    req.client.host = host
    req.headers.get.return_value = None
    return req


@pytest.fixture(autouse=True)
def _reset_limits():
    reset_rate_limits_for_tests()
    yield
    reset_rate_limits_for_tests()


@pytest.mark.asyncio
async def test_sync_pricing_rate_limit_blocks_excess(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config, "RATE_LIMIT_SYNC_PRICING_PER_MINUTE", 2)

    await check_sync_pricing_rate_limit(_mock_request())
    await check_sync_pricing_rate_limit(_mock_request())

    with pytest.raises(HTTPException) as exc:
        await check_sync_pricing_rate_limit(_mock_request())
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


@pytest.mark.asyncio
async def test_sync_pricing_rejects_too_many_parts(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(config, "SYNC_PRICING_MAX_PARTS", 2)
    transport = ASGITransport(app=app)
    parts = [
        Part(original_name=f"p{i}", quantity=1, mcmaster_url="https://www.mcmaster.com/91251A194/")
        for i in range(3)
    ]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "backend.services.pricing_listing.sync_parts_pricing_from_listings",
            new_callable=AsyncMock,
        ) as mocked:
            response = await client.post(
                "/api/bom/sync-pricing",
                json={"parts": [p.model_dump() for p in parts]},
            )
            mocked.assert_not_awaited()
    assert response.status_code == 400
    assert "Too many parts" in response.text


@pytest.mark.asyncio
async def test_sync_pricing_rejects_invalid_mcmaster_url(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", False)
    transport = ASGITransport(app=app)
    part = Part(
        original_name="evil",
        quantity=1,
        mcmaster_url="https://evil.example/steal",
    )
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "backend.services.pricing_listing.sync_parts_pricing_from_listings",
            new_callable=AsyncMock,
        ) as mocked:
            response = await client.post(
                "/api/bom/sync-pricing",
                json={"parts": [part.model_dump()]},
            )
            mocked.assert_not_awaited()
    assert response.status_code == 400
    assert "Invalid McMaster URL" in response.text
