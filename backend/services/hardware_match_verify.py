"""Post-match size/length verification and catalog correction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.models.part import Part
from backend.services.hardware_spec import (
    MetricFastenerSpec,
    all_fastener_specs,
    build_explicit_fastener_query,
    lengths_match,
    primary_fastener_spec,
    sizes_match,
    spec_from_catalog_hit,
)
from backend.services.mcmaster_catalog import CatalogHit, catalog_lookup
from backend.services.mcmaster_handler import McMasterLink, build_mcmaster_link

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


@dataclass(frozen=True)
class HardwareMatchCheck:
    status: HardwareMatchStatus
    message: str
    expected: MetricFastenerSpec | None = None
    matched: MetricFastenerSpec | None = None
    corrected: bool = False


def _conflicting_specs(part: Part) -> list[MetricFastenerSpec]:
    specs = all_fastener_specs(part)
    if len(specs) <= 1:
        return []

    diameters = {s.diameter_mm for s in specs}
    lengths = {s.length_mm for s in specs if s.length_mm is not None}
    if len(diameters) > 1 or len(lengths) > 1:
        return specs
    return []


def check_size(part: Part, matched: MetricFastenerSpec | None) -> HardwareMatchCheck | None:
    expected = primary_fastener_spec(part)
    if not expected or not matched:
        return None
    if sizes_match(expected, matched):
        return None
    return HardwareMatchCheck(
        status="size_mismatch",
        message=(
            f"Size mismatch — BOM specifies {expected.label()} "
            f"but catalog match is {matched.label()}"
        ),
        expected=expected,
        matched=matched,
    )


def check_length(part: Part, matched: MetricFastenerSpec | None) -> HardwareMatchCheck | None:
    expected = primary_fastener_spec(part)
    if not expected or not matched:
        return None
    if expected.length_mm is None:
        return HardwareMatchCheck(
            status="length_unknown",
            message="Length not found in BOM — verify McMaster part length manually",
            expected=expected,
            matched=matched,
        )
    if lengths_match(expected, matched):
        return None
    return HardwareMatchCheck(
        status="length_mismatch",
        message=(
            f"Length mismatch — BOM specifies {expected.length_mm} mm "
            f"but catalog match is {matched.length_mm} mm"
        ),
        expected=expected,
        matched=matched,
    )


def verify_hardware_match(
    part: Part,
    *,
    hit: CatalogHit | None,
) -> HardwareMatchCheck:
    if hit is None:
        expected = primary_fastener_spec(part)
        if expected and expected.length_mm is None and expected.kind == "screw":
            return HardwareMatchCheck(
                status="length_unknown",
                message="No catalog match — length not specified in BOM",
                expected=expected,
            )
        return HardwareMatchCheck(status="unchecked", message="")

    conflicts = _conflicting_specs(part)
    if conflicts:
        labels = ", ".join(s.label() for s in conflicts)
        return HardwareMatchCheck(
            status="spec_conflict",
            message=f"Conflicting hardware specs in BOM fields: {labels}",
            expected=conflicts[0],
        )

    expected = primary_fastener_spec(part)
    matched = spec_from_catalog_hit(hit)
    if not expected:
        return HardwareMatchCheck(status="unchecked", message="", matched=matched)

    if not matched:
        if expected.length_mm is None and expected.kind == "screw":
            return HardwareMatchCheck(
                status="length_unknown",
                message="Catalog hit has no parseable length — verify manually",
                expected=expected,
            )
        return HardwareMatchCheck(status="unchecked", message="", expected=expected)

    size_issue = check_size(part, matched)
    if size_issue:
        return size_issue

    length_issue = check_length(part, matched)
    if length_issue and length_issue.status == "length_mismatch":
        return length_issue

    if length_issue and length_issue.status == "length_unknown":
        return length_issue

    return HardwareMatchCheck(
        status="verified",
        message="Size and length verified against catalog",
        expected=expected,
        matched=matched,
    )


def correct_hardware_match(
    part: Part,
    *,
    query: str,
    hit: CatalogHit | None,
    link: McMasterLink,
    check: HardwareMatchCheck,
) -> tuple[CatalogHit | None, McMasterLink, HardwareMatchCheck]:
    """
    Attempt catalog re-lookup when size/length mismatches are recoverable.

    Returns possibly updated hit/link and check state (``corrected`` on success).
    """
    if check.status not in {"size_mismatch", "length_mismatch", "spec_conflict"}:
        return hit, link, check

    expected = primary_fastener_spec(part)
    if not expected:
        return hit, link, check

    if check.status == "spec_conflict":
        expected = check.expected or expected

    if expected.length_mm is None and expected.kind == "screw":
        return hit, link, check

    corrected_query = build_explicit_fastener_query(expected, hint_text=part.original_name)
    corrected_hit = catalog_lookup(corrected_query)
    if not corrected_hit:
        return hit, link, check

    corrected_matched = spec_from_catalog_hit(corrected_hit)
    if not corrected_matched:
        return hit, link, check

    if not sizes_match(expected, corrected_matched):
        return hit, link, check
    if expected.length_mm is not None and not lengths_match(expected, corrected_matched):
        return hit, link, check

    if hit and corrected_hit.part_number == hit.part_number:
        return hit, link, HardwareMatchCheck(
            status="verified",
            message="Size and length verified against catalog",
            expected=expected,
            matched=corrected_matched,
        )

    corrected_link = build_mcmaster_link(corrected_query, catalog_hit=corrected_hit)
    return (
        corrected_hit,
        corrected_link,
        HardwareMatchCheck(
            status="corrected",
            message=(
                f"Corrected catalog match to {corrected_matched.label()} "
                f"({corrected_hit.part_number})"
            ),
            expected=expected,
            matched=corrected_matched,
            corrected=True,
        ),
    )


def apply_match_check_to_part(
    part: Part,
    *,
    check: HardwareMatchCheck,
    confidence: float,
    base_reason: str,
) -> tuple[Part, float]:
    """Merge verification state into Part fields and adjust confidence."""
    reason = base_reason
    status = check.status
    new_confidence = confidence

    if check.message:
        reason = f"{check.message}. {base_reason}".strip(". ") if base_reason else check.message

    if status == "size_mismatch":
        new_confidence = min(confidence, 0.35)
    elif status == "length_mismatch":
        new_confidence = min(confidence, 0.45)
    elif status == "spec_conflict":
        new_confidence = min(confidence, 0.4)
    elif status == "length_unknown" and confidence >= 0.85:
        new_confidence = min(confidence, 0.78)
    elif status == "corrected":
        new_confidence = min(max(confidence, 0.88), 0.92)
    elif status == "verified" and confidence >= 0.9:
        new_confidence = confidence

    mcmaster_status = part.mcmaster_status
    if status in {"size_mismatch", "length_mismatch", "spec_conflict"}:
        mcmaster_status = "possible"
    elif status == "length_unknown":
        mcmaster_status = "likely" if new_confidence >= 0.7 else "possible"

    return (
        part.model_copy(
            update={
                "hardware_diameter_mm": check.expected.diameter_mm if check.expected else None,
                "hardware_length_mm": (
                    float(check.expected.length_mm)
                    if check.expected and check.expected.length_mm is not None
                    else None
                ),
                "hardware_match_status": status,
                "mcmaster_reason": reason,
                "mcmaster_status": mcmaster_status,
            }
        ),
        new_confidence,
    )
