"""MakerWorld embedded BOM from __NEXT_DATA__ design payloads."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from backend.models.part import Part

FILE_URL_RE = re.compile(r"\.(csv|xlsx|xls)(?:\?|$)", re.I)


def _selected_sku_name(group: dict[str, Any]) -> str:
    sku = group.get("sku")
    spu = str(group.get("spuName") or "").strip()
    for item in group.get("productSkuList") or []:
        if item.get("sku") == sku:
            name = str(item.get("skuName") or "").strip()
            if name:
                return name
    return spu or str(sku or "Part")


def _parts_from_bom_groups(
    groups: list[dict[str, Any]] | None,
    *,
    category: str,
) -> list[Part]:
    parts: list[Part] = []
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        name = _selected_sku_name(group)
        if not name:
            continue
        qty = group.get("quantity", 1)
        try:
            quantity = float(qty) if qty is not None else 1.0
        except (TypeError, ValueError):
            quantity = 1.0
        parts.append(
            Part(
                quantity=quantity,
                original_name=name,
                specification="",
                notes=f"MakerWorld BOM ({category})",
            )
        )
    return parts


def _parts_from_other_list(items: list[dict[str, Any]] | None) -> list[Part]:
    parts: list[Part] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("nameTranslated") or item.get("name") or "").strip()
        if not name:
            continue
        qty = item.get("quantity", 1)
        try:
            quantity = float(qty) if qty is not None else 1.0
        except (TypeError, ValueError):
            quantity = 1.0
        note = str(item.get("note") or "").strip()
        parts.append(
            Part(
                quantity=quantity,
                original_name=name,
                specification=note if note and note != "MakerWorld BOM (other parts)" else "",
                notes=note or "MakerWorld BOM (other parts)",
            )
        )
    return parts


def parts_from_design(design: dict[str, Any]) -> list[Part]:
    """Build parts from MakerWorld embedded BOM fields."""
    ext = design.get("designExtension") or {}
    parts: list[Part] = []

    parts.extend(_parts_from_bom_groups(ext.get("boms_v2"), category="Maker's Supply"))
    parts.extend(
        _parts_from_bom_groups(ext.get("boms_of_materials_v2"), category="materials")
    )
    parts.extend(
        _parts_from_bom_groups(ext.get("boms_of_filaments_v2"), category="filament")
    )
    parts.extend(_parts_from_other_list(ext.get("boms_of_other_part_list")))

    if not parts:
        parts.extend(_parts_from_bom_groups(ext.get("boms"), category="Maker's Supply"))
        parts.extend(
            _parts_from_bom_groups(ext.get("boms_of_materials"), category="materials")
        )
        parts.extend(
            _parts_from_bom_groups(ext.get("boms_of_filaments"), category="filament")
        )

    return parts


def find_attachment_urls(
    design: dict[str, Any],
    page_url: str,
) -> list[tuple[str, str]]:
    """Find downloadable BOM file URLs inside the design JSON tree."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    def visit(obj: Any) -> None:
        if isinstance(obj, dict):
            url = obj.get("url") or obj.get("fileUrl") or obj.get("downloadUrl")
            name = (
                obj.get("name")
                or obj.get("fileName")
                or obj.get("modelFileName")
                or ""
            )
            if isinstance(url, str) and FILE_URL_RE.search(url):
                absolute = url if url.startswith("http") else f"{page_url.rstrip('/')}/{url.lstrip('/')}"
                filename = str(name).strip() or urlparse(absolute).path.split("/")[-1]
                if absolute not in seen:
                    seen.add(absolute)
                    found.append((absolute, filename or "bom.csv"))
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    visit(design.get("designExtension") or {})
    visit(design.get("preset") or {})
    return found


def score_attachment(url: str, filename: str) -> int:
    label = f"{url} {filename}".lower()
    score = 0
    if "bom" in label or "bill" in label:
        score += 10
    if filename.lower().endswith(".csv"):
        score += 5
    if filename.lower().endswith(".xlsx"):
        score += 3
    return score


def best_attachment(candidates: list[tuple[str, str]]) -> tuple[str, str] | None:
    if not candidates:
        return None
    return max(candidates, key=lambda item: score_attachment(item[0], item[1]))
