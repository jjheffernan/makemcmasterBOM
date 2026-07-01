"""McMaster vendor adapter — filters, tiers, browse parse, API parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.models.part import Part
from backend.services.mcmaster_handler import build_mcmaster_link
from backend.services.vendors.mcmaster.api import parse_product_payload
from backend.services.vendors.mcmaster.browse_parse import parse_product_presentations
from backend.services.vendors.mcmaster.filters import (
    build_fastener_filters,
    metric_length_filter_slug,
    metric_thread_filter_slug,
)
from backend.services.vendors.mcmaster.part_numbers import (
    extract_part_number_from_text,
    is_valid_part_number,
)
from backend.services.vendors.mcmaster.tiers import resolve_mcmaster_link
from backend.services.vendors.mcmaster.urls import filtered_browse_url

FIXTURES = Path(__file__).parent / "fixtures"


def test_metric_filter_slugs():
    assert metric_thread_filter_slug(3) == "m3"
    assert metric_thread_filter_slug(2.5) == "m2-5"
    assert metric_length_filter_slug(16) == "16-mm"


def test_build_fastener_filters_path():
    from backend.services.hardware_spec import MetricFastenerSpec

    spec = MetricFastenerSpec(diameter_mm=3, length_mm=16, kind="screw")
    path = build_fastener_filters(spec).as_path()
    assert path == "system-of-measurement~metric/thread-size~m3/length~16-mm/"


def test_filtered_browse_url_example():
    url = filtered_browse_url(
        "/products/screws/socket-head-screws-2~/steel-socket-head-screws~~/",
        "system-of-measurement~metric/thread-size~m3/length~16-mm/",
        search_query="M3x16 socket head cap screw",
    )
    assert "system-of-measurement~metric" in url
    assert "thread-size~m3" in url
    assert "length~16-mm" in url
    assert "searchQuery=M3x16" in url


def test_resolve_filtered_browse_for_unknown_m4_socket_head():
    part = Part(original_name="M4x30 socket head cap screw", specification="")
    link = resolve_mcmaster_link("M4x30 socket head cap screw", part=part)
    assert link.tier == "filtered_browse"
    assert link.link_kind == "filtered_browse"
    assert "thread-size~m4" in link.url
    assert "length~30-mm" in link.url


def test_resolve_explicit_part_number_in_bom():
    part = Part(
        original_name="Heat insert",
        specification="McMaster 94180A331 for plastic",
    )
    link = resolve_mcmaster_link("heat insert", part=part)
    assert link.tier == "part_number"
    assert link.part_number == "94180A331"
    assert link.url.startswith("https://www.mcmaster.com/94180A331/")


def test_part_number_helpers():
    assert is_valid_part_number("91290A120")
    assert not is_valid_part_number("M3x16")
    assert extract_part_number_from_text("Use 91290A115 and 5972K113") == "91290A115"


def test_parse_product_presentations_fixture():
    payload = json.loads(
        (FIXTURES / "mcmaster_product_presentations_min.json").read_text()
    )
    rows = parse_product_presentations(payload)
    assert len(rows) == 1
    assert rows[0].part_number == "91290A120"
    assert rows[0].fields["Length"] == "16 mm"


def test_parse_official_api_product_payload():
    payload = {
        "PartNumber": "4936K451",
        "ProductStatus": "Active",
        "FamilyDescription": "Compact Extreme-Pressure Steel Pipe Fitting",
        "DetailDescription": "Adapter, 1/2 NPT Female, M20 x 1.5mm Male Thread",
        "Specifications": [
            {"Attribute": "Shape", "Values": ["Straight"]},
        ],
        "Links": [{"Key": "Price", "Value": "/v1/products/4936K451/price"}],
    }
    record = parse_product_payload(payload)
    assert record.part_number == "4936K451"
    assert record.product_status == "Active"
    assert record.specifications[0].attribute == "Shape"
    assert record.catalog_url.endswith("/4936K451")


def test_build_mcmaster_link_filtered_browse_integration():
    matched = build_mcmaster_link(
        "M4x30 socket head cap screw",
        part=Part(original_name="M4x30 socket head cap screw"),
    )
    assert matched.link_type == "filtered_browse"
    assert "length~30-mm" in matched.url
