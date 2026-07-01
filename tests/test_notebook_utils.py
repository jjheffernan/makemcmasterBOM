import pytest

from backend.models.part import Part
from backend.notebook_utils import (
    load_local_bom_file,
    load_regression_catalog,
    pick_sample_url,
    prepare_crawl_env,
    print_pipeline_map,
)
from backend.services.pipeline import match_parts_only, parse_bom_only


def test_load_regression_catalog():
    catalog = load_regression_catalog()
    assert len(catalog["urls"]) >= 1


def test_pick_sample_url_prefers_bom():
    entry = pick_sample_url(catalog=load_regression_catalog(), require_bom=True)
    assert "url" in entry


def test_load_local_bom_sample():
    prepare_crawl_env(reload_backend=False)
    loaded = load_local_bom_file()
    assert loaded is not None
    content, name = loaded
    assert name.endswith(".csv")
    assert b"Part Name" in content


def test_print_pipeline_map(capsys):
    print_pipeline_map()
    out = capsys.readouterr().out
    assert "validate" in out
    assert "import_from_url" in out or "pipeline" in out


def test_parse_and_match_stages_match_api():
    content, name = load_local_bom_file()
    assert content is not None
    parts = parse_bom_only(content, name)  # type: ignore[arg-type]
    matched = match_parts_only(parts)
    assert len(matched) == len(parts)
    assert all(p.mcmaster_url or p.mcmaster_status == "not_applicable" for p in matched)
