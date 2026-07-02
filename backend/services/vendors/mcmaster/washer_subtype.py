"""Washer family detection — flat vs lock vs fender McMaster browse tables."""

from __future__ import annotations

import re

WASHER_CATEGORY_IDS = frozenset({"flat_washer", "lock_washer", "fender_washer"})

_LOCK_WASHER_RE = re.compile(
    r"\b("
    r"lock\s+washer|spring\s+washer|split\s+lock|split\s+washer|"
    r"tooth\s+lock|star\s+washer|serrated\s+washer|din\s*127|din\s*7980"
    r")\b",
    re.I,
)
_FENDER_WASHER_RE = re.compile(r"\b(fender\s+washer)\b", re.I)
_FLAT_WASHER_RE = re.compile(r"\b(flat\s+washer|din\s*125)\b", re.I)
_SOCKET_HEAD_CONTEXT_RE = re.compile(
    r"\b(socket\s+head|shcs|cap\s+screw)\b",
    re.I,
)


def combined_washer_text(query: str, specification: str = "") -> str:
    return f"{query} {specification}".strip().lower()


def infer_washer_category_id(query: str, specification: str = "") -> str:
    """
    Pick McMaster browse family for washer BOM lines.

    Defaults ambiguous ``M4 washer`` to flat washers — the common BOM case.
    """
    text = combined_washer_text(query, specification)
    if not re.search(r"\bwasher\b", text):
        return "flat_washer"
    if _FENDER_WASHER_RE.search(text):
        return "fender_washer"
    if _LOCK_WASHER_RE.search(text):
        return "lock_washer"
    if _FLAT_WASHER_RE.search(text):
        return "flat_washer"
    return "flat_washer"


def lock_washer_finish_id(query: str, specification: str = "") -> str:
    """Split-lock table for socket-head stacks; general lock table otherwise."""
    text = combined_washer_text(query, specification)
    if _SOCKET_HEAD_CONTEXT_RE.search(text) or re.search(
        r"\bspring\s+washer\b", text, re.I
    ):
        return "split_socket"
    return "general"


def is_washer_category(category_id: str) -> bool:
    return category_id in WASHER_CATEGORY_IDS or category_id == "washer"
