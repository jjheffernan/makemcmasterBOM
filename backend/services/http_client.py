"""Shared HTTP client for outbound requests (MakerWorld, BOM files)."""

from __future__ import annotations

import os

import httpx
from tenacity import RetryError

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

# Prevent inherited shell/Cursor proxy vars from breaking direct fetches
for _proxy_var in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
):
    os.environ.pop(_proxy_var, None)


def unwrap_exception(exc: BaseException) -> BaseException:
    """Flatten tenacity RetryError and exception chains."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, RetryError) and current.last_attempt.failed:
            current = current.last_attempt.exception()
            continue
        if current.__cause__ is not None and id(current.__cause__) not in seen:
            current = current.__cause__
            continue
        break
    return current or exc


def outbound_client(**kwargs) -> httpx.AsyncClient:
    """Direct HTTP client — never routes through system or env proxies."""
    headers = kwargs.pop("headers", None)
    merged = {**BROWSER_HEADERS, **(headers or {})}
    return httpx.AsyncClient(
        trust_env=False,
        proxy=None,
        headers=merged,
        **kwargs,
    )


def format_fetch_error(exc: BaseException) -> str:
    """User-facing message for scrape/download failures."""
    exc = unwrap_exception(exc)
    if isinstance(exc, RetryError):
        exc = unwrap_exception(exc)
    if isinstance(exc, httpx.ProxyError):
        return (
            "A network proxy blocked the request to MakerWorld. "
            "Restart with ./scripts/dev.sh (uses Playwright fallback) or set SCRAPER=playwright."
        )
    if isinstance(exc, RuntimeError) and "Playwright" in str(exc):
        return str(exc)
    if isinstance(exc, httpx.ConnectError):
        return f"Could not connect to MakerWorld: {exc}"
    if isinstance(exc, httpx.TimeoutException):
        return "MakerWorld request timed out — try again in a moment."
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 404:
            return "MakerWorld project not found (404) — check the URL."
        if code == 403:
            return (
                "MakerWorld blocked the HTTP request (403). "
                "Install Playwright: pip install -e '.[playwright]' && playwright install chromium"
            )
        return f"MakerWorld returned HTTP {code}."
    return str(exc)
