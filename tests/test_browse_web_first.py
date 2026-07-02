"""Tests for live browse row selection and web-first matching policy."""

from backend import config
from backend.models.part import Part
from backend.services.vendors.mcmaster.browse_parse import BrowseRow
from backend.services.vendors.mcmaster.browse_row_select import pick_best_browse_row
from backend.services.vendors.mcmaster.candidates import collect_scored_candidates


def test_pick_best_browse_row_by_length():
    part = Part(original_name="M3x16 socket head cap screw")
    rows = [
        BrowseRow(
            part_number="91290A112",
            fields={"Length": "12 mm", "Thread Size": "M3"},
        ),
        BrowseRow(
            part_number="91290A120",
            fields={"Length": "16 mm", "Thread Size": "M3"},
        ),
    ]
    picked = pick_best_browse_row(part, rows)
    assert picked is not None
    assert picked.part_number == "91290A120"


def test_pick_best_browse_row_prefiltered_url_returns_first():
    part = Part(original_name="M3 Nut")
    rows = [
        BrowseRow(part_number="90591A110", fields={"Thread Size": "M3"}),
        BrowseRow(part_number="90591A111", fields={"Thread Size": "M3"}),
    ]
    url = (
        "https://www.mcmaster.com/products/hex-nuts/zinc-plated-steel-hex-nuts~~/"
        "system-of-measurement~metric/thread-size~m3/"
    )
    picked = pick_best_browse_row(part, rows, browse_url=url)
    assert picked is not None
    assert picked.part_number == "90591A110"


def test_catalog_demoted_when_browse_resolve_enabled(monkeypatch):
    monkeypatch.setattr(config, "MCMASTER_BROWSE_RESOLVE_ENABLED", True)
    part = Part(original_name="M3 Hex Nut", specification="18-8 stainless")
    candidates = collect_scored_candidates("M3 hex nut", part)
    primary = candidates[0]
    assert primary.link.tier == "filtered_browse"
    catalog = next(c for c in candidates if c.link.part_number == "91828A113")
    assert catalog.link.method == "catalog_cache"
    assert catalog.confidence <= 0.72


def test_catalog_primary_when_browse_resolve_disabled(monkeypatch):
    monkeypatch.setattr(config, "MCMASTER_BROWSE_RESOLVE_ENABLED", False)
    part = Part(original_name="M3 Hex Nut", specification="18-8 stainless")
    candidates = collect_scored_candidates("M3 hex nut", part)
    assert candidates[0].link.tier == "filtered_browse"
    catalog = next(c for c in candidates if c.link.part_number == "91828A113")
    assert catalog.link.tier in {"catalog", "rule"}
