"""Debug endpoints (active when DEBUG=1)."""

from __future__ import annotations

import os
import sys

from fastapi import APIRouter, HTTPException

from backend import config
from backend.debug_log import clear, get_entries

router = APIRouter(prefix="/debug", tags=["debug"])


def _redact_proxy_url(url: str) -> str:
    """Hide credentials embedded in proxy URLs (user:pass@host)."""
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            host_part = rest.rsplit("@", 1)[-1]
            return f"{scheme}://***@{host_part}"
    elif "@" in url:
        return f"***@{url.rsplit('@', 1)[-1]}"
    return url


def _proxy_env_snapshot() -> dict[str, str]:
    keys = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "http_proxy",
        "https_proxy",
        "ALL_PROXY",
    )
    return {
        k: _redact_proxy_url(os.environ[k])
        for k in keys
        if os.environ.get(k)
    }


def _require_debug() -> None:
    if not config.DEBUG:
        raise HTTPException(status_code=404, detail="Debug mode is disabled")


@router.get("")
async def debug_status() -> dict:
    """Return whether debug mode is on (always reachable)."""
    return {
        "debug": config.DEBUG,
        "python": sys.version.split()[0],
        "proxy_env": _proxy_env_snapshot(),
    }


@router.get("/logs")
async def debug_logs(limit: int = 100) -> dict:
    _require_debug()
    return {"entries": get_entries(limit)}


@router.delete("/logs")
async def debug_clear_logs() -> dict:
    _require_debug()
    clear()
    return {"cleared": True}
