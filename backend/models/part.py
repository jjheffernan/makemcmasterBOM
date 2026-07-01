from typing import Literal

from pydantic import BaseModel, Field

McMasterStatus = Literal["likely", "possible", "unlikely", "not_applicable"]
HardwareMatchStatus = Literal[
    "verified",
    "corrected",
    "size_mismatch",
    "length_mismatch",
    "spec_conflict",
    "length_unknown",
    "unchecked",
    "not_applicable",
]


class MatchAlternative(BaseModel):
    """Secondary McMaster link guess for the same BOM line."""

    mcmaster_url: str
    mcmaster_part_number: str = ""
    mcmaster_category: str = ""
    match_tier: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_low: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_high: float | None = Field(default=None, ge=0.0, le=1.0)
    mcmaster_reason: str = ""


class BrowseFinishOption(BaseModel):
    """Same thread/length filtered browse with a different material finish."""

    finish_id: str
    label: str
    mcmaster_url: str


class Part(BaseModel):
    quantity: float = 1
    original_name: str = ""
    normalized_name: str = ""
    specification: str = ""
    notes: str = ""
    mcmaster_url: str = ""
    mcmaster_part_number: str = ""
    mcmaster_category: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_low: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_high: float | None = Field(default=None, ge=0.0, le=1.0)
    mcmaster_status: McMasterStatus = "possible"
    mcmaster_reason: str = ""
    match_tier: str = ""
    match_alternatives: list[MatchAlternative] = Field(default_factory=list)
    browse_finish_options: list[BrowseFinishOption] = Field(default_factory=list)
    selected_finish_id: str = ""
    mcmaster_detail_description: str = ""
    mcmaster_product_status: str = ""
    hardware_diameter_mm: float | None = None
    hardware_length_mm: float | None = None
    hardware_match_status: HardwareMatchStatus = "unchecked"
