"""Filtered-browse finish variants — same thread/length, different McMaster material routes."""

from __future__ import annotations

from backend.models.part import BrowseFinishOption, Part
from backend.services.vendors.mcmaster.browse_roots import (
    BrowseRoot,
    default_material_for_category,
    list_finish_roots,
)
from backend.services.vendors.mcmaster.filters import infer_finish_from_bom
from backend.services.vendors.mcmaster.urls import filtered_browse_url


def applicable_finish_roots(
    category_id: str,
    query: str,
    specification: str,
) -> list[BrowseRoot]:
    """Finish roots to offer — one when BOM names a finish, all when ambiguous."""
    roots = list_finish_roots(category_id)
    if not roots:
        return []

    bom_finish = infer_finish_from_bom(query, specification)
    if bom_finish:
        matched = [root for root in roots if root.finish_id == bom_finish]
        return matched or roots[:1]

    return roots


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
