"""McMaster-Carr Product Information API client — re-export from vendor package."""

from backend.services.vendors.mcmaster.api import (
    McMasterApiClient,
    McMasterApiError,
    McMasterProductRecord,
    McMasterSpecification,
    get_mcmaster_api_client,
    parse_product_payload,
)
from backend.services.vendors.mcmaster.urls import mcmaster_product_url

__all__ = [
    "McMasterApiClient",
    "McMasterApiError",
    "McMasterProductRecord",
    "McMasterSpecification",
    "get_mcmaster_api_client",
    "parse_product_payload",
    "product_url_from_api_payload",
]


def product_url_from_api_payload(payload: dict) -> str:
    part_number = payload.get("PartNumber", "")
    return mcmaster_product_url(str(part_number)) if part_number else ""
