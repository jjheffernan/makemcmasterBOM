"""Live McMaster browse tables via in-house Playwright scrape + parser."""

from __future__ import annotations

import logging

from backend import config
from backend.services.vendors.mcmaster.browse_parse import BrowseRow, parse_product_presentations
from backend.services.vendors.mcmaster.browse_scrape import fetch_product_presentations
from backend.services.vendors.mcmaster.urls import is_mcmaster_url

logger = logging.getLogger(__name__)


async def fetch_browse_rows(url: str, *, refresh: bool = False) -> list[BrowseRow]:
    """
    Load a McMaster browse URL and return product table rows.

    Requires ``[playwright]`` extra and ``MCMASTER_BROWSE_RESOLVE_ENABLED=1``.
    ``refresh`` is accepted for API compatibility (no disk cache yet).
    """
    del refresh  # reserved for future browse response caching

    if not is_mcmaster_url(url):
        raise ValueError("Not a McMaster-Carr URL")

    if not config.MCMASTER_BROWSE_RESOLVE_ENABLED:
        raise RuntimeError(
            "Live McMaster browse resolution is disabled "
            "(set MCMASTER_BROWSE_RESOLVE_ENABLED=1)"
        )

    logger.info("Fetching McMaster browse table: %s", url)
    payload = await fetch_product_presentations(url)
    return parse_product_presentations(payload)


async def resolve_part_from_browse(
    browse_url: str,
    *,
    part_number_hint: str = "",
    refresh: bool = False,
) -> BrowseRow | None:
    """Return the first matching browse row (by hint or sole row)."""
    rows = await fetch_browse_rows(browse_url, refresh=refresh)
    if not rows:
        return None
    if part_number_hint:
        target = part_number_hint.strip().upper()
        for row in rows:
            if row.part_number.upper() == target:
                return row
    if len(rows) == 1:
        return rows[0]
    return None
