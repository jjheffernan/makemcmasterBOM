"""Filtered-browse finish variants — same thread/length, different McMaster material routes."""

from __future__ import annotations

from backend.models.part import BrowseFinishOption, Part
from backend.services.vendors.mcmaster.browse_roots import (
    BrowseRoot,
    get_browse_root,
    get_metric_finish_root,
    list_finish_roots,
)
from backend.services.vendors.mcmaster.filters import (
    infer_finish_from_bom,
    infer_material_variant_id,
)
from backend.services.vendors.mcmaster.urls import filtered_browse_url


def applicable_finish_roots(
    category_id: str,
    query: str,
    specification: str,
) -> list[BrowseRoot]:
    """
    Finish roots to hydrate — one precise table per BOM line.

    Ambiguous metric nuts/washers use the metric catalog (not imperial material
  roots with metric thread filters). Ambiguous screws default to black oxide
  only; name a finish in the BOM to target zinc or stainless.
    """
    bom_finish = infer_finish_from_bom(query, specification)
    if bom_finish:
        root = get_browse_root(category_id, bom_finish)
        return [root] if root else []

    if category_id in {"nut", "washer"}:
        metric = get_metric_finish_root(category_id)
        return [metric] if metric else []

    default_id = infer_material_variant_id(
        query,
        specification,
        category_id=category_id,
    )
    root = get_browse_root(category_id, default_id)
    if root:
        return [root]
    material_roots = list_finish_roots(category_id)
    return material_roots[:1]


def default_finish_id(
    category_id: str,
    query: str,
    specification: str,
) -> str:
    bom_finish = infer_finish_from_bom(query, specification)
    if bom_finish:
        return bom_finish
    from backend.services.vendors.mcmaster.filters import infer_material_variant_id

    return infer_material_variant_id(
        query,
        specification,
        category_id=category_id,
    )


def build_browse_finish_options(
    query: str,
    part: Part,
    *,
    category_id: str,
    filter_path: str,
) -> list[BrowseFinishOption]:
    """Build same-spec McMaster browse URLs for each applicable finish."""
    if not filter_path.strip():
        return []

    roots = applicable_finish_roots(category_id, query, part.specification)
    options: list[BrowseFinishOption] = []
    for root in roots:
        options.append(
            BrowseFinishOption(
                finish_id=root.finish_id,
                label=root.finish_label,
                mcmaster_url=filtered_browse_url(
                    root.route,
                    filter_path,
                    search_query=query,
                ),
            )
        )
    return options


def finish_option_for_id(
    options: list[BrowseFinishOption],
    finish_id: str,
) -> BrowseFinishOption | None:
    for option in options:
        if option.finish_id == finish_id:
            return option
    return None
