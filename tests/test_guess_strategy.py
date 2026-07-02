"""Structured primary / secondary McMaster guess tests."""

from backend.models.part import Part
from backend.services.matcher import match_part
from backend.services.vendors.mcmaster.candidates import collect_scored_candidates, pick_primary_and_alternatives
from backend.services.vendors.mcmaster.guess_strategy import filter_specificity


def test_m3_screw_primary_is_size_filtered_browse():
    part = Part(original_name="M3x16 socket head cap screw")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "thread-size~m3" in matched.mcmaster_url
    assert "length~16-mm" in matched.mcmaster_url
    assert "Primary guess" in matched.mcmaster_reason


def test_alternatives_grouped_by_scope():
    part = Part(original_name="M3x16 socket head cap screw")
    query = "M3x16 socket head cap screw"
    candidates = collect_scored_candidates(query, part)
    primary, alts = pick_primary_and_alternatives(candidates, query=query, part=part)
    assert primary is not None
    assert primary.link.tier == "filtered_browse"
    assert filter_specificity(primary.link) >= 5

    matched = match_part(part)
    scopes = {alt.guess_scope for alt in matched.match_alternatives}
    assert "same_size" in scopes or "wider_scope" in scopes


def test_same_size_finish_alternatives_for_ambiguous_screw():
    part = Part(original_name="M4x30 socket head cap screw")
    matched = match_part(part)
    same_size = [
        alt for alt in matched.match_alternatives if alt.guess_scope == "same_size"
    ]
    assert any("Same size" in alt.mcmaster_reason for alt in same_size)


def test_imperial_screw_gets_inch_filtered_browse():
    part = Part(original_name='#6-32 x 1/2"', specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "system-of-measurement~inch" in matched.mcmaster_url
    assert "thread-size~#6-32" in matched.mcmaster_url
    assert "length~1-2-in" in matched.mcmaster_url


def test_wider_scope_includes_category_fallback():
    part = Part(original_name="M3x16 socket head cap screw")
    matched = match_part(part)
    wider = [
        alt for alt in matched.match_alternatives if alt.guess_scope == "wider_scope"
    ]
    assert wider
    assert any(
        alt.match_tier in {"catalog", "rule", "category_search"} for alt in wider
    )
