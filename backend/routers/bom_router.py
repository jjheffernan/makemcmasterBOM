from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from backend.api.store import get, list_history, update
from backend.models.part import Part
from backend.models.project import Project, ProjectHistoryItem
from backend.services.parsers.helpers.spec_metadata import SPEC_HINTS, normalize_part_specification
from backend.services.parsers.helpers.specification_checks import check_parts_specifications
from backend.services.pipeline import parts_to_csv

router = APIRouter(prefix="/bom", tags=["bom"])


class UpdateBomRequest(BaseModel):
    parts: list[Part]


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
    updated = project.model_copy(update={"parts": normalized_parts})
    update(project_id, updated)
    return updated


@router.get("/{project_id}/export")
async def export_csv(project_id: str) -> Response:
    project = get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    csv_content = parts_to_csv(project.parts)
    filename = f"{project.title or 'bom'}.csv".replace(" ", "_")
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
