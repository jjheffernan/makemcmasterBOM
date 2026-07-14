"""Shared hardware keyword and pattern library for BOM parsing and matching."""

from __future__ import annotations

import re
from typing import Callable

# Metric thread designations commonly found in maker BOMs (M2–M12)
METRIC_SIZES: tuple[str, ...] = (
    "M2",
    "M2.5",
    "M3",
    "M4",
    "M5",
    "M6",
    "M8",
    "M10",
    "M12",
)

_METRIC_SIZE_ALT = "|".join(re.escape(s) for s in METRIC_SIZES)

# Standalone metric label: M3, M2.5
METRIC_SIZE_WORD_RE = re.compile(rf"\b(?:{_METRIC_SIZE_ALT})\b", re.I)

# Thread + length: M3x8, M3*8, M3×8, M2.5x6mm, M3-16, M3-16mm
METRIC_FASTENER_RE = re.compile(
    r"\bM\s*(\d+(?:\.\d+)?)\s*[*×xX\-]\s*(\d+(?:\.\d+)?)(?:\s*mm)?\b",
    re.I,
)

# Any M-diameter token (M3, M12, M2.5)
METRIC_THREAD_RE = re.compile(r"\bM\s*(\d+(?:\.\d+)?)\b", re.I)

# Imperial: #6-32, 1/4-20
IMPERIAL_THREAD_RE = re.compile(
    r"#\s*\d+\s*-\s*\d+|\b\d+\s*/\s*\d+\s*-\s*\d+",
)

# Axial dimensions: 5x30, 5×30mm, 8x22x7, 12/10mm
DIMENSION_AXIAL_RE = re.compile(
    r"\b\d+(?:\.\d+)?(?:\s*[x×/]\s*\d+(?:\.\d+)?){1,2}\s*(?:mm|cm|in(?:ch)?|\")?\b",
    re.I,
)

# Length with unit: 30mm, 30 mm, 1.5 mm
LENGTH_MM_RE = re.compile(r"\b\d+(?:\.\d+)?\s*mm\b", re.I)
LENGTH_CM_RE = re.compile(r"\b\d+(?:\.\d+)?\s*cm\b", re.I)
LENGTH_IN_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:in(?:ch)?|\")\b", re.I)

# Bearing designations: 608-ZZ, 693ZZ, 608-RS
BEARING_DESIGNATION_RE = re.compile(
    r"\b\d{3}\s*[-_]?\s*(?:ZZ|RS|2RS)\b",
    re.I,
)

# Fastener type words (suffix / standalone)
FASTENER_TYPES: frozenset[str] = frozenset(
    {
        "screw",
        "bolt",
        "nut",
        "washer",
        "stud",
        "standoff",
        "rivet",
        "pin",
        "insert",
        "fastener",
        "rod",
        "set screw",
        "grub screw",
        "cap screw",
        "machine screw",
        "wood screw",
        "self-tapping screw",
        "tapping screw",
        "hex bolt",
        "carriage bolt",
        "lag bolt",
        "eye bolt",
        "hex nut",
        "lock nut",
        "nyloc nut",
        "nylock nut",
        "jam nut",
        "flange nut",
        "flat washer",
        "lock washer",
        "spring washer",
        "fender washer",
    }
)

# Modifiers that precede fastener types
FASTENER_PREFIXES: frozenset[str] = frozenset(
    {
        "hex",
        "socket",
        "button",
        "flat",
        "cap",
        "allen",
        "cheese",
        "wafer",
        "pan",
        "machine",
        "countersunk",
        "countersink",
        "flange",
        "shoulder",
        "thumb",
        "knurled",
        "hexagonal",
    }
)

FASTENER_TYPE_RE = re.compile(
    r"\b("
    r"screws?|bolts?|nuts?|washers?|studs?|fasteners?|standoffs?|rivets?|pins?|inserts?|rods?"
    r")\b",
    re.I,
)

FASTENER_PREFIX_RE = re.compile(
    r"\b("
    r"hex|socket|button|flat|cap|allen|cheese|wafer|pan|machine|"
    r"countersunk?|flange|shoulder|thumb|knurled|hexagonal"
    r")\b",
    re.I,
)

# Broader hardware vocabulary (mechanical + common BOM extras)
HARDWARE_TERMS: frozenset[str] = frozenset(
    {
        *FASTENER_TYPES,
        *FASTENER_PREFIXES,
        *{s.lower() for s in METRIC_SIZES},
        "bearing",
        "ball bearing",
        "roller bearing",
        "bushing",
        "spring",
        "magnet",
        "o-ring",
        "oring",
        "seal",
        "clamp",
        "bracket",
        "hinge",
        "latch",
        "coupling",
        "gear",
        "pulley",
        "belt",
        "chain",
        "sprocket",
        "shaft",
        "aluminum",
        "aluminium",
        "steel",
        "stainless",
        "brass",
        "nylon",
        "delrin",
        "acetal",
        "peek",
        "ptfe",
        "tube",
        "tubing",
        "hose",
        "cable",
        "wire",
        "connector",
        "socket head",
        "button head",
        "heat insert",
        "threaded insert",
        "heat-set insert",
        "carbon fiber",
        "acrylic",
        "glass",
        "panel",
        "button",
        "valve",
        "nozzle",
        # MakerWorld BOM extras
        "marker",
        "foil pen",
        "card",
        "tape",
        "glue",
        "epoxy",
        "bulb",
        "acrly",
        "graugear",
        "mainboard",
    }
)


def _compile_term_pattern(terms: frozenset[str]) -> re.Pattern[str]:
    ordered = sorted(terms, key=len, reverse=True)
    body = "|".join(re.escape(term) for term in ordered)
    return re.compile(rf"\b(?:{body})\b", re.I)


HARDWARE_KEYWORD_RE = _compile_term_pattern(HARDWARE_TERMS)

# Back-compat alias used by matcher
HARDWARE_KEYWORDS = HARDWARE_KEYWORD_RE


def has_fastener_type(text: str) -> bool:
    return bool(FASTENER_TYPE_RE.search(text))


def has_fastener_prefix(text: str) -> bool:
    return bool(FASTENER_PREFIX_RE.search(text))


def has_fastener_suffix(text: str) -> bool:
    """True when text ends with or contains a known fastener type word."""
    if FASTENER_TYPE_RE.search(text):
        return True
    lower = text.lower()
    return any(
        re.search(rf"\b{re.escape(term)}\b", lower)
        for term in FASTENER_TYPES
        if " " not in term
    )


def has_metric_size(text: str) -> bool:
    return bool(METRIC_SIZE_WORD_RE.search(text) or METRIC_THREAD_RE.search(text))


def has_metric_fastener(text: str) -> bool:
    return bool(METRIC_FASTENER_RE.search(text))


def has_imperial_thread(text: str) -> bool:
    return bool(IMPERIAL_THREAD_RE.search(text))


def has_length_mm(text: str) -> bool:
    return bool(LENGTH_MM_RE.search(text))


def has_length_cm(text: str) -> bool:
    return bool(LENGTH_CM_RE.search(text))


def has_length_in(text: str) -> bool:
    return bool(LENGTH_IN_RE.search(text))


def has_axial_dimension(text: str) -> bool:
    return bool(DIMENSION_AXIAL_RE.search(text))


def has_bearing_designation(text: str) -> bool:
    return bool(BEARING_DESIGNATION_RE.search(text))


def has_hardware_keyword(text: str) -> bool:
    return bool(HARDWARE_KEYWORD_RE.search(text))


def extract_metric_sizes(text: str) -> list[str]:
    """Return normalized metric labels found in text (e.g. M3, M2.5)."""
    found: list[str] = []
    seen: set[str] = set()
    for match in METRIC_THREAD_RE.finditer(text):
        label = f"M{match.group(1)}"
        key = label.lower()
        if key not in seen:
            seen.add(key)
            found.append(label)
    return found


_HARDWARE_SIGNAL_CHECKS: tuple[Callable[[str], bool], ...] = (
    has_hardware_keyword,
    has_metric_fastener,
    has_metric_size,
    has_imperial_thread,
    has_axial_dimension,
    has_length_mm,
    has_bearing_designation,
)


def has_hardware_signal(text: str) -> bool:
    """True when text looks like catalog hardware (keywords, metric, or dimensions)."""
    if not text or not text.strip():
        return False
    return any(check(text) for check in _HARDWARE_SIGNAL_CHECKS)
