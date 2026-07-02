"""Cross-test matcher and pipeline on curated McMaster URLs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.models.part import Part
from backend.services.matcher import match_part, match_parts
from backend.services.pipeline import match_parts_only
from backend.services.vendors.mcmaster.browse_parse import parse_product_presentations

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CATALOG_PATH = REPO_ROOT / "data" / "mcmaster_regression_urls.json"


@dataclass
class CrossTestCase:
    label: str
    part: Part
    expect: dict[str, Any]
    live: dict[str, Any] = field(default_factory=dict)
    offline_fixture: str = ""
    offline_fixture_expect_part_numbers: list[str] = field(default_factory=list)


@dataclass
class CrossTestCaseResult:
    label: str
    ok: bool
    matcher_url: str = ""
    pipeline_url: str = ""
    batch_url: str = ""
    match_tier: str = ""
    app_pipeline_match: bool = False
    batch_pipeline_match: bool = False
    expect_errors: list[str] = field(default_factory=list)
    fixture_part_numbers: list[str] = field(default_factory=list)
    live_row_count: int | None = None
    live_part_numbers: list[str] = field(default_factory=list)
    live_sku_found: bool | None = None
    errors: list[str] = field(default_factory=list)


def load_mcmaster_regression_catalog(
    path: Path | None = None,
) -> dict[str, Any]:
    catalog_path = path or DEFAULT_CATALOG_PATH
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def load_cross_test_cases(path: Path | None = None) -> list[CrossTestCase]:
    catalog = load_mcmaster_regression_catalog(path)
    cases: list[CrossTestCase] = []
    for raw in catalog.get("cases", []):
        part_data = raw.get("part", {})
        cases.append(
            CrossTestCase(
                label=raw["label"],
                part=Part(**part_data),
                expect=raw.get("expect", {}),
                live=raw.get("live", {}),
                offline_fixture=raw.get("offline_fixture", ""),
                offline_fixture_expect_part_numbers=raw.get(
                    "offline_fixture_expect_part_numbers", []
                ),
            )
        )
    return cases


def _check_expectations(matched: Part, expect: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if tier := expect.get("match_tier"):
        if matched.match_tier != tier:
            errors.append(f"match_tier: expected {tier!r}, got {matched.match_tier!r}")

    for fragment in expect.get("url_contains", []):
        if fragment not in matched.mcmaster_url:
            errors.append(f"URL missing fragment {fragment!r}")

    for fragment in expect.get("url_must_not_contain", []):
        if fragment in matched.mcmaster_url:
            errors.append(f"URL must not contain {fragment!r}")

    if finish_id := expect.get("selected_finish_id"):
        if matched.selected_finish_id != finish_id:
            errors.append(
                f"selected_finish_id: expected {finish_id!r}, "
                f"got {matched.selected_finish_id!r}"
            )

    finish_count = len(matched.browse_finish_options)
    if exact_finishes := expect.get("finish_options_count"):
        if finish_count != exact_finishes:
            errors.append(
                f"finish_options: expected exactly {exact_finishes}, got {finish_count}"
            )
    if min_finishes := expect.get("finish_options_min"):
        if finish_count < min_finishes:
            errors.append(
                f"finish_options: expected >={min_finishes}, got {finish_count}"
            )
    if max_finishes := expect.get("finish_options_max"):
        if finish_count > max_finishes:
            errors.append(
                f"finish_options: expected <={max_finishes}, got {finish_count}"
            )

    if sku := expect.get("catalog_part_number"):
        if matched.mcmaster_part_number != sku:
            alt_pns = {a.mcmaster_part_number for a in matched.match_alternatives}
            if sku not in alt_pns and matched.mcmaster_part_number != sku:
                errors.append(
                    f"catalog SKU: expected primary or alt {sku!r}, "
                    f"got {matched.mcmaster_part_number!r} alts={sorted(alt_pns)}"
                )

    if sku := expect.get("catalog_sku_in_alternatives"):
        all_pns = {matched.mcmaster_part_number} | {
            a.mcmaster_part_number for a in matched.match_alternatives
        }
        if sku not in all_pns:
            errors.append(f"expected SKU {sku!r} in primary or alternatives")

    return errors


def run_offline_case(case: CrossTestCase) -> CrossTestCaseResult:
    """Compare main matcher vs notebook pipeline path (no network)."""
    result = CrossTestCaseResult(label=case.label, ok=True)

    try:
        single = match_part(case.part)
        pipeline = match_parts_only([case.part])[0]
        batch = match_parts([case.part])[0]

        result.matcher_url = single.mcmaster_url
        result.pipeline_url = pipeline.mcmaster_url
        result.batch_url = batch.mcmaster_url
        result.match_tier = single.match_tier
        result.app_pipeline_match = single.mcmaster_url == pipeline.mcmaster_url
        result.batch_pipeline_match = single.mcmaster_url == batch.mcmaster_url

        if not result.app_pipeline_match:
            result.errors.append(
                "match_part vs match_parts_only URL mismatch "
                f"({single.mcmaster_url!r} vs {pipeline.mcmaster_url!r})"
            )
        if not result.batch_pipeline_match:
            result.errors.append(
                "match_part vs match_parts URL mismatch "
                f"({single.mcmaster_url!r} vs {batch.mcmaster_url!r})"
            )

        result.expect_errors = _check_expectations(single, case.expect)
        result.errors.extend(result.expect_errors)

        if case.offline_fixture:
            fixture_path = REPO_ROOT / case.offline_fixture
            payload = json.loads(fixture_path.read_text(encoding="utf-8"))
            parsed = parse_product_presentations(payload)
            part_numbers = sorted({row.part_number for row in parsed})
            result.fixture_part_numbers = part_numbers
            for expected_pn in case.offline_fixture_expect_part_numbers:
                if expected_pn not in part_numbers:
                    result.errors.append(
                        f"fixture missing expected part number {expected_pn!r}"
                    )

    except Exception as exc:
        result.errors.append(str(exc))

    result.ok = not result.errors
    return result


def run_offline_cross_test(path: Path | None = None) -> list[CrossTestCaseResult]:
    return [run_offline_case(case) for case in load_cross_test_cases(path)]


QUERY_ACCURACY_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "bom_listing_query_cases.json"
)


def load_query_accuracy_cases(path: Path | None = None) -> list[CrossTestCase]:
    """Load offline query-accuracy cases from the dummy BOM listing fixture."""
    return load_cross_test_cases(path or QUERY_ACCURACY_FIXTURE)


def run_query_accuracy_test(path: Path | None = None) -> list[CrossTestCaseResult]:
    return [run_offline_case(case) for case in load_query_accuracy_cases(path)]


async def run_live_case(
    case: CrossTestCase,
    *,
    refresh: bool = False,
) -> CrossTestCaseResult:
    """Fetch browse table via in-house Playwright scrape; compare to matcher URL."""
    offline = run_offline_case(case)
    result = CrossTestCaseResult(
        label=case.label,
        ok=offline.ok,
        matcher_url=offline.matcher_url,
        pipeline_url=offline.pipeline_url,
        batch_url=offline.batch_url,
        match_tier=offline.match_tier,
        app_pipeline_match=offline.app_pipeline_match,
        batch_pipeline_match=offline.batch_pipeline_match,
        expect_errors=offline.expect_errors,
        fixture_part_numbers=offline.fixture_part_numbers,
        errors=list(offline.errors),
    )

    if case.live.get("skip_browse_fetch"):
        result.ok = not result.errors
        return result

    if result.match_tier != "filtered_browse" or not result.matcher_url:
        result.ok = not result.errors
        return result

    browse_url = case.live.get("browse_url") or result.matcher_url

    try:
        from backend.services.vendors.mcmaster.browse_fetch import fetch_browse_rows

        rows = await fetch_browse_rows(browse_url, refresh=refresh)
        part_numbers = {row.part_number for row in rows}
        result.live_row_count = len(rows)
        result.live_part_numbers = sorted(part_numbers)

        expected = case.live.get("expect_part_numbers_contain", [])
        if expected:
            missing = [pn for pn in expected if pn not in part_numbers]
            result.live_sku_found = not missing
            if missing:
                result.errors.append(
                    f"live table missing expected SKUs: {missing} "
                    f"(got {len(part_numbers)} rows)"
                )

    except Exception as exc:
        result.errors.append(f"live fetch: {exc}")

    result.ok = not result.errors
    return result


async def run_live_cross_test(
    path: Path | None = None,
    *,
    refresh: bool = False,
) -> list[CrossTestCaseResult]:
    results: list[CrossTestCaseResult] = []
    for case in load_cross_test_cases(path):
        results.append(await run_live_case(case, refresh=refresh))
    return results


def format_cross_test_report(results: list[CrossTestCaseResult]) -> str:
    lines = ["McMaster cross-test report", "=" * 72]
    passed = sum(1 for r in results if r.ok)
    lines.append(f"Passed {passed}/{len(results)}")
    lines.append("")

    for result in results:
        status = "PASS" if result.ok else "FAIL"
        lines.append(f"[{status}] {result.label}")
        lines.append(f"  tier: {result.match_tier}")
        lines.append(f"  match_part URL: {_short_url(result.matcher_url)}")
        lines.append(
            f"  pipeline parity: app={result.app_pipeline_match} batch={result.batch_pipeline_match}"
        )
        if result.fixture_part_numbers:
            lines.append(f"  fixture PNs: {result.fixture_part_numbers}")
        if result.live_row_count is not None:
            lines.append(
                f"  live rows: {result.live_row_count} "
                f"sample={result.live_part_numbers[:5]}"
            )
        for err in result.errors:
            lines.append(f"  ! {err}")
        lines.append("")

    return "\n".join(lines)


def _short_url(url: str, max_len: int = 96) -> str:
    if len(url) <= max_len:
        return url
    return url[: max_len - 3] + "..."
