import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from backend import config
from backend.main import app
from backend.rate_limit import check_import_rate_limit


def _mock_request(host: str = "127.0.0.1") -> MagicMock:
    req = MagicMock()
    req.client.host = host
    req.headers.get.return_value = None
    return req


@pytest.mark.asyncio
async def test_import_rate_limit_blocks_excess(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config, "RATE_LIMIT_IMPORT_PER_MINUTE", 2)

    await check_import_rate_limit(_mock_request())
    await check_import_rate_limit(_mock_request())

    with pytest.raises(HTTPException) as exc:
        await check_import_rate_limit(_mock_request())
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


@pytest.mark.asyncio
async def test_import_rate_limit_disabled(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(config, "RATE_LIMIT_IMPORT_PER_MINUTE", 1)
    for _ in range(5):
        await check_import_rate_limit(_mock_request())


@pytest.mark.asyncio
async def test_outbound_min_interval(monkeypatch):
    from backend.rate_limit import outbound_request

    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(config, "RATE_LIMIT_OUTBOUND_MIN_INTERVAL", 0.05)

    async with outbound_request():
        pass
    start = asyncio.get_event_loop().time()
    async with outbound_request():
        pass
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed >= 0.04


@pytest.mark.asyncio
async def test_health_reports_rate_limit_config():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    body = response.json()
    assert body["rate_limit"]["enabled"] is True
    assert body["rate_limit"]["import_per_minute"] >= 1
