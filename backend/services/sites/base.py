"""Shared contracts for marketplace / design-host site ingestion adapters."""

from __future__ import annotations

from typing import Protocol

from backend.models.part import Part
from backend.models.progress import ProgressCallback
from backend.services.scraper import ScrapeResult


class SiteAdapter(Protocol):
    """Interface each design-host site package should implement for BOM ingestion.

    Scaffold only: existing API/pipeline paths stay MakerWorld-specific until a
    later slice routes through the registry. Adapters wrap scrape/parse hooks
    without duplicating site logic.
    """

    site_id: str

    def can_handle(self, url: str) -> bool:
        """Return True if this adapter owns the given project URL."""
        ...

    async def scrape(
        self,
        url: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> ScrapeResult:
        """Fetch and extract BOM-related page material for the URL."""
        ...

    def parse_bom(self, content: bytes, filename: str) -> list[Part]:
        """Parse uploaded or downloaded BOM file bytes into parts."""
        ...
