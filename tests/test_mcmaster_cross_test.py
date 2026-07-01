"""Offline cross-test: matcher vs pipeline on curated McMaster cases."""

from __future__ import annotations

import pytest

from backend.services.vendors.mcmaster.cross_test import (
    format_cross_test_report,
    load_cross_test_cases,
    run_offline_cross_test,
)


def test_mcmaster_regression_catalog_loads():
    cases = load_cross_test_cases()
    assert len(cases) >= 5
    assert any("M3x16" in case.label for case in cases)


def test_offline_cross_test_all_pass():
    results = run_offline_cross_test()
    report = format_cross_test_report(results)
    failed = [r for r in results if not r.ok]
    assert not failed, report


def test_match_part_equals_match_parts_only_on_catalog():
    from backend.models.part import Part
    from backend.services.matcher import match_part
    from backend.services.pipeline import match_parts_only

    part = Part(original_name="M3 Hex Nut", specification="18-8 stainless")
    single = match_part(part)
    pipeline = match_parts_only([part])[0]
    assert single.mcmaster_url == pipeline.mcmaster_url
    assert single.match_tier == pipeline.match_tier


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_cross_test_filtered_browse(monkeypatch):
    monkeypatch.setenv("MCMASTER_BROWSE_RESOLVE_ENABLED", "1")
    from backend.services.vendors.mcmaster.cross_test import run_live_case, load_cross_test_cases

    case = next(c for c in load_cross_test_cases() if "M3x16 SHCS — black oxide" in c.label)
    result = await run_live_case(case)
    assert result.app_pipeline_match
    if result.errors:
        pytest.skip(f"Live McMaster unavailable: {result.errors[0]}")
    assert (result.live_row_count or 0) > 0
    assert result.live_sku_found is True
