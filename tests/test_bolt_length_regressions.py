"""Bolt / screw length parse regressions (exact-mode friendliness)."""

from __future__ import annotations

import pytest

from backend.models.part import Part
from backend.services.hardware_spec import extract_fastener_specs, primary_fastener_spec
from backend.services.matcher import match_part


@pytest.mark.parametrize(
    "text,diameter,length",
    [
        ("M3x10 socket head cap screw", 3.0, 10),
        ("M3 x 10mm socket head", 3.0, 10),
        ("M3 screws 10 mm", 3.0, 10),
        ("M3x10", 3.0, 10),
        ("8 M3x12 SHCS", 3.0, 12),
        ("M3 10mm screw", 3.0, 10),
        ("M4 20 mm bolt", 4.0, 20),
        ("M2.5 6mm screw", 2.5, 6),
    ],
)
def test_extract_length_from_common_bom_forms(text, diameter, length):
    specs = extract_fastener_specs(text)
    assert any(
        s.diameter_mm == diameter and s.length_mm == length for s in specs
    ), specs
    primary = primary_fastener_spec(Part(original_name=text, quantity=1))
    assert primary is not None
    assert primary.diameter_mm == diameter
    assert primary.length_mm == length


def test_exact_mode_prefers_length_scoped_alternatives_only(monkeypatch):
    """When length is known, exact mode must not keep wider_scope alts."""
    from backend.services import matcher as matcher_mod
    from backend.services.vendors.base import VendorLink
    from backend.services.vendors.mcmaster.candidates import ScoredCandidate

    part = Part(original_name="M3 10mm screw", quantity=2)
    primary = ScoredCandidate(
        link=VendorLink(
            url="https://www.mcmaster.com/products/socket-head-screws/",
            link_kind="filtered_browse",
            tier="filtered_browse",
            category_id="socket_head",
            category_label="Socket Head",
            filter_path="length~10mm/thread-size~m3",
            method="test",
            confidence_hint=0.9,
            extras={},
        ),
        catalog_hit=None,
        confidence=0.9,
        confidence_low=0.85,
        confidence_high=0.95,
        reason="length filtered",
    )
    wider = ScoredCandidate(
        link=VendorLink(
            url="https://www.mcmaster.com/products/screws/",
            link_kind="filtered_browse",
            tier="filtered_browse",
            category_id="socket_head",
            category_label="Socket Head",
            filter_path="",
            method="test",
            confidence_hint=0.4,
            extras={},
        ),
        catalog_hit=None,
        confidence=0.4,
        confidence_low=0.3,
        confidence_high=0.5,
        reason="wider",
    )
    monkeypatch.setattr(
        matcher_mod, "collect_scored_candidates", lambda query, p: [primary, wider]
    )
    monkeypatch.setattr(
        matcher_mod, "classify_mcmaster_eligibility", lambda p: ("likely", "")
    )

    exact = match_part(part, guess_mode="exact")
    lazy = match_part(part, guess_mode="lazy")
    assert exact.mcmaster_url
    assert all(a.guess_scope == "same_size" for a in exact.match_alternatives)
    # Lazy may keep wider_scope; exact must never.
    assert any(a.guess_scope == "wider_scope" for a in lazy.match_alternatives)
    assert primary_fastener_spec(part) and primary_fastener_spec(part).length_mm == 10
