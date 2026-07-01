"""Rate limiting for API imports and outbound MakerWorld HTTP."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request

from backend import config

# --- Outbound (MakerWorld scrapes) ---

_outbound_lock = asyncio.Lock()
_last_outbound_at: float = 0.0
_scrape_semaphore = asyncio.Semaphore(config.RATE_LIMIT_MAX_CONCURRENT_SCRAPES)


async def acquire_outbound_slot() -> None:
    """Wait for min interval + concurrent scrape slot before hitting MakerWorld."""
    if not config.RATE_LIMIT_ENABLED:
        return

    await _scrape_semaphore.acquire()
    global _last_outbound_at
    async with _outbound_lock:
        now = time.monotonic()
        wait = config.RATE_LIMIT_OUTBOUND_MIN_INTERVAL - (now - _last_outbound_at)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_outbound_at = time.monotonic()


def release_outbound_slot() -> None:
    if not config.RATE_LIMIT_ENABLED:
        return
    _scrape_semaphore.release()


class _OutboundGuard:
    async def __aenter__(self) -> None:
        await acquire_outbound_slot()

    async def __aexit__(self, *args: object) -> None:
        release_outbound_slot()


def outbound_request() -> _OutboundGuard:
    """Context manager: rate-limited MakerWorld fetch slot."""
    return _OutboundGuard()


# --- Inbound (API import endpoints) ---

_client_windows: dict[str, Deque[float]] = defaultdict(deque)
_client_lock = asyncio.Lock()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def check_import_rate_limit(request: Request) -> None:
    """Raise 429 if this client exceeds import requests per minute."""
    if not config.RATE_LIMIT_ENABLED:
        return

    key = _client_key(request)
    limit = config.RATE_LIMIT_IMPORT_PER_MINUTE
    window_seconds = 60.0
    now = time.monotonic()

    async with _client_lock:
        hits = _client_windows[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = int(window_seconds - (now - hits[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Import rate limit exceeded ({limit} per minute). "
                    f"Try again in {retry_after}s."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)


async def check_feedback_rate_limit(request: Request) -> None:
    """Raise 429 if this client exceeds feedback submissions per minute."""
    if not config.RATE_LIMIT_ENABLED:
        return

    key = f"feedback:{_client_key(request)}"
    limit = 10
    window_seconds = 60.0
    now = time.monotonic()

    async with _client_lock:
        hits = _client_windows[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = int(window_seconds - (now - hits[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Feedback rate limit exceeded ({limit} per minute). "
                    f"Try again in {retry_after}s."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)


def reset_rate_limits_for_tests() -> None:
    """Clear state between tests."""
    global _last_outbound_at, _scrape_semaphore
    _last_outbound_at = 0.0
    _client_windows.clear()
    _scrape_semaphore = asyncio.Semaphore(config.RATE_LIMIT_MAX_CONCURRENT_SCRAPES)
