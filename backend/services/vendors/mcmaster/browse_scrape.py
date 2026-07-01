"""Live McMaster ProductPresentations JSON via Playwright.

Playwright discovery logic migrated from upstream mcmaster-scraper v0.2.1
(https://github.com/thedjchi/mcmaster-scraper). Archived reference:
``docs/archive/mcmaster-scraper-v0.2.1/``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from backend.services.vendors.mcmaster.urls import is_mcmaster_url

logger = logging.getLogger(__name__)

_browser_context = None
_lock = asyncio.Lock()


async def _ensure_browser_context():
    global _browser_context

    async with _lock:
        if _browser_context:
            return _browser_context

        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth

        playwright = (
            await Stealth(navigator_user_agent=False)
            .use_async(async_playwright())
            .start()
        )
        browser = await playwright.chromium.launch()
        _browser_context = await browser.new_context()
        return _browser_context


async def _new_page():
    context = await _ensure_browser_context()
    return await context.new_page()


async def fetch_product_presentations(url: str) -> dict[str, Any]:
    """
    Load a McMaster browse URL and return raw ProductPresentations JSON.

    Requires ``pip install -e '.[playwright]'`` and ``playwright install chromium``.
    """
    if not is_mcmaster_url(url):
        raise ValueError("Not a McMaster-Carr URL")

    logger.info("Finding API for McMaster product page...")
    page = await _new_page()
    try:
        await page.goto(url, wait_until="commit")

        product_api = "**/ProdPageWebPart.aspx**"
        async with page.expect_request(product_api, timeout=5000) as request:
            api_url = (await request.value).url

        logger.info("Fetching ProductPresentations JSON")
        await page.goto(api_url)

        body = await page.locator("body").text_content()
        if body is None:
            raise ValueError("Empty response from McMaster ProdPageWebPart API")

        return _extract_json_from_response(body)
    finally:
        await page.close()


def _extract_json_from_response(body: str) -> dict[str, Any]:
    start = body.find("{")
    end = body.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON found in McMaster API response")
    return json.loads(body[start : end + 1])
