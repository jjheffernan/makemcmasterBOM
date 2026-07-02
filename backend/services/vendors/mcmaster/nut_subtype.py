"""Nut family detection — hex vs lock/nyloc vs flange/jam/coupling McMaster tables."""

from __future__ import annotations

import re

NUT_CATEGORY_IDS = frozenset(
    {"hex_nut", "lock_nut", "flange_nut", "jam_nut", "coupling_nut"},
)

_LOCK_NUT_RE = re.compile(
    r"\b("
    r"lock\s*nut|locknut|nyloc|nylock|nylon[\s-]*insert|"
    r"prevailing[\s-]*torque|flex[\s-]*top|din\s*985|din\s*986"
    r")\b",
    re.I,
)
_FLANGE_NUT_RE = re.compile(r"\b(flange\s+nut)\b", re.I)
_JAM_NUT_RE = re.compile(r"\b(jam\s+nut)\b", re.I)
_COUPLING_NUT_RE = re.compile(r"\b(coupling\s+nut)\b", re.I)
_HEX_NUT_RE = re.compile(r"\b(hex\s+nut|din\s*934)\b", re.I)
_NUT_TOKEN_RE = re.compile(r"\b(?:hex\s+)?nut\b|\b(?:nylock|nyloc)\b", re.I)


def combined_nut_text(query: str, specification: str = "") -> str:
    return f"{query} {specification}".strip().lower()


def is_nut_line(query: str, specification: str = "") -> bool:
    return bool(_NUT_TOKEN_RE.search(combined_nut_text(query, specification)))


def infer_nut_category_id(query: str, specification: str = "") -> str:
    """
    Pick McMaster browse family for nut BOM lines.

    Defaults ambiguous ``M4 nut`` to metric hex nuts — the common BOM case.
    """
    text = combined_nut_text(query, specification)
    if _COUPLING_NUT_RE.search(text):
        return "coupling_nut"
    if _JAM_NUT_RE.search(text):
        return "jam_nut"
    if _FLANGE_NUT_RE.search(text):
        return "flange_nut"
    if _LOCK_NUT_RE.search(text):
        return "lock_nut"
    if _HEX_NUT_RE.search(text) or re.search(r"\bnut\b", text):
        return "hex_nut"
    return "hex_nut"


def is_nut_category(category_id: str) -> bool:
    return category_id in NUT_CATEGORY_IDS or category_id == "nut"
