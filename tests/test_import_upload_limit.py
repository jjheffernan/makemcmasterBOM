"""Upload size limits for POST /api/import/file."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from starlette.requests import Request

from backend import config
from backend.routers.import_router import (
    _reject_if_content_length_too_large,
    _upload_too_large_detail,
)

def _request_with_content_length(value: str | None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if value is not None:
        headers.append((b"content-length", value.encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/import/file",
        "raw_path": b"/api/import/file",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    return Request(scope)


def test_reject_if_content_length_too_large() -> None:
    max_bytes = 100
    _reject_if_content_length_too_large(_request_with_content_length(None), max_bytes)
    _reject_if_content_length_too_large(_request_with_content_length("50"), max_bytes)
    _reject_if_content_length_too_large(_request_with_content_length("not-int"), max_bytes)

    with pytest.raises(HTTPException) as exc_info:
        _reject_if_content_length_too_large(_request_with_content_length("101"), max_bytes)
    assert exc_info.value.status_code == 413
    assert exc_info.value.detail == _upload_too_large_detail(max_bytes)


@pytest.mark.asyncio
async def test_import_file_rejects_oversized_upload(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oversized body yields HTTP 413 before parse (Content-Length and/or capped read)."""
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 64)
    payload = b"Qty,Part Name,Specification\n" + (b"2,M3 bolt,Stainless\n" * 20)
    assert len(payload) > 64

    response = await api_client.post(
        "/api/import/file",
        files={"file": ("bom.csv", payload, "text/csv")},
    )
    assert response.status_code == 413
    assert "64" in response.json()["detail"]


@pytest.mark.asyncio
async def test_import_file_accepts_under_limit(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 10 * 1024)
    csv_content = b"Qty,Part Name,Specification\n2,M3 bolt,Stainless\n"
    response = await api_client.post(
        "/api/import/file",
        files={"file": ("bom.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    assert len(response.json()["project"]["parts"]) == 1
