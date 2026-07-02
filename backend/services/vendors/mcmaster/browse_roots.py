"""McMaster browse-root routes for filtered category URLs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BROWSE_ROOTS_PATH = REPO_ROOT / "data" / "mcmaster_browse_roots.json"

DEFAULT_FINISH_ORDER = ("black_oxide", "zinc_plated", "stainless")

CATEGORY_FINISH_ORDER: dict[str, tuple[str, ...]] = {
    "nut": ("zinc_plated", "black_oxide", "stainless"),
    "washer": ("zinc_plated", "black_oxide", "stainless"),
}


@dataclass(frozen=True)
class BrowseRoot:
    category_id: str
    finish_id: str
    finish_label: str
    route: str

    @property
    def material_id(self) -> str:
        """Legacy alias used by older call sites."""
        return self.finish_id


@lru_cache(maxsize=1)
def _load_roots() -> tuple[BrowseRoot, ...]:
    if not BROWSE_ROOTS_PATH.is_file():
        return ()
    raw = json.loads(BROWSE_ROOTS_PATH.read_text(encoding="utf-8"))
    roots: list[BrowseRoot] = []
    for entry in raw.get("roots", []):
        finish_id = entry.get("finish_id") or entry.get("material_id", "steel")
        roots.append(
            BrowseRoot(
                category_id=entry["category_id"],
                finish_id=finish_id,
                finish_label=entry.get("finish_label")
                or entry.get("label", finish_id.replace("_", " ").title()),
                route=entry["route"],
            )
        )
    return tuple(roots)


def list_finish_roots(category_id: str) -> list[BrowseRoot]:
    """All finish browse roots for a fastener category, in default display order."""
    roots = [
        root
        for root in _load_roots()
        if root.category_id == category_id and root.finish_id != "metric"
    ]
    order_list = CATEGORY_FINISH_ORDER.get(category_id, DEFAULT_FINISH_ORDER)
    order = {finish_id: index for index, finish_id in enumerate(order_list)}
    return sorted(roots, key=lambda root: order.get(root.finish_id, 99))


def get_browse_root(category_id: str, material_id: str) -> BrowseRoot | None:
    for root in _load_roots():
        if root.category_id == category_id and root.finish_id == material_id:
            return root
    return None


def get_browse_root_by_finish(category_id: str, finish_id: str) -> BrowseRoot | None:
    return get_browse_root(category_id, finish_id)


def default_material_for_category(category_id: str) -> str:
    roots = list_finish_roots(category_id)
    if roots:
        return roots[0].finish_id
    return "black_oxide"
