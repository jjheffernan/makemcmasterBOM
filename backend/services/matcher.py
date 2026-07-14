"""McMaster-Carr link matcher — prototype in notebooks/04_match_mcmaster.ipynb."""

from __future__ import annotations

import re

from backend.models.part import McMasterStatus, Part
from backend.services.hardware_terms import (
    FASTENER_TYPE_RE,
    HARDWARE_KEYWORDS,
    IMPERIAL_THREAD_RE,
    METRIC_FASTENER_RE,
    has_hardware_signal,
)

from backend.services.hardware_match_verify import (
    apply_match_check_to_part,
    correct_hardware_match,
    verify_hardware_match,
)
from backend.services.hardware_spec import (
    build_explicit_fastener_query,
    primary_fastener_spec,
)
from backend.services.mcmaster_catalog import catalog_lookup
from backend.services.mcmaster_handler import build_mcmaster_link
from backend.services.vendors.mcmaster.metacategories import (
    infer_bom_metacategory,
    metacategory_label,
    resolve_link_metacategory,
)
from backend.services.vendors.mcmaster.candidates import (
    collect_scored_candidates,
    pick_primary_and_alternatives,
    alternatives_with_scope,
)
from backend.services.vendors.mcmaster.finish_browse import (
    build_browse_finish_options,
    default_finish_id,
    finish_option_for_id,
)
from backend.services.vendors.mcmaster.tiers import vendor_link_to_handler_link

MAKERWORLD_CATEGORY_SPECS = frozenset({
    "maker's supply",
    "makers supply",
    "filament",
    "materials",
})

FASTENER_ABBREVIATIONS: dict[str, str] = {
    "shcs": "socket head cap screw",
    "bhcs": "button head cap screw",
    "fhcs": "flat head cap screw",
    "fhsc": "flat head socket cap screw",
    "csfh": "countersunk flat head screw",
    "cheese head": "cheese head screw",
}

DIN_STANDARDS: dict[str, str] = {
    "din912": "socket head cap screw",
    "din931": "hex bolt",
    "din933": "hex bolt",
    "din934": "hex nut",
    "din985": "nyloc nut",
    "iso4762": "socket head cap screw",
}

MAKERWORLD_QTY_SUFFIX_RE = re.compile(r"\s*\(\d+\s*PCS?\)\s*", re.I)
MAKERWORLD_SKU_SUFFIX_RE = re.compile(r"\s*-\s*[A-Z]{1,2}[-]?\w{3,}\s*$", re.I)

NOT_APPLICABLE_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(3d\s*print|3d-?print|printed|print in place|print-in-place|"
            r"pla\b|petg|abs\b|tpu\b|asa\b|resin|filament|stl\b|"
            r"makerworld|bambu|makerlab)\b",
            re.I,
        ),
        "3D-printed part — not sold on McMaster-Carr",
    ),
    (
        re.compile(
            r"\b(arduino|raspberry\s*pi|esp32|esp8266|stm32|microcontroller|"
            r"mcu\b|pcb|breadboard|solder|gpio|jumper|dupont|"
            r"stepper\s+motor|servo\s+motor|dc\s+motor|brushless\s+motor|"
            r"led\b|neopixel|lcd\b|oled|display\s+module|camera\s+module|"
            r"usb\s+cable|hdmi|power\s+supply|battery|lipo|buck\s+converter|"
            r"hotend|nozzle|heatbed|thermistor|endstop)\b",
            re.I,
        ),
        "Electronics or printer component — use DigiKey, Mouser, or Amazon",
    ),
    (
        re.compile(
            r"\b(download|digital\s+file|gcode|\.stl|\.3mf|\.step\b|"
            r"cad\s+file|model\s+file|thingiverse)\b",
            re.I,
        ),
        "Digital file — not a purchasable hardware item",
    ),
    (
        re.compile(
            r"\b(glue\s+stick|super\s+glue|loctite|epoxy|tape\s+roll|"
            r"zip\s+tie\s+pack|label\s+sticker)\b",
            re.I,
        ),
        "Consumable — McMaster may not carry this specific product",
    ),
]

MAKERWORLD_NON_MCMASTER_NOTES = re.compile(
    r"makerworld bom \((filament|materials)\)",
    re.I,
)
CUSTOM_PART_HINTS = re.compile(
    r"\b(body|cover|housing|enclosure|shell|lid|door|cap|knob|handle|"
    r"spacer|widget|mount|plate|base|frame|adapter|dock|tray|organizer|"
    r"bracket)\b",
    re.I,
)

VAGUE_PART = re.compile(
    r"^(part|item|component|piece|object|model)\s*[#\d]*$",
    re.I,
)


def _clean_specification(specification: str) -> str:
    spec = specification.strip()
    if not spec:
        return ""
    lower = spec.lower()
    if lower in MAKERWORLD_CATEGORY_SPECS or lower.startswith("makerworld bom"):
        return ""
    return spec


def _strip_makerworld_name_noise(text: str) -> str:
    text = MAKERWORLD_QTY_SUFFIX_RE.sub(" ", text)
    text = MAKERWORLD_SKU_SUFFIX_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_metric_dimensions(text: str) -> str:
    return METRIC_FASTENER_RE.sub(
        lambda m: f"M{m.group(1)}x{m.group(2)}",
        text,
    )


def _expand_fastener_abbreviations(text: str) -> str:
    for abbr, expansion in FASTENER_ABBREVIATIONS.items():
        text = re.sub(rf"\b{re.escape(abbr)}\b", expansion, text, flags=re.I)
    for code, expansion in DIN_STANDARDS.items():
        text = re.sub(rf"\b{re.escape(code)}\b", expansion, text, flags=re.I)
    return text


def _infer_missing_fastener_type(text: str) -> str:
    if FASTENER_TYPE_RE.search(text):
        return text
    if METRIC_FASTENER_RE.search(text) or IMPERIAL_THREAD_RE.search(text):
        return f"{text} screw"
    return text


def _has_hardware_signal(text: str) -> bool:
    return has_hardware_signal(text)


def _part_text(part: Part) -> str:
    return f"{part.original_name} {part.specification} {part.notes}".strip()


def classify_mcmaster_eligibility(part: Part) -> tuple[McMasterStatus, str]:
    """Determine whether McMaster-Carr is expected to carry this BOM line."""
    if MAKERWORLD_NON_MCMASTER_NOTES.search(part.notes):
        return "not_applicable", "Filament or build material — not sold on McMaster-Carr"

    text = f"{part.original_name} {part.specification}".strip()

    if not text:
        return "not_applicable", "Empty part name — nothing to search"

    for pattern, reason in NOT_APPLICABLE_RULES:
        if pattern.search(text):
            return "not_applicable", reason

    name = part.original_name.strip()
    if VAGUE_PART.match(name):
        return "unlikely", "Vague part name — verify manually or rename before searching"

    query = normalize_hardware_name(part.original_name, part.specification)
    if not query:
        return "not_applicable", "No searchable terms after normalization"

    from backend.services.searchability import analyze_searchability

    searchability = analyze_searchability(
        part.original_name,
        part.specification,
        normalized_query=query,
    )
    if not searchability.searchable:
        return "not_applicable", searchability.reason

    if CUSTOM_PART_HINTS.search(query) and not _has_hardware_signal(query):
        return (
            "unlikely",
            "Custom or printed-style part — McMaster is unlikely to stock this exact item",
        )

    return "possible", ""


def _singularize_fastener_terms(text: str) -> str:
    """Normalize plural BOM fastener words for category routing."""
    return re.sub(
        r"\b(screw|bolt|nut|washer|stud|insert)s\b",
        r"\1",
        text,
        flags=re.I,
    )


def normalize_hardware_name(name: str, specification: str = "") -> str:
    spec = _clean_specification(specification)
    combined = f"{name} {spec}".strip()
    combined = _strip_makerworld_name_noise(combined)
    combined = re.sub(r"\s+", " ", combined)
    combined = _singularize_fastener_terms(combined)
    combined = re.sub(
        r"\b(printed|3d\s*print|makerworld|optional|recommended)\b",
        "",
        combined,
        flags=re.I,
    )
    combined = re.sub(r"\s+", " ", combined).strip()
    combined = _normalize_metric_dimensions(combined)
    combined = _expand_fastener_abbreviations(combined)
    combined = _infer_missing_fastener_type(combined)
    return combined.strip()


def build_search_query(part: Part) -> str:
    name_only = normalize_hardware_name(part.original_name, "")
    full = normalize_hardware_name(part.original_name, part.specification)

    primary_from_name = primary_fastener_spec(
        Part(original_name=part.original_name, specification="", notes="")
    )

    if part.specification.strip() and primary_from_name:
        primary_full = primary_fastener_spec(part)
        if primary_full and (
            primary_full.diameter_mm != primary_from_name.diameter_mm
            or (
                primary_full.length_mm is not None
                and primary_from_name.length_mm is not None
                and primary_full.length_mm != primary_from_name.length_mm
            )
        ):
            if primary_from_name.length_mm is not None:
                return build_explicit_fastener_query(
                    primary_from_name,
                    hint_text=f"{part.original_name} {part.specification}",
                )
            return name_only

    rich_type = re.compile(
        r"\b(socket head|button head|hex bolt|flat head|countersink(?:ed)?|cheese head)\b",
        re.I,
    )
    if rich_type.search(name_only):
        return name_only
    if rich_type.search(full):
        return full

    if primary_from_name and primary_from_name.length_mm is not None:
        if catalog_lookup(name_only):
            return name_only
        return build_explicit_fastener_query(
            primary_from_name,
            hint_text=part.original_name,
        )

    if primary_from_name:
        return name_only

    return full or name_only or part.original_name


def _apply_hardware_verification(
    part: Part,
    *,
    query: str,
    hit,
    link,
    confidence: float,
    base_reason: str,
) -> Part:
    check = verify_hardware_match(part, hit=hit)
    hit, link, check = correct_hardware_match(
        part, query=query, hit=hit, link=link, check=check
    )
    if check.corrected and hit:
        corrected_query = (
            build_explicit_fastener_query(check.expected, hint_text=part.original_name)
            if check.expected and check.expected.length_mm is not None
            else query
        )
        part = part.model_copy(
            update={
                "mcmaster_url": link.url,
                "mcmaster_part_number": hit.part_number,
                "mcmaster_category": link.category_id,
                "normalized_name": corrected_query,
                "mcmaster_status": "likely",
            }
        )
    elif check.status == "verified" and hit:
        part = part.model_copy(
            update={
                "mcmaster_url": link.url,
                "mcmaster_part_number": hit.part_number,
                "mcmaster_category": link.category_id,
            }
        )
    part, confidence = apply_match_check_to_part(
        part,
        check=check,
        confidence=confidence,
        base_reason=base_reason,
    )
    part = part.model_copy(update={"confidence": confidence})
    return _with_match_notes(part)


def score_confidence(
    part: Part,
    query: str,
    *,
    status: McMasterStatus,
    catalog_hit: bool = False,
    tier_hint: float | None = None,
) -> float:
    if status == "not_applicable":
        return 0.0

    if not query.strip():
        return 0.0

    if catalog_hit:
        return min(0.85, tier_hint or 0.85)

    if tier_hint is not None:
        score = min(round(tier_hint, 2), 1.0)
        if status == "unlikely":
            score = min(score, 0.25)
        return score

    score = 0.35

    if _has_hardware_signal(query):
        score += 0.35

    spec = _clean_specification(part.specification)
    if spec:
        score += 0.15

    if re.search(r"\d", query):
        score += 0.1

    if len(query.split()) >= 2:
        score += 0.05

    if status == "unlikely":
        score = min(score, 0.25)

    return min(round(score, 2), 1.0)


def resolve_status_from_confidence(
    confidence: float,
    preliminary: McMasterStatus,
) -> McMasterStatus:
    if preliminary == "not_applicable":
        return "not_applicable"
    if preliminary == "unlikely":
        return "unlikely"
    if confidence >= 0.7:
        return "likely"
    if confidence >= 0.4:
        return "possible"
    return "unlikely"


def resolve_match_status(
    confidence: float,
    preliminary: McMasterStatus,
    *,
    tier: str = "",
) -> McMasterStatus:
    """Map match tier + confidence to editor status (tuned for search-only rows)."""
    if preliminary in {"not_applicable", "unlikely"}:
        return preliminary
    if tier in {"catalog", "rule", "part_number", "api_verified"}:
        return "likely" if confidence >= 0.75 else "possible"
    if tier == "filtered_browse":
        return "likely" if confidence >= 0.65 else "possible"
    if tier == "category_search":
        return "likely" if confidence >= 0.72 else "possible"
    if tier == "site_search":
        return "possible" if confidence >= 0.3 else "unlikely"
    return resolve_status_from_confidence(confidence, preliminary)


def status_reason(
    status: McMasterStatus,
    confidence: float,
    preliminary_reason: str,
) -> str:
    if preliminary_reason:
        return preliminary_reason
    if status == "likely":
        return ""
    if status == "possible":
        return "May need manual verification on McMaster-Carr"
    if status == "unlikely":
        return "Low confidence — item may not be standard catalog hardware"
    return ""


def mcmaster_search_url(query: str) -> str:
    return build_mcmaster_link(query).url


def _link_reason(link, *, catalog_title: str | None = None) -> str:
    if link.link_type == "product" and catalog_title:
        return f"Catalog match — {catalog_title} ({link.category_label})"
    if link.link_type == "filtered_browse":
        return f"McMaster {link.category_label} filtered browse"
    if link.link_type == "category_search":
        return f"McMaster {link.category_label} search"
    return "McMaster site search"


def compute_match_option_count(part: Part) -> int:
    """Count distinct McMaster match paths offered for this BOM line."""
    finishes = len(part.browse_finish_options)
    alts = len(part.match_alternatives)
    if finishes > 0:
        return finishes + alts
    if part.mcmaster_url or part.mcmaster_part_number:
        return 1 + alts
    return alts


def _with_match_notes(part: Part) -> Part:
    """Copy match explanation into Notes so the BOM editor shows verbose sourcing context."""
    option_count = compute_match_option_count(part)
    updates: dict[str, object] = {"match_option_count": option_count}
    if option_count > 3 and part.mcmaster_status != "not_applicable":
        hint = (
            f"McMaster: {option_count} match paths for this line "
            "(finishes + alternatives) — confirm link and finish."
        )
        existing = part.notes.strip()
        if hint not in existing:
            updates["notes"] = f"{existing}\n\n{hint}" if existing else hint

    reason = part.mcmaster_reason.strip()
    if not reason:
        return part.model_copy(update=updates)
    tier = (part.match_tier or "match").replace("_", " ")
    line = f"McMaster ({tier}): {reason}"
    existing = part.notes.strip()
    if line in existing:
        return part.model_copy(update=updates)
    notes = f"{existing}\n\n{line}" if existing else line
    updates["notes"] = notes
    return part.model_copy(update=updates)


def match_part(part: Part, *, guess_mode: str = "lazy") -> Part:
    preliminary_status, preliminary_reason = classify_mcmaster_eligibility(part)
    query = build_search_query(part)
    mode = (guess_mode or "lazy").strip().lower()
    if mode not in {"exact", "lazy"}:
        mode = "lazy"

    if preliminary_status == "not_applicable":
        return _with_match_notes(
            part.model_copy(
            update={
                "normalized_name": query or part.original_name,
                "mcmaster_url": "",
                "mcmaster_part_number": "",
                "mcmaster_category": "",
                "confidence": 0.0,
                "confidence_low": None,
                "confidence_high": None,
                "mcmaster_status": "not_applicable",
                "mcmaster_reason": preliminary_reason,
                "hardware_match_status": "not_applicable",
                "match_tier": "not_applicable",
                "match_alternatives": [],
                "browse_finish_options": [],
                "selected_finish_id": "",
            }
        )
        )

    candidates = collect_scored_candidates(query, part)
    primary, alt_candidates = pick_primary_and_alternatives(
        candidates,
        query=query,
        part=part,
        max_wider_scope=0 if mode == "exact" else 3,
    )

    if primary is None or primary.link.tier in {"site_search", "not_applicable"}:
        search_reason = (
            "No McMaster category match — standard site search is disabled"
        )
        if preliminary_reason:
            search_reason = f"{preliminary_reason} ({search_reason})"
        return _with_match_notes(
            part.model_copy(
            update={
                "normalized_name": query,
                "mcmaster_url": "",
                "mcmaster_part_number": "",
                "mcmaster_category": "",
                "confidence": 0.0,
                "confidence_low": None,
                "confidence_high": None,
                "mcmaster_status": "not_applicable",
                "mcmaster_reason": search_reason,
                "hardware_match_status": "not_applicable",
                "match_tier": "not_applicable",
                "match_alternatives": [],
                "browse_finish_options": [],
                "selected_finish_id": "",
            }
        )
        )

    confidence = round(primary.confidence, 2)
    if preliminary_status == "unlikely":
        confidence = min(confidence, 0.25)
    link = vendor_link_to_handler_link(primary.link)
    alternatives = alternatives_with_scope(
        alt_candidates,
        primary,
        query=query,
        specification=part.specification,
    )
    if mode == "exact":
        alternatives = [a for a in alternatives if a.guess_scope == "same_size"]

    final_status = resolve_match_status(
        confidence,
        preliminary_status,
        tier=primary.link.tier,
    )
    reason = preliminary_reason or primary.reason
    if not preliminary_reason and primary.link.tier not in {"site_search"}:
        reason = primary.reason

    meta_id = (
        resolve_link_metacategory(
            category_id=primary.link.category_id,
            url=primary.link.url,
        )
        or infer_bom_metacategory(query, part.specification)
        or ""
    )
    meta_label = metacategory_label(meta_id) if meta_id else ""

    matched = part.model_copy(
        update={
            "normalized_name": query,
            "mcmaster_url": primary.link.url,
            "mcmaster_part_number": primary.link.part_number,
            "mcmaster_category": primary.link.category_id,
            "mcmaster_metacategory": meta_id,
            "mcmaster_metacategory_label": meta_label,
            "confidence": confidence,
            "confidence_low": primary.confidence_low,
            "confidence_high": primary.confidence_high,
            "mcmaster_status": final_status,
            "mcmaster_reason": reason,
            "match_tier": primary.link.tier,
            "match_alternatives": alternatives,
            "browse_finish_options": [],
            "selected_finish_id": "",
        }
    )

    if primary.link.tier == "filtered_browse" and primary.link.filter_path:
        finish_options = build_browse_finish_options(
            query,
            part,
            category_id=primary.link.category_id,
            filter_path=primary.link.filter_path,
        )
        default_finish = default_finish_id(
            primary.link.category_id,
            query,
            part.specification,
        )
        selected = finish_option_for_id(finish_options, default_finish)
        effective_finish = default_finish
        if selected is None and finish_options:
            effective_finish = finish_options[0].finish_id
            selected = finish_options[0]
        browse_updates: dict[str, object] = {
            "browse_finish_options": finish_options,
            "selected_finish_id": effective_finish,
        }
        if selected:
            browse_updates["mcmaster_url"] = selected.mcmaster_url
        matched = matched.model_copy(update=browse_updates)

    if primary.catalog_hit:
        return _apply_hardware_verification(
            matched,
            query=query,
            hit=primary.catalog_hit,
            link=link,
            confidence=confidence,
            base_reason=reason,
        )

    expected = primary_fastener_spec(part)
    hardware_updates: dict[str, object] = {}
    if expected:
        hardware_updates["hardware_diameter_mm"] = expected.diameter_mm
        if expected.length_mm is not None:
            hardware_updates["hardware_length_mm"] = float(expected.length_mm)
        if expected.length_mm is None and expected.kind == "screw":
            hardware_updates["hardware_match_status"] = "length_unknown"
            if not preliminary_reason:
                reason = (
                    f"{primary.reason}. Length not in BOM — confirm on McMaster."
                )
        else:
            hardware_updates["hardware_match_status"] = "unchecked"

    return _with_match_notes(
        matched.model_copy(
        update={
            **hardware_updates,
            "mcmaster_reason": reason,
        }
    )
    )


def match_parts(parts: list[Part], *, guess_mode: str = "lazy") -> list[Part]:
    return [match_part(p, guess_mode=guess_mode) for p in parts]


def summarize_mcmaster_coverage(parts: list[Part]) -> dict[str, int]:
    """Count parts by McMaster eligibility status."""
    counts: dict[str, int] = {
        "likely": 0,
        "possible": 0,
        "unlikely": 0,
        "not_applicable": 0,
    }
    for part in parts:
        counts[part.mcmaster_status] = counts.get(part.mcmaster_status, 0) + 1
    return counts
