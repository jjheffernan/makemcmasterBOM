"""Post-match McMaster enrichment — live browse tables + optional B2B API."""

from __future__ import annotations

import logging

from backend import config
from backend.models.part import Part
from backend.models.progress import ProgressCallback, StageEvent
from backend.services.vendors.mcmaster.api import McMasterApiClient, get_mcmaster_api_client
from backend.services.vendors.mcmaster.browse_finish_hydrate import hydrate_part_from_browse
from backend.services.vendors.mcmaster.hydration_session import HydrationSession

logger = logging.getLogger(__name__)


def _emit(on_progress: ProgressCallback | None, event: StageEvent) -> None:
    if on_progress:
        on_progress(event)


async def try_resolve_part_from_browse(
    part: Part,
    *,
    session: HydrationSession | None = None,
) -> Part:
    """
    Resolve SKUs, finish variants, and listing prices from live McMaster tables.
    """
    if not config.MCMASTER_BROWSE_RESOLVE_ENABLED:
        return part
    if part.mcmaster_status == "not_applicable":
        return part

    has_browse = (
        part.match_tier in {"filtered_browse", "category_search"}
        or bool(part.browse_finish_options)
    )
    if not has_browse and not (
        part.mcmaster_url and "thread-size~" in part.mcmaster_url.lower()
    ):
        return part

    try:
        return await hydrate_part_from_browse(part, session=session)
    except Exception as exc:
        logger.debug("McMaster browse hydrate failed: %s", exc)
        return part


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


def _part_label(part: Part) -> str:
    return part.original_name or part.normalized_name or "part"


async def enrich_parts(
    parts: list[Part],
    *,
    on_progress: ProgressCallback | None = None,
) -> list[Part]:
    """Apply live browse hydrate, optional API, and listing price fallback."""
    if not parts:
        _emit(
            on_progress,
            StageEvent(
                stage="enrich_mcmaster",
                status="skipped",
                message="No parts to hydrate",
            ),
        )
        return parts

    from backend.services.pricing_listing import sync_part_pricing_from_listing

    enrichable = [
        part
        for part in parts
        if part.mcmaster_status != "not_applicable"
        and (
            part.match_tier in {"filtered_browse", "category_search"}
            or part.browse_finish_options
            or part.mcmaster_url
        )
    ]
    total = len(enrichable)
    _emit(
        on_progress,
        StageEvent(
            stage="enrich_mcmaster",
            status="running",
            message=(
                f"Fetching live McMaster listings for {total} hardware line"
                f"{'' if total == 1 else 's'}…"
                if total
                else "No McMaster hardware lines need live hydration"
            ),
            debug={"part_total": total, "part_index": -1} if total else None,
        ),
    )

    client = get_mcmaster_api_client()
    enriched: list[Part] = []
    hydrated_count = 0
    priced_count = 0
    enrich_index = 0
    session = HydrationSession()

    for part in parts:
        if part.mcmaster_status == "not_applicable":
            enriched.append(part)
            continue

        needs_live = (
            part.match_tier in {"filtered_browse", "category_search"}
            or part.browse_finish_options
            or part.mcmaster_url
        )
        if needs_live and config.MCMASTER_BROWSE_RESOLVE_ENABLED:
            enrich_index += 1
            _emit(
                on_progress,
                StageEvent(
                    stage="enrich_mcmaster",
                    status="running",
                    message=(
                        f"Part {enrich_index}/{total}: {_part_label(part)} "
                        "— loading McMaster table…"
                    ),
                    debug={
                        "part_index": enrich_index - 1,
                        "part_total": total,
                        "part_name": _part_label(part),
                    },
                ),
            )

        updated = await try_resolve_part_from_browse(part, session=session)
        if updated.mcmaster_part_number and not part.mcmaster_part_number:
            hydrated_count += 1
        updated = await enrich_part_with_api(updated, client)
        if not updated.price_source and not updated.unit_cost:
            updated = await sync_part_pricing_from_listing(updated)
            if updated.price_source or updated.unit_cost:
                priced_count += 1
        elif updated.price_source and not part.price_source:
            priced_count += 1
        enriched.append(updated)

    if total == 0:
        _emit(
            on_progress,
            StageEvent(
                stage="enrich_mcmaster",
                status="skipped",
                message="No McMaster hardware lines need live hydration",
            ),
        )
    else:
        _emit(
            on_progress,
            StageEvent(
                stage="enrich_mcmaster",
                status="done",
                message=(
                    f"Hydrated {hydrated_count} SKUs, priced {priced_count} lines "
                    f"from live McMaster listings"
                ),
            ),
        )
    return enriched
