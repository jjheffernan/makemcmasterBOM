"""Hardware metadata rules for the BOM specification field."""

from __future__ import annotations

import re
from typing import Literal

from backend.services.parsers.helpers.hardware_signals import (
    BEARING_DESIGNATION_RE,
    FASTENER_PREFIX_RE,
    FASTENER_TYPE_RE,
    METRIC_FASTENER_RE,
    METRIC_THREAD_RE,
    has_bearing_designation,
    has_hardware_signal,
)

HardwareKind = Literal[
    "fastener",
    "bearing",
    "nut",
    "washer",
    "magnet",
    "insert",
    "tubing",
    "other_hardware",
    "non_hardware",
]

# Metadata that belongs in specification (not duplicated from name)
FASTENER_HEAD_STYLE_RE = re.compile(
    r"\b("
    r"socket\s+head|button\s+head|flat\s+head|pan\s+head|cheese\s+head|"
    r"countersunk(?:\s+head)?|fillister|truss\s+head|wafer\s+head|"
    r"shoulder\s+head|thumb\s+screw|knurled\s+head"
    r")\b",
    re.I,
)
FASTENER_DRIVE_RE = re.compile(
    r"\b("
    r"hex\s+socket|socket\s+head|allen|phillips|slotted|torx|"
    r"hex(?:agonal)?\s+head|square\s+drive|security\s+torx"
    r")\b",
    re.I,
)
BEARING_SHIELD_RE = re.compile(
    r"\b("
    r"double[-\s]?shielded|shielded|open|sealed|"
    r"2\s*rs|2rs|zz|2zz|-zz|-2rs"
    r")\b",
    re.I,
)
NUT_STYLE_RE = re.compile(
    r"\b(lock\s+nut|nyloc|nylock|jam\s+nut|flange\s+nut|coupling\s+nut)\b",
    re.I,
)
FINISH_MATERIAL_RE = re.compile(
    r"\b("
    r"black\s+oxide|zinc(?:\s+plated)?|stainless|18-8|316|a2|a4|"
    r"alloy\s+steel|brass|nylon|passivated|blue\s+dyed|"
    r"fully\s+threaded|partially\s+threaded|coarse|fine"
    r")\b",
    re.I,
)
ASSEMBLY_PROSE_RE = re.compile(
    r"\b("
    r"against|attaching|module|modules|side|sides|holder|holders|"
    r"left\s+front|right\s+rear|gear|motor|pcb|assembly"
    r")\b",
    re.I,
)
MAKERWORLD_NOISE_RE = re.compile(
    r"\b(makerworld\s+bom|maker'?s\s+supply|filament|bambu\s+lab)\b",
    re.I,
)

SPEC_HINTS: dict[HardwareKind, str] = {
    "fastener": "Head style, drive, finish, threading (e.g. socket head, hex, 18-8, fully threaded)",
    "bearing": "Shielding / seal (e.g. double-shielded, 2RS, open)",
    "nut": "Style or locking (e.g. nyloc, flange, jam)",
    "washer": "Type or finish (e.g. lock washer, stainless)",
    "magnet": "Grade, coating, or pull force if known",
    "insert": "Install method or material (e.g. heat-set, brass)",
    "tubing": "ID/OD, wall, material (e.g. PTFE, 4 mm ID)",
    "other_hardware": "Distinguishing details not already in the part name",
    "non_hardware": "Optional extra detail — leave blank if N/A",
}


def classify_hardware_kind(part_name: str, specification: str = "") -> HardwareKind:
    text = f"{part_name} {specification}".lower()
    if not text.strip():
        return "non_hardware"
    if not has_hardware_signal(text):
        return "non_hardware"
    if has_bearing_designation(text) or re.search(r"\bbearing\b", text):
        return "bearing"
    if re.search(r"\b(?:hex\s+)?nut\b", text):
        return "nut"
    if re.search(r"\bwasher\b", text):
        return "washer"
    if re.search(r"\bmagnet\b", text):
        return "magnet"
    if re.search(r"\b(?:heat[-\s]?set\s+)?insert\b", text):
        return "insert"
    if re.search(r"\b(?:ptfe\s+)?tub(?:e|ing)\b", text):
        return "tubing"
    if FASTENER_TYPE_RE.search(text):
        return "fastener"
    return "other_hardware"


def spec_field_hint(part: object) -> str:
    name = getattr(part, "original_name", "") or ""
    spec = getattr(part, "specification", "") or ""
    kind = classify_hardware_kind(name, spec)
    return SPEC_HINTS[kind]


def _normalize_metric_token(text: str) -> str:
    match = METRIC_FASTENER_RE.search(text)
    if match:
        return f"m{float(match.group(1)):g}x{float(match.group(2)):g}"
    match = METRIC_THREAD_RE.search(text)
    if match:
        return f"m{float(match.group(1)):g}"
    return text.lower().strip()


def _metric_identity_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in METRIC_FASTENER_RE.finditer(text):
        tokens.add(f"m{float(match.group(1)):g}x{float(match.group(2)):g}")
    for match in METRIC_THREAD_RE.finditer(text):
        tokens.add(f"m{float(match.group(1)):g}")
    return tokens


def _has_fastener_style(text: str) -> bool:
    return bool(
        FASTENER_HEAD_STYLE_RE.search(text)
        or FASTENER_DRIVE_RE.search(text)
        or FASTENER_PREFIX_RE.search(text)
    )


def _has_bearing_shield_metadata(text: str) -> bool:
    return bool(BEARING_SHIELD_RE.search(text) or BEARING_DESIGNATION_RE.search(text))


def _overlap_ratio(shorter: str, longer: str) -> float:
    a = shorter.lower().strip()
    b = longer.lower().strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b:
        return len(a) / len(b)
    return 0.0


def extract_spec_metadata(text: str) -> list[str]:
    """Return metadata phrases found in specification text."""
    if not text.strip():
        return []
    found: list[str] = []
    for pattern in (
        FASTENER_HEAD_STYLE_RE,
        FASTENER_DRIVE_RE,
        BEARING_SHIELD_RE,
        NUT_STYLE_RE,
        FINISH_MATERIAL_RE,
    ):
        for match in pattern.finditer(text):
            phrase = re.sub(r"\s+", " ", match.group(0).strip())
            if phrase.lower() not in {f.lower() for f in found}:
                found.append(phrase)
    return found


def normalize_specification_text(name: str, specification: str, notes: str = "") -> tuple[str, str, str]:
    """
    Trim specification to metadata-only content and prevent field drift.

    Returns (name, specification, notes) — may move prose from spec to notes.
    """
    name = (name or "").strip()
    spec = (specification or "").strip()
    notes = (notes or "").strip()

    if MAKERWORLD_NOISE_RE.search(spec):
        spec = MAKERWORLD_NOISE_RE.sub("", spec).strip(" ,;")

    if ASSEMBLY_PROSE_RE.search(spec) and len(spec) > 24:
        if spec not in notes:
            notes = f"{spec} ({notes})" if notes else spec
        spec = ""

    if spec and _overlap_ratio(spec, name) >= 0.85:
        spec = ""

    if spec:
        name_metrics = _metric_identity_tokens(name)
        spec_metrics = _metric_identity_tokens(spec)
        if spec_metrics and spec_metrics <= name_metrics:
            spec = METRIC_FASTENER_RE.sub("", spec)
            spec = METRIC_THREAD_RE.sub("", spec)
            spec = re.sub(r"\s+", " ", spec).strip(" ,;")

        if spec:
            for pattern in (FASTENER_TYPE_RE, FASTENER_HEAD_STYLE_RE):
                for match in pattern.finditer(name):
                    token = match.group(0)
                    spec = re.sub(rf"\b{re.escape(token)}\b", "", spec, flags=re.I)
            spec = re.sub(r"\s+", " ", spec).strip(" ,;")

    if spec and name.lower() == spec.lower():
        spec = ""

    return name, spec[:400], notes[:400]


def normalize_part_specification(part: object):
    """Return a copy of the part with normalized specification fields."""
    from backend.models.part import Part

    if not isinstance(part, Part):
        part = Part.model_validate(part)
    name, spec, notes = normalize_specification_text(
        part.original_name,
        part.specification,
        part.notes,
    )
    return part.model_copy(
        update={
            "original_name": name,
            "specification": spec,
            "notes": notes,
        }
    )
