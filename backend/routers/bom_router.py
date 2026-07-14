from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from backend import config
from backend.api.store import get, list_history, update
from backend.models.part import Part
from backend.models.project import Project, ProjectHistoryItem
from backend.rate_limit import check_sync_pricing_rate_limit
from backend.services.parsers.helpers.spec_metadata import SPEC_HINTS, normalize_part_specification
from backend.services.parsers.helpers.specification_checks import check_parts_specifications
from backend.services.pipeline import parts_to_csv, parts_to_tsv, parts_to_xlsx
from backend.services.vendors.mcmaster.urls import is_mcmaster_url

router = APIRouter(prefix="/bom", tags=["bom"])

ExportFormat = Literal["csv", "tsv", "xlsx"]

_EXPORT_HANDLERS: dict[ExportFormat, tuple[str, str]] = {
    "csv": ("text/csv", "csv"),
    "tsv": ("text/tab-separated-values", "tsv"),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    ),
}


class UpdateBomRequest(BaseModel):
    parts: list[Part]
    bom_headings: dict[str, str] | None = None


class ValidateSpecificationsRequest(BaseModel):
    parts: list[Part]


class ValidateSpecificationsResponse(BaseModel):
    issues: list["SpecificationIssueOut"]
    error_count: int
    warning_count: int


class SpecificationIssueOut(BaseModel):
    part_index: int
    original_name: str
    specification: str
    code: str
    message: str
    severity: str
    hint: str = ""


class SpecGuidanceResponse(BaseModel):
    hints: dict[str, str]


class BomHistoryResponse(BaseModel):
    items: list[ProjectHistoryItem]
    limit: int


class SyncPricingRequest(BaseModel):
    parts: list[Part]


class SyncPricingResponse(BaseModel):
    parts: list[Part]
    synced_count: int


@router.get("/spec-guidance", response_model=SpecGuidanceResponse)
async def get_spec_guidance() -> SpecGuidanceResponse:
    return SpecGuidanceResponse(hints=dict(SPEC_HINTS))


@router.post("/validate-specifications", response_model=ValidateSpecificationsResponse)
async def validate_specifications(
    body: ValidateSpecificationsRequest,
) -> ValidateSpecificationsResponse:
    issues = check_parts_specifications(body.parts)
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    return ValidateSpecificationsResponse(
        issues=[
            SpecificationIssueOut(
                part_index=i.part_index,
                original_name=i.original_name,
                specification=i.specification,
                code=i.code,
                message=i.message,
                severity=i.severity,
                hint=i.hint,
            )
            for i in issues
        ],
        error_count=errors,
        warning_count=warnings,
    )


@router.post(
    "/sync-pricing",
    response_model=SyncPricingResponse,
    dependencies=[Depends(check_sync_pricing_rate_limit)],
)
async def sync_pricing(body: SyncPricingRequest) -> SyncPricingResponse:
    """Pull price tiers from McMaster hardware listings (API or browse table)."""
    from backend.services.pricing_listing import sync_parts_pricing_from_listings

    if len(body.parts) > config.SYNC_PRICING_MAX_PARTS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Too many parts for sync-pricing "
                f"({len(body.parts)} > {config.SYNC_PRICING_MAX_PARTS})."
            ),
        )

    for part in body.parts:
        url = (part.mcmaster_url or "").strip()
        if url and not is_mcmaster_url(url):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid McMaster URL for part {part.original_name!r}",
            )

    updated = await sync_parts_pricing_from_listings(body.parts)
    synced = sum(
        1
        for before, after in zip(body.parts, updated, strict=True)
        if after.price_source and after.price_source != before.price_source
        or (
            after.price_batch_cost != before.price_batch_cost
            or after.unit_cost != before.unit_cost
        )
    )
    return SyncPricingResponse(parts=updated, synced_count=synced)


@router.get("/history", response_model=BomHistoryResponse)
async def get_bom_history() -> BomHistoryResponse:
    from backend.api.store import MAX_HISTORY

    return BomHistoryResponse(items=list_history(), limit=MAX_HISTORY)


@router.get("/{project_id}", response_model=Project)
async def get_bom(project_id: str) -> Project:
    project = get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=Project)
async def update_bom(project_id: str, body: UpdateBomRequest) -> Project:
    project = get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    normalized_parts = [normalize_part_specification(p) for p in body.parts]
    updates: dict[str, object] = {"parts": normalized_parts}
    if body.bom_headings is not None:
        updates["bom_headings"] = body.bom_headings
    updated = project.model_copy(update=updates)
    update(project_id, updated)
    return updated


@router.get("/{project_id}/export")
async def export_bom(
    project_id: str,
    format: ExportFormat = Query("csv"),
) -> Response:
    project = get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    media_type, ext = _EXPORT_HANDLERS[format]
    if format == "csv":
        content: str | bytes = parts_to_csv(project.parts)
    elif format == "tsv":
        content = parts_to_tsv(project.parts)
    else:
        content = parts_to_xlsx(project.parts)

    stem = (project.title or "bom").replace(" ", "_")
    filename = f"{stem}.{ext}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
