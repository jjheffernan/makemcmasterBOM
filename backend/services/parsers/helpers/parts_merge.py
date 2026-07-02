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


def merge_description_with_embedded(
    embedded: list[Part],
    description: list[Part],
    *,
    description_explicit: bool,
) -> list[Part]:
    """Prefer description BOM lines when the author labeled a BOM section."""
    if not description:
        return embedded
    if not embedded:
        return description
    if description_explicit:
        return merge_parts(description, embedded)
    return merge_parts(embedded, description)
