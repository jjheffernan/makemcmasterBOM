"""MakerWorld site adapter — thin wrap over existing scrape/parse entry points."""

from __future__ import annotations

from urllib.parse import urlparse

from backend.models.part import Part
from backend.models.progress import ProgressCallback
from backend.services.parser import parse_bom_bytes
from backend.services.scraper import ScrapeResult, scrape_project


class MakerWorldAdapter:
    """Delegates to ``backend.services.scraper`` / ``parser`` — no duplicated logic."""

    site_id = "makerworld"

    def can_handle(self, url: str) -> bool:
        host = urlparse(url.strip()).netloc.lower()
        return "makerworld.com" in host

    async def scrape(
        self,
        url: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> ScrapeResult:
        return await scrape_project(url, on_progress=on_progress)

    def parse_bom(self, content: bytes, filename: str) -> list[Part]:
        return parse_bom_bytes(content, filename)
