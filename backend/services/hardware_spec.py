"""Extract and compare metric fastener size / length from BOM text and catalog hits."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from backend.models.part import Part
from backend.services.hardware_terms import (
    BEARING_DESIGNATION_RE,
    METRIC_FASTENER_RE,
    METRIC_THREAD_RE,
)
from backend.services.mcmaster_catalog import CatalogHit, M3_SOCKET_HEAD_BY_LENGTH_MM

FastenerKind = Literal["screw", "nut", "washer", "bearing", "insert", "unknown"]

# M4 screws 40mm / M4 screw 40 mm (diameter and length not joined with x)
METRIC_SIZE_SEPARATE_LENGTH_MM = re.compile(
    r"\bM\s*(\d+(?:\.\d+)?)\b"
    r"(?:\s+(?:socket\s+head\s+)?(?:cap\s+)?)?"
    r"(?:screw|screws|bolt|bolts|stud|studs)"
    r"\s+(\d+(?:\.\d+)?)\s*mm\b",
    re.I,
)

# Trailing length after fastener word: socket head screw 16 mm
FASTENER_TRAILING_LENGTH_MM = re.compile(
    r"\b(?:screw|screws|bolt|bolts|stud|studs)\s+(\d+(?:\.\d+)?)\s*mm\b",
    re.I,
)


@dataclass(frozen=True)
class MetricFastenerSpec:
    diameter_mm: float
    length_mm: int | None = None
    kind: FastenerKind = "screw"

    def label(self) -> str:
        if self.length_mm is not None:
            return f"M{self.diameter_mm:g}×{self.length_mm} mm"
        return f"M{self.diameter_mm:g}"


# Reverse map McMaster M3 socket-head series → length
_M3_PART_TO_LENGTH: dict[str, int] = {
    part: length for length, part in M3_SOCKET_HEAD_BY_LENGTH_MM.items()
}

_CATALOG_TITLE_METRIC = re.compile(
    r"\bM\s*(\d+(?:\.\d+)?)\s*[×x]\s*(\d+(?:\.\d+)?)\s*mm\b",
    re.I,
)
_CATALOG_TITLE_SIZE_ONLY = re.compile(
    r"\bM\s*(\d+(?:\.\d+)?)\b",
    re.I,
)


def _kind_from_text(text: str) -> FastenerKind:
    lower = text.lower()
    if BEARING_DESIGNATION_RE.search(lower):
        return "bearing"
    if re.search(r"\b(?:hex\s+)?nut\b", lower):
        return "nut"
    if re.search(r"\bwasher\b", lower):
        return "washer"
    if re.search(r"\binsert\b", lower):
        return "insert"
    if re.search(r"\b(?:screw|bolt|stud)\b", lower):
        return "screw"
    return "unknown"


def _spec_from_metric_match(
    diameter: float,
    length: float | None,
    text: str,
) -> MetricFastenerSpec:
    length_mm = int(length) if length is not None else None
    return MetricFastenerSpec(
        diameter_mm=diameter,
        length_mm=length_mm,
        kind=_kind_from_text(text),
    )


def extract_fastener_specs(text: str) -> list[MetricFastenerSpec]:
    """Return all metric fastener specs found in text (may be multiple)."""
    if not text or not text.strip():
        return []

    found: list[MetricFastenerSpec] = []
    seen: set[tuple[float, int | None, str]] = set()

    def add(spec: MetricFastenerSpec) -> None:
        key = (spec.diameter_mm, spec.length_mm, spec.kind)
        if key not in seen:
            seen.add(key)
            found.append(spec)

    for match in METRIC_FASTENER_RE.finditer(text):
        add(
            _spec_from_metric_match(
                float(match.group(1)),
                float(match.group(2)),
                match.group(0),
            )
        )

    for match in METRIC_SIZE_SEPARATE_LENGTH_MM.finditer(text):
        add(
            _spec_from_metric_match(
                float(match.group(1)),
                float(match.group(2)),
                match.group(0),
            )
        )

    # Diameter from M-label + trailing screw length (e.g. after normalization)
    diameter_match = METRIC_THREAD_RE.search(text)
    length_match = FASTENER_TRAILING_LENGTH_MM.search(text)
    if diameter_match and length_match:
        if not any(
            s.diameter_mm == float(diameter_match.group(1))
            and s.length_mm == int(float(length_match.group(1)))
            for s in found
        ):
            add(
                _spec_from_metric_match(
                    float(diameter_match.group(1)),
                    float(length_match.group(1)),
                    text,
                )
            )

    return found


def primary_fastener_spec(part: Part) -> MetricFastenerSpec | None:
    """
    Best single fastener spec for a BOM row.

    Prefers ``original_name``, then ``specification``, then ``notes`` so a clean
    part name is not overridden by stale qty/spec fragments in other fields.
    """
    for field in (part.original_name, part.specification, part.notes):
        specs = extract_fastener_specs(field)
        if specs:
            return specs[0]
    return None


def all_fastener_specs(part: Part) -> list[MetricFastenerSpec]:
    """Specs from name, spec, and notes — used to detect conflicts."""
    combined: list[MetricFastenerSpec] = []
    seen: set[tuple[float, int | None]] = set()
    for field in (part.original_name, part.specification, part.notes):
        for spec in extract_fastener_specs(field):
            key = (spec.diameter_mm, spec.length_mm)
            if key not in seen:
                seen.add(key)
                combined.append(spec)
    return combined


def spec_from_catalog_hit(hit: CatalogHit) -> MetricFastenerSpec | None:
    title = hit.title or ""
    metric = _CATALOG_TITLE_METRIC.search(title)
    if metric:
        return MetricFastenerSpec(
            diameter_mm=float(metric.group(1)),
            length_mm=int(float(metric.group(2))),
            kind=_kind_from_text(title) if _kind_from_text(title) != "unknown" else "screw",
        )

    if hit.part_number in _M3_PART_TO_LENGTH:
        return MetricFastenerSpec(
            diameter_mm=3.0,
            length_mm=_M3_PART_TO_LENGTH[hit.part_number],
            kind="screw",
        )

    size_only = _CATALOG_TITLE_SIZE_ONLY.search(title)
    if size_only and hit.category in {"nut", "washer"}:
        return MetricFastenerSpec(
            diameter_mm=float(size_only.group(1)),
            length_mm=None,
            kind=hit.category,  # type: ignore[arg-type]
        )

    return None


def build_explicit_fastener_query(spec: MetricFastenerSpec, *, hint_text: str = "") -> str:
    hint = hint_text.lower()
    d, length = spec.diameter_mm, spec.length_mm
    if length is not None:
        if "button head" in hint or "bhcs" in hint:
            return f"M{d:g}x{length} mm button head cap screw"
        if "flat head" in hint or "fhcs" in hint:
            return f"M{d:g}x{length} mm flat head cap screw"
        if "hex bolt" in hint or re.search(r"\bbolt\b", hint):
            return f"M{d:g}x{length} mm hex bolt"
        if "socket" in hint or "shcs" in hint:
            return f"M{d:g}x{length} mm socket head cap screw"
        return f"M{d:g}x{length} mm screw"
    if spec.kind == "nut" or "nut" in hint:
        return f"M{d:g} hex nut"
    if spec.kind == "washer" or "washer" in hint:
        return f"M{d:g} washer"
    return f"M{d:g} screw"


def sizes_match(expected: MetricFastenerSpec, matched: MetricFastenerSpec) -> bool:
    return abs(expected.diameter_mm - matched.diameter_mm) < 0.01


def lengths_match(expected: MetricFastenerSpec, matched: MetricFastenerSpec) -> bool:
    if expected.length_mm is None or matched.length_mm is None:
        return True
    return expected.length_mm == matched.length_mm
