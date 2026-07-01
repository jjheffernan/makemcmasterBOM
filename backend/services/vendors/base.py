"""Shared vendor-matching contracts — copy this pattern for new supplier sites."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from backend.models.part import Part

MatchTier = Literal[
    "catalog",
    "rule",
    "part_number",
    "filtered_browse",
    "category_search",
    "site_search",
    "api_verified",
    "not_applicable",
]

LinkKind = Literal["product", "filtered_browse", "category_search", "site_search"]


@dataclass(frozen=True)
class VendorMatchContext:
    """Normalized inputs passed into a vendor adapter."""

    query: str
    part: Part
    category_id: str = ""
    catalog_part_number: str = ""


@dataclass(frozen=True)
class VendorLink:
    """Resolved outbound link for a supplier."""

    url: str
    link_kind: LinkKind
    tier: MatchTier
    part_number: str = ""
    category_id: str = ""
    category_label: str = ""
    filter_path: str = ""
    method: str = ""
    detail_description: str = ""
    product_status: str = ""
    confidence_hint: float = 0.0
    extras: dict[str, str] = field(default_factory=dict)


class VendorAdapter(Protocol):
    """Interface each supplier package should implement."""

    vendor_id: str

    def build_link(self, ctx: VendorMatchContext) -> VendorLink:
        """Resolve the best offline link for a BOM line (no live network)."""

    async def enrich_link(self, link: VendorLink, ctx: VendorMatchContext) -> VendorLink:
        """Optional live enrichment (official API, browse tables, etc.)."""
