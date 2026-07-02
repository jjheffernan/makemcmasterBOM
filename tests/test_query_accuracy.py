"""Offline query-accuracy tests from dummy BOM listing fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.models.part import Part
from backend.services.matcher import match_part
from backend.services.vendors.mcmaster.cross_test import (
    QUERY_ACCURACY_FIXTURE,
    format_cross_test_report,
    load_query_accuracy_cases,
    run_query_accuracy_test,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_query_accuracy_fixture_loads():
    cases = load_query_accuracy_cases()
    assert len(cases) >= 10
    assert all(case.part.original_name for case in cases)


def test_query_accuracy_fixture_has_listing_description():
    payload = json.loads(QUERY_ACCURACY_FIXTURE.read_text(encoding="utf-8"))
    listing = payload.get("listing_description", "")
    assert "M3 Nut" in listing
    assert "socket head cap screw" in listing
    assert len(payload.get("cases", [])) >= 10


def test_query_accuracy_all_cases_pass_offline():
    results = run_query_accuracy_test()
    failed = [r for r in results if not r.ok]
    assert not failed, format_cross_test_report(results)


@pytest.mark.parametrize(
    "case",
    load_query_accuracy_cases(),
    ids=lambda case: case.label,
)
def test_query_accuracy_case(case):
    matched = match_part(case.part)
    from backend.services.vendors.mcmaster.cross_test import _check_expectations

    errors = _check_expectations(matched, case.expect)
    assert not errors, f"{case.label}: {errors}\nURL: {matched.mcmaster_url}"


def test_m3_nut_finish_urls_align_with_primary():
    """Regression: finish dropdown must target the same metric table as primary URL."""
    matched = match_part(Part(original_name="M3 Nut", specification=""))
    assert len(matched.browse_finish_options) == 1
    option = matched.browse_finish_options[0]
    assert option.finish_id == "metric"
    assert option.mcmaster_url == matched.mcmaster_url
    assert "metric-hex-nuts" in option.mcmaster_url


def test_ambiguous_screw_single_finish_not_material_grid():
    matched = match_part(Part(original_name="M3x16 socket head cap screw"))
    assert len(matched.browse_finish_options) == 1
    assert matched.selected_finish_id == "black_oxide"
    urls = {matched.mcmaster_url, matched.browse_finish_options[0].mcmaster_url}
    assert len(urls) == 1
    assert "black-oxide" in matched.mcmaster_url
