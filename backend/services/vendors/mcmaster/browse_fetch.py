"""Live McMaster browse tables via in-house Playwright scrape + parser."""

from __future__ import annotations

import asyncio
import logging

from backend import config
from backend.models.part import Part
from backend.services.vendors.mcmaster.browse_row_select import pick_best_browse_row
from backend.services.vendors.mcmaster.browse_parse import BrowseRow, parse_product_presentations
from backend.services.vendors.mcmaster.browse_scrape import fetch_product_presentations
from backend.services.vendors.mcmaster.urls import is_mcmaster_url

logger = logging.getLogger(__name__)

_browse_rows_cache: dict[str, list[BrowseRow]] = {}
_browse_cache_lock = asyncio.Lock()


async def fetch_browse_rows(url: str, *, refresh: bool = False) -> list[BrowseRow]:
    """
    Load a McMaster browse URL and return product table rows.

    Requires ``[playwright]`` extra and ``MCMASTER_BROWSE_RESOLVE_ENABLED=1``.
    Responses are cached in-process for the duration of the server process.
    """
    if not is_mcmaster_url(url):
        raise ValueError("Not a McMaster-Carr URL")

    if not config.MCMASTER_BROWSE_RESOLVE_ENABLED:
        raise RuntimeError(
            "Live McMaster browse resolution is disabled "
            "(set MCMASTER_BROWSE_RESOLVE_ENABLED=1)"
        )

    if not refresh:
        cached = _browse_rows_cache.get(url)
        if cached is not None:
            logger.debug("McMaster browse cache hit: %s", url)
            return cached

    async with _browse_cache_lock:
        if not refresh:
            cached = _browse_rows_cache.get(url)
            if cached is not None:
                return cached

        logger.info("Fetching McMaster browse table: %s", url)
        payload = await fetch_product_presentations(url)
        rows = parse_product_presentations(payload)
        _browse_rows_cache[url] = rows
        return rows


async def resolve_part_from_browse(
    browse_url: str,
    *,
    part: Part | None = None,
    part_number_hint: str = "",
    refresh: bool = False,
) -> BrowseRow | None:
    """Return the best browse row for a BOM line (live McMaster product table)."""
    rows = await fetch_browse_rows(browse_url, refresh=refresh)
    if not rows:
        return None
    if part is not None:
        from backend.services.vendors.mcmaster.browse_row_select import pick_lowest_price_row

        return pick_lowest_price_row(part, rows, browse_url=browse_url)
    if part_number_hint:
        target = part_number_hint.strip().upper()
        for row in rows:
            if row.part_number.upper() == target:
                return row
    if len(rows) == 1:
        return rows[0]
    if "thread-size~" in browse_url.lower() and rows:
        return rows[0]
    return None
