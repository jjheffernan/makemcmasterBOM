"""Fetch MakerWorld HTML — httpx first, Playwright browser fallback."""

from __future__ import annotations

import asyncio
import os
from typing import Literal

import httpx

from backend.debug_log import record
from backend.rate_limit import outbound_request
from backend.services.http_client import BROWSER_HEADERS, outbound_client, unwrap_exception

ScraperMode = Literal["auto", "httpx", "playwright"]

_playwright = None
_browser = None
_browser_lock = asyncio.Lock()


def scraper_mode() -> ScraperMode:
    value = os.getenv("SCRAPER", "auto").strip().lower()
    if value in {"playwright", "browser"}:
        return "playwright"
    if value == "httpx":
        return "httpx"
    return "auto"


async def _fetch_httpx(url: str) -> str:
    async with outbound_request():
        async with outbound_client(follow_redirects=True, timeout=45.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text


async def _ensure_playwright_browser():
    global _playwright, _browser
    async with _browser_lock:
        if _browser is not None:
            return _browser
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is required to scrape MakerWorld from this environment. "
                "Run: pip install -e '.[playwright]' && playwright install chromium"
            ) from exc

        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--no-proxy-server", "--proxy-server=direct://"],
        )
        return _browser


async def _fetch_playwright(url: str) -> str:
    async with outbound_request():
        browser = await _ensure_playwright_browser()
        context = await browser.new_context(
            user_agent=BROWSER_HEADERS["User-Agent"],
            locale="en-US",
            extra_http_headers={
                k: v
                for k, v in BROWSER_HEADERS.items()
                if k != "User-Agent"
            },
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_selector(
                "#__NEXT_DATA__",
                state="attached",
                timeout=30_000,
            )
            return await page.content()
        finally:
            await context.close()


def _should_browser_fallback(exc: BaseException) -> bool:
    root = unwrap_exception(exc)
    if isinstance(root, httpx.ProxyError):
        return True
    if isinstance(root, httpx.HTTPStatusError):
        return root.response.status_code in {403, 429}
    if isinstance(root, (httpx.ConnectError, httpx.ReadError)):
        return True
    return False


async def fetch_makerworld_html(url: str) -> tuple[str, str]:
    """
    Return (html, method) where method is 'httpx' or 'playwright'.
    """
    mode = scraper_mode()

    if mode == "playwright":
        record("scrape", "Fetching via Playwright", data={"url": url})
        html = await _fetch_playwright(url)
        return html, "playwright"

    if mode == "httpx":
        html = await _fetch_httpx(url)
        return html, "httpx"

    # auto
    try:
        html = await _fetch_httpx(url)
        if "__NEXT_DATA__" not in html:
            record("scrape", "No __NEXT_DATA__ in httpx response; trying Playwright")
            html = await _fetch_playwright(url)
            return html, "playwright"
        return html, "httpx"
    except Exception as exc:
        if not _should_browser_fallback(exc):
            raise
        root = unwrap_exception(exc)
        record(
            "scrape",
            "httpx failed; retrying with Playwright",
            data={"url": url, "error": str(root), "type": type(root).__name__},
        )
        html = await _fetch_playwright(url)
        return html, "playwright"


async def shutdown_browser() -> None:
    global _playwright, _browser
    async with _browser_lock:
        if _browser is not None:
            await _browser.close()
            _browser = None
        if _playwright is not None:
            await _playwright.stop()
            _playwright = None
