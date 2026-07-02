"""Detect BOM lines that are not meaningful McMaster catalog searches."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.services.hardware_terms import (
    BEARING_DESIGNATION_RE,
    IMPERIAL_THREAD_RE,
    METRIC_FASTENER_RE,
    METRIC_THREAD_RE,
    has_hardware_signal,
)

# Instructional / prose BOM lines (MakerWorld descriptions, assembly notes)
NATURAL_LANGUAGE_STARTERS = re.compile(
    r"^\s*(?:please|use|add|install|attach|apply|see|refer|check|note|if|when|as|for|"
    r"with|include|exclude|optional|recommended|required|ensure|make sure|do not|don't)\b",
    re.I,
)

INSTRUCTION_PHRASES = re.compile(
    r"\b(as needed|if (?:needed|required|necessary)|or similar|see (?:the )?(?:assembly )?"
    r"(?:diagram|drawing|above|below|image)|refer to|not included|user[- ]supplied|bring your own|"
    r"by user|per assembly|not on bom|bom only|for reference)\b",
    re.I,
)

MARKUP_RE = re.compile(
    r"<[^>]+>|```|\*\*[^*]+\*\*|^#+\s|\[[^\]]+\]\([^)]+\)|https?://",
    re.I | re.M,
)

NON_PART_TOKENS = re.compile(
    r"^(?:tbd|n/?a|none|null|various|misc(?:ellaneous)?|etc\.?|same as above|ditto|"
    r"——|-+|\.+|\.{3}|x{2,})$",
    re.I,
)

SYNTAX_ONLY = re.compile(r"^[\W_\d]+$")

PLACEHOLDER_RE = re.compile(
    r"\b(xxx|tbd|placeholder|sample text|lorem ipsum|insert here)\b",
    re.I,
)

FILE_EXTENSION_RE = re.compile(
    r"\.(?:stl|3mf|step|stp|iges|igs|gcode|fcstd|skp|obj)\b",
    re.I,
)

_CATALOG_TOKEN_RE = re.compile(r"\b[0-9]{5}[A-Z][0-9]{2,4}\b", re.I)


@dataclass(frozen=True)
class SearchabilityResult:
    searchable: bool
    reason: str
    category: str = ""


def _has_measurable_hardware_token(text: str) -> bool:
    if has_hardware_signal(text):
        return True
    if METRIC_FASTENER_RE.search(text):
        return True
    if METRIC_THREAD_RE.search(text) and re.search(
        r"\b(screw|bolt|nut|washer|bearing|standoff|insert|pin)\b", text, re.I
    ):
        return True
    if IMPERIAL_THREAD_RE.search(text):
        return True
    if BEARING_DESIGNATION_RE.search(text):
        return True
    if _CATALOG_TOKEN_RE.search(text):
        return True
    return False


def analyze_searchability(
    name: str,
    specification: str = "",
    *,
    normalized_query: str = "",
) -> SearchabilityResult:
    """
    Return whether a BOM line is worth sending to McMaster matching.

    Trims natural-language notes, markup, placeholders, and syntax-only rows.
    """
    combined = f"{name} {specification}".strip()
    if not combined:
        return SearchabilityResult(False, "Empty line — nothing to search", "empty")

    if NON_PART_TOKENS.match(combined.strip()):
        return SearchabilityResult(
            False, "Placeholder token — not a part name", "placeholder"
        )

    if PLACEHOLDER_RE.search(combined):
        return SearchabilityResult(
            False, "Placeholder text — not a catalog line", "placeholder"
        )

    if MARKUP_RE.search(combined):
        return SearchabilityResult(
            False, "Markup or URL — not a searchable part name", "markup"
        )

    if FILE_EXTENSION_RE.search(combined):
        return SearchabilityResult(
            False, "CAD/file reference — not purchasable hardware", "file_reference"
        )

    if INSTRUCTION_PHRASES.search(combined):
        return SearchabilityResult(
            False, "Instruction text — trimmed from McMaster matching", "instruction"
        )

    if combined.strip().endswith("?"):
        if not (
            METRIC_FASTENER_RE.search(combined)
            or IMPERIAL_THREAD_RE.search(combined)
            or _CATALOG_TOKEN_RE.search(combined)
        ):
            return SearchabilityResult(
                False, "Question text — not a searchable part name", "natural_language"
            )

    if NATURAL_LANGUAGE_STARTERS.search(combined) and not _has_measurable_hardware_token(
        combined
    ):
        return SearchabilityResult(
            False,
            "Natural language note — trimmed from McMaster matching",
            "natural_language",
        )

    compact = combined.replace(" ", "")
    if SYNTAX_ONLY.match(compact):
        return SearchabilityResult(
            False, "Symbols or numbers only — not a part name", "syntax"
        )

    words = combined.split()
    if (
        len(words) >= 8
        and not _has_measurable_hardware_token(combined)
        and not _CATALOG_TOKEN_RE.search(normalized_query or combined)
    ):
        return SearchabilityResult(
            False,
            "Reads like assembly notes, not hardware — trimmed from McMaster matching",
            "natural_language",
        )

    return SearchabilityResult(True, "", "")
