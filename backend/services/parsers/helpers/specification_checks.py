"""Validate BOM specification fields — metadata-only, no drift from name/qty/notes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.models.part import Part
from backend.services.parsers.helpers.hardware_signals import (
    FASTENER_TYPE_RE,
    METRIC_FASTENER_RE,
    has_hardware_signal,
)
from backend.services.parsers.helpers.quantity_checks import check_part as check_quantity_part
from backend.services.parsers.helpers.spec_metadata import (
    ASSEMBLY_PROSE_RE,
    MAKERWORLD_NOISE_RE,
    classify_hardware_kind,
    extract_spec_metadata,
    spec_field_hint,
    _has_bearing_shield_metadata,
    _has_fastener_style,
    _metric_identity_tokens,
    _overlap_ratio,
)

QTY_PREFIX_IN_SPEC = re.compile(r"^\s*\d+(?:\.\d+)?\s*[x×]\s+", re.I)


@dataclass(frozen=True)
class SpecificationIssue:
    part_index: int
    original_name: str
    specification: str
    code: str
    message: str
    severity: str  # error | warning
    hint: str = ""


def _finish_only_spec(spec: str) -> bool:
    return bool(
        re.search(
            r"\b(stainless|18-8|316|black\s+oxide|zinc|alloy\s+steel|fully\s+threaded)\b",
            spec,
            re.I,
        )
    )


def _combined_text(part: Part) -> str:
    return f"{part.original_name} {part.specification}".strip()


def check_part_specification(
    part: Part,
    *,
    index: int = 0,
) -> list[SpecificationIssue]:
    issues: list[SpecificationIssue] = []
    kind = classify_hardware_kind(part.original_name, part.specification)
    hint = spec_field_hint(part)
    spec = (part.specification or "").strip()
    name = (part.original_name or "").strip()
    combined = _combined_text(part)

    for qty_issue in check_quantity_part(part, index=index):
        if qty_issue.code in {"qty_in_specification", "hardware_in_specification"}:
            issues.append(
                SpecificationIssue(
                    part_index=index,
                    original_name=part.original_name,
                    specification=part.specification,
                    code=qty_issue.code,
                    message=qty_issue.message,
                    severity="error",
                    hint=hint,
                )
            )

    if not spec:
        if kind in {"fastener", "bearing"} and has_hardware_signal(name):
            if kind == "fastener" and not _has_fastener_style(combined):
                issues.append(
                    SpecificationIssue(
                        part_index=index,
                        original_name=part.original_name,
                        specification=part.specification,
                        code="missing_fastener_style",
                        message="Add head or drive style in name or specification (socket, button, hex, Phillips, etc.)",
                        severity="warning",
                        hint=hint,
                    )
                )
            elif kind == "bearing" and not _has_bearing_shield_metadata(combined):
                issues.append(
                    SpecificationIssue(
                        part_index=index,
                        original_name=part.original_name,
                        specification=part.specification,
                        code="missing_bearing_shield",
                        message="Add shielding or seal type (ZZ, 2RS, open, double-shielded)",
                        severity="warning",
                        hint=hint,
                    )
                )
        return issues

    if QTY_PREFIX_IN_SPEC.match(spec):
        issues.append(
            SpecificationIssue(
                part_index=index,
                original_name=part.original_name,
                specification=part.specification,
                code="quantity_in_specification",
                message="Quantity belongs in Qty, not specification",
                severity="error",
                hint=hint,
            )
        )

    if _overlap_ratio(spec, name) >= 0.85:
        issues.append(
            SpecificationIssue(
                part_index=index,
                original_name=part.original_name,
                specification=part.specification,
                code="duplicate_of_name",
                message="Specification repeats the part name — keep only distinguishing metadata here",
                severity="error",
                hint=hint,
            )
        )

    spec_metrics = _metric_identity_tokens(spec)
    name_metrics = _metric_identity_tokens(name)
    if spec_metrics and name_metrics and spec_metrics <= name_metrics:
        issues.append(
            SpecificationIssue(
                part_index=index,
                original_name=part.original_name,
                specification=part.specification,
                code="size_in_specification",
                message="Thread size/length already in part name — specification should add style, finish, or grade",
                severity="error",
                hint=hint,
            )
        )

    if METRIC_FASTENER_RE.search(spec) and FASTENER_TYPE_RE.search(spec):
        if not extract_spec_metadata(spec) and not _finish_only_spec(spec):
            issues.append(
                SpecificationIssue(
                    part_index=index,
                    original_name=part.original_name,
                    specification=part.specification,
                    code="identity_in_specification",
                    message="Full fastener identity belongs in part name; use specification for head, drive, finish, or threading",
                    severity="error",
                    hint=hint,
                )
            )

    if ASSEMBLY_PROSE_RE.search(spec) and len(spec) > 24:
        issues.append(
            SpecificationIssue(
                part_index=index,
                original_name=part.original_name,
                specification=part.specification,
                code="prose_in_specification",
                message="Assembly or location text belongs in Notes, not specification",
                severity="error",
                hint=hint,
            )
        )

    if MAKERWORLD_NOISE_RE.search(spec):
        issues.append(
            SpecificationIssue(
                part_index=index,
                original_name=part.original_name,
                specification=part.specification,
                code="source_noise_in_specification",
                message="Source labels (MakerWorld BOM, filament, etc.) belong in Notes",
                severity="warning",
                hint=hint,
            )
        )

    if part.notes and spec.lower() in part.notes.lower():
        issues.append(
            SpecificationIssue(
                part_index=index,
                original_name=part.original_name,
                specification=part.specification,
                code="duplicate_in_notes",
                message="Specification duplicates Notes — keep metadata in one place",
                severity="warning",
                hint=hint,
            )
        )

    if kind == "fastener" and not _has_fastener_style(combined):
        issues.append(
            SpecificationIssue(
                part_index=index,
                original_name=part.original_name,
                specification=part.specification,
                code="missing_fastener_style",
                message="No head or drive style found — add socket, button, hex, Phillips, etc.",
                severity="warning",
                hint=hint,
            )
        )

    if kind == "bearing" and not _has_bearing_shield_metadata(combined):
        issues.append(
            SpecificationIssue(
                part_index=index,
                original_name=part.original_name,
                specification=part.specification,
                code="missing_bearing_shield",
                message="No bearing shield/seal type — add ZZ, 2RS, open, or double-shielded",
                severity="warning",
                hint=hint,
            )
        )

    return issues


def check_parts_specifications(parts: list[Part]) -> list[SpecificationIssue]:
    issues: list[SpecificationIssue] = []
    for index, part in enumerate(parts):
        issues.extend(check_part_specification(part, index=index))
    return issues


def format_specification_issues(issues: list[SpecificationIssue]) -> str:
    if not issues:
        return "No specification issues found."
    lines = [f"Found {len(issues)} specification issue(s):", ""]
    for issue in issues:
        sev = issue.severity.upper()
        lines.append(f"[{issue.code}] ({sev}) part {issue.part_index + 1}: {issue.message}")
        lines.append(f"  name: {issue.original_name!r}")
        if issue.specification:
            lines.append(f"  spec: {issue.specification!r}")
        if issue.hint:
            lines.append(f"  hint: {issue.hint}")
        lines.append("")
    return "\n".join(lines).rstrip()
