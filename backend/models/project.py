from typing import Literal

from pydantic import BaseModel

from backend.models.part import Part

BomStatus = Literal["file", "embedded", "description", "none", "upload"]


class Project(BaseModel):
    title: str = ""
    makerworld_url: str = ""
    description: str = ""
    thumbnail_url: str = ""
    parts: list[Part] = []
    bom_status: BomStatus = "none"
    warnings: list[str] = []
    bom_headings: dict[str, str] = {}


class ProjectHistoryItem(BaseModel):
    project_id: str
    title: str
    thumbnail_url: str = ""
    makerworld_url: str = ""
    parts_count: int = 0
    bom_status: BomStatus = "none"
    imported_at: str
    updated_at: str
