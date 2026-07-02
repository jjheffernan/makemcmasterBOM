"""McMaster browse filter path segments — inspired by site facet URLs and Parse search filters."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.services.hardware_spec import ImperialFastenerSpec, MetricFastenerSpec

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


def build_washer_filters(spec: MetricFastenerSpec) -> BrowseFilterSet:
    """
    McMaster washer tables filter on screw size (for screw size), not thread-size.

    Length is not used for washers.
    """
    segments: list[str] = ["system-of-measurement~metric/"]
    if spec.diameter_mm:
        size = metric_thread_filter_slug(spec.diameter_mm)
        segments.append(f"screw-size~{size}/")
    return BrowseFilterSet(tuple(segments))


def imperial_length_filter_slug(length_in: float) -> str:
    if abs(length_in - 0.5) < 0.01:
        return "1-2-in"
    if abs(length_in - 0.25) < 0.01:
        return "1-4-in"
    if abs(length_in - 0.75) < 0.01:
        return "3-4-in"
    if length_in == int(length_in):
        return f"{int(length_in)}-in"
    return f"{str(length_in).replace('.', '-')}-in"


def build_imperial_fastener_filters(spec: ImperialFastenerSpec) -> BrowseFilterSet:
    """Inch-system thread + optional length facets."""
    segments: list[str] = ["system-of-measurement~inch/"]
    segments.append(f"thread-size~{spec.thread_callout}/")
    if spec.length_in is not None:
        segments.append(f"length~{imperial_length_filter_slug(spec.length_in)}/")
    return BrowseFilterSet(tuple(segments))


def build_imperial_washer_filters(spec: ImperialFastenerSpec) -> BrowseFilterSet:
    segments: list[str] = ["system-of-measurement~inch/"]
    segments.append(f"screw-size~{spec.thread_callout}/")
    return BrowseFilterSet(tuple(segments))


def infer_finish_from_bom(query: str, specification: str = "") -> str | None:
    """
    Return a finish_id when the BOM names a material finish.

    Returns None when ambiguous — callers pick a single default browse table.
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


def infer_material_variant_id(
    query: str,
    specification: str = "",
    *,
    category_id: str = "",
) -> str:
    """
    Pick the default browse-root finish for metric fasteners.

    Returns one of: black_oxide | zinc_plated | stainless
    """
    finish = infer_finish_from_bom(query, specification)
    if finish:
        return finish
    if category_id == "lock_washer":
        from backend.services.vendors.mcmaster.washer_subtype import lock_washer_finish_id

        return lock_washer_finish_id(query, specification)
    if category_id in {
        "hex_nut",
        "lock_nut",
        "flange_nut",
        "jam_nut",
        "coupling_nut",
        "flat_washer",
        "fender_washer",
        "washer",
    }:
        return "metric"
    return "black_oxide"


def bearing_trade_filter_slug(trade: str) -> str | None:
    digits = re.sub(r"[^0-9]", "", trade)[:3]
    return f"{digits}-trade" if digits else None
