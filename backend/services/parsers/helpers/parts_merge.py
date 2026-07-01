"""Merge multiple part lists from different BOM sources."""

from __future__ import annotations

from backend.models.part import Part


def merge_parts(*lists: list[Part]) -> list[Part]:
    """Combine part lists; first list wins on duplicate name+quantity."""
    merged: list[Part] = []
    seen: set[tuple[str, float]] = set()
    for parts in lists:
        for part in parts:
            key = (part.original_name.strip().lower(), part.quantity)
            if key in seen:
                continue
            seen.add(key)
            merged.append(part)
    return merged
