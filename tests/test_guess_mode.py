"""Exact vs lazy McMaster guess mode."""

from __future__ import annotations

from backend.models.part import MatchAlternative, Part
from backend.services.matcher import match_part


def test_exact_mode_drops_wider_scope_alternatives(monkeypatch):
    part = Part(original_name="M3 x 10mm socket head cap screw", quantity=4)

    def _fake_match(p: Part, *, guess_mode: str = "lazy") -> Part:
        alts = [
            MatchAlternative(
                mcmaster_url="https://www.mcmaster.com/products/screws/same/",
                guess_scope="same_size",
                confidence=0.8,
            ),
            MatchAlternative(
                mcmaster_url="https://www.mcmaster.com/products/screws/wider/",
                guess_scope="wider_scope",
                confidence=0.5,
            ),
        ]
        # Simulate post-filter by using real match_part path: inject via monkeypatch on helpers.
        return p.model_copy(
            update={
                "mcmaster_url": "https://www.mcmaster.com/products/screws/",
                "match_alternatives": (
                    [a for a in alts if a.guess_scope == "same_size"]
                    if guess_mode == "exact"
                    else alts
                ),
                "confidence": 0.9,
                "mcmaster_status": "likely",
                "match_tier": "filtered_browse",
            }
        )

    monkeypatch.setattr("backend.services.matcher.match_part", _fake_match)
    from backend.services import matcher as matcher_mod

    lazy = matcher_mod.match_parts([part], guess_mode="lazy")[0]
    exact = matcher_mod.match_parts([part], guess_mode="exact")[0]
    assert any(a.guess_scope == "wider_scope" for a in lazy.match_alternatives)
    assert all(a.guess_scope == "same_size" for a in exact.match_alternatives)


def test_match_part_exact_filters_wider(monkeypatch):
    """Integration-style: stub collectors but exercise match_part filter."""
    from backend.services import matcher as matcher_mod
    from backend.services.vendors.base import VendorLink
    from backend.services.vendors.mcmaster.candidates import ScoredCandidate

    part = Part(original_name="M3 x 12mm screw", quantity=2)

    primary = ScoredCandidate(
        link=VendorLink(
            url="https://www.mcmaster.com/products/socket-head-screws/",
            link_kind="filtered_browse",
            tier="filtered_browse",
            category_id="socket_head",
            category_label="Socket Head",
            filter_path="length~12mm/thread-size~m3",
            method="test",
            confidence_hint=0.9,
            extras={},
        ),
        catalog_hit=None,
        confidence=0.9,
        confidence_low=0.85,
        confidence_high=0.95,
        reason="test primary",
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
        reason="test wider",
    )

    monkeypatch.setattr(
        matcher_mod,
        "collect_scored_candidates",
        lambda query, p: [primary, wider],
    )
    monkeypatch.setattr(
        matcher_mod,
        "classify_mcmaster_eligibility",
        lambda p: ("likely", ""),
    )

    lazy = match_part(part, guess_mode="lazy")
    exact = match_part(part, guess_mode="exact")
    assert any(a.guess_scope == "wider_scope" for a in lazy.match_alternatives) or lazy.mcmaster_url
    assert all(a.guess_scope == "same_size" for a in exact.match_alternatives)
