"""Shared hydration cache — avoid duplicate McMaster fetches within one import."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.models.part import BrowseFinishOption, Part


@dataclass
class HydrationSession:
    """In-memory dedup for a single enrich_parts / import batch."""

    url_variants: dict[tuple[str, str], BrowseFinishOption] = field(
        default_factory=dict
    )
    group_templates: dict[str, tuple[list[BrowseFinishOption], str]] = field(
        default_factory=dict
    )

    def variant_key(self, browse_url: str, finish_id: str) -> tuple[str, str]:
        return (browse_url.strip(), finish_id.strip())

    def get_cached_option(
        self, browse_url: str, finish_id: str
    ) -> BrowseFinishOption | None:
        return self.url_variants.get(self.variant_key(browse_url, finish_id))

    def store_option(
        self, browse_url: str, finish_id: str, option: BrowseFinishOption
    ) -> None:
        self.url_variants[self.variant_key(browse_url, finish_id)] = option

    def get_group_template(
        self, group_key: str
    ) -> tuple[list[BrowseFinishOption], str] | None:
        return self.group_templates.get(group_key)

    def store_group_template(
        self,
        group_key: str,
        options: list[BrowseFinishOption],
        selected_finish_id: str,
    ) -> None:
        self.group_templates[group_key] = (options, selected_finish_id)


def hydration_group_key(part: Part) -> str:
    """Stable key for BOM lines that share the same McMaster browse resolution."""
    name = (part.normalized_name or part.original_name).strip().lower()
    spec = part.specification.strip().lower()
    category = part.mcmaster_category.strip().lower()
    tier = part.match_tier.strip().lower()
    filter_path = ""
    if part.mcmaster_url and "thread-size~" in part.mcmaster_url.lower():
        from backend.services.vendors.mcmaster.browse_finish_hydrate import (
            _filter_path_from_url,
        )

        filter_path = _filter_path_from_url(part.mcmaster_url)
    finish_ids = ",".join(
        sorted(option.finish_id for option in part.browse_finish_options)
    )
    return "|".join([name, spec, category, tier, filter_path, finish_ids])


def part_already_hydrated(part: Part) -> bool:
    """True when live browse already resolved SKUs and finish variants."""
    if part.mcmaster_status == "not_applicable":
        return True
    if not part.mcmaster_part_number:
        return False
    if part.browse_finish_options:
        return all(
            option.mcmaster_part_number for option in part.browse_finish_options
        )
    return bool(part.price_source or part.unit_cost)
