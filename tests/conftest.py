"""Shared pytest fixtures — isolation and HTTP client helpers."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

REPO_ROOT = Path(__file__).resolve().parents[1]
# Vendored mcmaster-scraper diskcache (sandbox-safe, repo-local)
os.environ.setdefault("XDG_CACHE_HOME", str(REPO_ROOT / ".cache"))

from backend.api import store
from backend.main import app
from backend.rate_limit import reset_rate_limits_for_tests


@pytest.fixture(autouse=True)
def _isolated_store() -> None:
    """Prevent in-memory project history from leaking between tests."""
    store.clear_all()
    yield
    store.clear_all()


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    """Reset per-IP and outbound rate limiter state between tests."""
    reset_rate_limits_for_tests()
    yield
    reset_rate_limits_for_tests()


@pytest.fixture
async def api_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
