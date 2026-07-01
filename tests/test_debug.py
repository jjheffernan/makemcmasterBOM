import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_debug_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/debug")
    assert response.status_code == 200
    body = response.json()
    assert "debug" in body


@pytest.mark.asyncio
async def test_debug_logs_disabled_by_default():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/debug/logs")
    assert response.status_code == 404
