"""Post-match McMaster enrichment — official API + optional browse resolution."""

from __future__ import annotations

import logging

from backend import config
from backend.models.part import Part
from backend.services.mcmaster_catalog import CatalogHit
from backend.services.vendors.mcmaster.api import McMasterApiClient, get_mcmaster_api_client
from backend.services.vendors.mcmaster.browse_fetch import resolve_part_from_browse
from backend.services.vendors.mcmaster.urls import mcmaster_product_url

logger = logging.getLogger(__name__)


def _apply_api_record(part: Part, record) -> Part:
    detail = record.detail_description or record.family_description
    reason = part.mcmaster_reason
    if detail and detail not in reason:
        reason = f"{reason} — {detail}".strip(" —")
    if record.is_discontinued:
        reason = f"{reason} — DISCONTINUED".strip(" —")
        if record.suggested_product_url:
            reason = f"{reason}; see {record.suggested_product_url}"
    return part.model_copy(
        update={
            "mcmaster_detail_description": detail,
            "mcmaster_product_status": record.product_status,
            "mcmaster_reason": reason,
            "match_tier": "api_verified",
        }
    )


async def enrich_part_with_api(part: Part, client: McMasterApiClient | None = None) -> Part:
    if not part.mcmaster_part_number or part.mcmaster_status == "not_applicable":
        return part
    api = client or get_mcmaster_api_client()
    if not api.is_configured():
        return part
    try:
        record = await api.lookup_product(part.mcmaster_part_number)
    except Exception as exc:
        logger.debug("McMaster API enrich failed for %s: %s", part.mcmaster_part_number, exc)
        return part
    if not record:
        return part
    return _apply_api_record(part, record)


async def try_resolve_part_from_browse(part: Part) -> Part:
    """
    When browse resolution is enabled and we only have a filtered browse URL,
    attempt to pick a catalog part number from the live product table.
    """
    if not config.MCMASTER_BROWSE_RESOLVE_ENABLED:
        return part
    if part.mcmaster_part_number or part.match_tier != "filtered_browse":
        return part
    if not part.mcmaster_url:
        return part
    try:
        row = await resolve_part_from_browse(part.mcmaster_url)
    except Exception as exc:
        logger.debug("McMaster browse resolve failed: %s", exc)
        return part
    if not row:
        return part
    hit = CatalogHit(
        part_number=row.part_number,
        title=str(row.fields.get("Length", row.product_type or row.part_number)),
        category=part.mcmaster_category or "screw",
        source="browse",
    )
    return part.model_copy(
        update={
            "mcmaster_part_number": hit.part_number,
            "mcmaster_url": mcmaster_product_url(hit.part_number, part.normalized_name),
            "confidence": 0.9,
            "mcmaster_status": "likely",
            "match_tier": "filtered_browse",
            "mcmaster_reason": (
                f"Resolved from filtered browse table — {hit.part_number}"
            ),
        }
    )


async def enrich_parts(parts: list[Part]) -> list[Part]:
    """Apply optional API + browse enrichment to matched parts."""
    if not parts:
        return parts
    client = get_mcmaster_api_client()
    enriched: list[Part] = []
    for part in parts:
        updated = await try_resolve_part_from_browse(part)
        updated = await enrich_part_with_api(updated, client)
        enriched.append(updated)
    return enriched
