"""Catalog JSON must stay internally consistent (offline)."""

from backend.services.catalog_integrity import check_catalog_integrity


def test_catalog_integrity_passes() -> None:
    issues = check_catalog_integrity()
    assert not issues, "\n".join(
        f"{i.code}: {i.part_number} — {i.message}" for i in issues
    )
