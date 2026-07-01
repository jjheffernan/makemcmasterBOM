"""McMaster browse filter path segments — inspired by site facet URLs and Parse search filters."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.services.hardware_spec import MetricFastenerSpec

_MATERIAL_STAINLESS = re.compile(r"\b(18-8|316|stainless|a2|a4)\b", re.I)
_MATERIAL_BLACK_OXIDE = re.compile(r"\b(black\s*oxide|black[\s-]*oxide)\b", re.I)
_MATERIAL_ZINC = re.compile(r"\b(zinc(?:\s+plated)?|zinc[\s-]*plate[d]?)\b", re.I)
_MATERIAL_ALLOY = re.compile(r"\b(alloy\s+steel)\b", re.I)


def slugify_filter_value(value: str) -> str:
    """Turn a facet value into a McMaster path token (lowercase, spaces → hyphens)."""
    text = value.strip().lower()
    text = text.replace("×", "x").replace("–", "-")
    text = re.sub(r"[^\w./-]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def metric_thread_filter_slug(diameter_mm: float) -> str:
    """M3 → m3, M2.5 → m2-5 (matches live McMaster filter slugs)."""
    if diameter_mm == int(diameter_mm):
        return f"m{int(diameter_mm)}"
    return f"m{str(diameter_mm).replace('.', '-')}"


def metric_length_filter_slug(length_mm: int | float) -> str:
    if length_mm == int(length_mm):
        return f"{int(length_mm)}-mm"
    return f"{str(length_mm).replace('.', '-')}-mm"


@dataclass(frozen=True)
class BrowseFilterSet:
    """Ordered McMaster path filter segments."""

    segments: tuple[str, ...]

    def as_path(self) -> str:
        return "".join(self.segments)

    @property
    def is_empty(self) -> bool:
        return not self.segments


def build_fastener_filters(spec: MetricFastenerSpec) -> BrowseFilterSet:
    """Build metric fastener filters: system-of-measurement, thread-size, length."""
    segments: list[str] = ["system-of-measurement~metric/"]
    if spec.diameter_mm:
        thread = metric_thread_filter_slug(spec.diameter_mm)
        segments.append(f"thread-size~{thread}/")
    if spec.length_mm is not None:
        length = metric_length_filter_slug(spec.length_mm)
        segments.append(f"length~{length}/")
    return BrowseFilterSet(tuple(segments))


def infer_finish_from_bom(query: str, specification: str = "") -> str | None:
    """
    Return a single finish_id when the BOM names a finish.

    Returns None when multiple finishes should be offered (dropdown).
    """
    combined = f"{query} {specification}".lower()
    if _MATERIAL_STAINLESS.search(combined):
        return "stainless"
    if _MATERIAL_ZINC.search(combined):
        return "zinc_plated"
    if _MATERIAL_BLACK_OXIDE.search(combined):
        return "black_oxide"
    if _MATERIAL_ALLOY.search(combined):
        return "black_oxide"
    return None


def infer_material_variant_id(query: str, specification: str = "") -> str:
    """
    Pick the default browse-root finish for socket-head screws.

    Returns one of: black_oxide | zinc_plated | stainless
    """
    finish = infer_finish_from_bom(query, specification)
    if finish:
        return finish
    return "black_oxide"


def bearing_trade_filter_slug(trade: str) -> str | None:
    digits = re.sub(r"[^0-9]", "", trade)[:3]
    return f"{digits}-trade" if digits else None
