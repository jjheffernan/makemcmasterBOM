"""Extract and validate McMaster catalog part numbers from BOM text."""

from __future__ import annotations

import re

from backend.services.vendors.mcmaster.urls import part_number_from_url

# McMaster SKUs: 4–5 digits + letter + 2–3 digits (e.g. 91290A120, 5972K113)
MCMASTER_PART_NUMBER_RE = re.compile(r"\b([0-9]{4,5}[A-Z][0-9]{2,3})\b")


def normalize_part_number(value: str) -> str:
    return value.strip().upper()


def is_valid_part_number(value: str) -> bool:
    return bool(MCMASTER_PART_NUMBER_RE.fullmatch(normalize_part_number(value)))


def extract_part_numbers(text: str) -> list[str]:
    """All unique McMaster part numbers mentioned in free text."""
    seen: set[str] = set()
    ordered: list[str] = []
    for match in MCMASTER_PART_NUMBER_RE.finditer(text):
        pn = normalize_part_number(match.group(1))
        if pn not in seen:
            seen.add(pn)
            ordered.append(pn)
    return ordered


def extract_part_number_from_text(text: str) -> str | None:
    numbers = extract_part_numbers(text)
    return numbers[0] if numbers else None


def extract_part_number_from_url(url: str) -> str | None:
    return part_number_from_url(url)
