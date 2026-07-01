import asyncio
from typing import Union

from playwright.async_api import BrowserContext, Page, async_playwright
from playwright_stealth import Stealth

_browser_context: Union[BrowserContext, None] = None
_lock = asyncio.Lock()


async def _ensure_browser_context() -> BrowserContext:
    global _browser_context

    async with _lock:
        if _browser_context:
            return _browser_context

        _playwright = (
            await Stealth(navigator_user_agent=False)
            .use_async(async_playwright())
            .start()
        )
        _browser = await _playwright.chromium.launch()
        _browser_context = await _browser.new_context()

        assert _browser_context
        return _browser_context


async def get_page() -> Page:
    browser_context = await _ensure_browser_context()
    return await browser_context.new_page()
