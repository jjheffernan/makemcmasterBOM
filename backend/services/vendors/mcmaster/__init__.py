"""McMaster-Carr vendor adapter."""

from backend.services.vendors.mcmaster.api import (
    McMasterApiClient,
    McMasterProductRecord,
    get_mcmaster_api_client,
    parse_product_payload,
)
from backend.services.vendors.mcmaster.browse_parse import BrowseRow, parse_product_presentations
from backend.services.vendors.mcmaster.enrichment import enrich_parts
from backend.services.vendors.mcmaster.filters import BrowseFilterSet, build_fastener_filters
from backend.services.vendors.mcmaster.part_numbers import extract_part_numbers, is_valid_part_number
from backend.services.vendors.mcmaster.tiers import resolve_mcmaster_link
from backend.services.vendors.mcmaster.urls import filtered_browse_url, mcmaster_product_url

__all__ = [
    "BrowseFilterSet",
    "BrowseRow",
    "McMasterApiClient",
    "McMasterProductRecord",
    "build_fastener_filters",
    "enrich_parts",
    "extract_part_numbers",
    "filtered_browse_url",
    "get_mcmaster_api_client",
    "is_valid_part_number",
    "mcmaster_product_url",
    "parse_product_payload",
    "parse_product_presentations",
    "resolve_mcmaster_link",
]
