"""Parse McMaster ProductPresentations JSON (ProdPageWebPart) into browse rows.

Table parsing is implemented in-house. Upstream reference (mcmaster-scraper v0.2.1):
``docs/archive/mcmaster-scraper-v0.2.1/``. See docs/backend/mcmaster.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any


@dataclass(frozen=True)
class BrowseRow:
    part_number: str
    fields: dict[str, str | float]
    product_type: str = ""
    product_subtype: str = ""


def _extract_text(meta_item: dict[str, Any]) -> str | float:
    components = meta_item.get("Name", {}).get("Components", [])
    text = " ".join(c.get("Text", "") for c in components).strip()
    if not text:
        return ""
    cleaned = text.replace('"', "").strip()
    try:
        return float(cleaned)
    except ValueError:
        pass
    try:
        return float(sum(Fraction(part) for part in cleaned.split()))
    except ValueError:
        pass
    return text


def _header_text(col_id: str | int, meta: dict[str, Any]) -> str:
    column_meta = meta["ColumnIdToMetadata"][str(col_id)]
    header_type = column_meta.get("Type")
    if header_type == "PART_NUMBER":
        return "Part Number"
    if header_type == "PRICING":
        return "Price"
    return str(_extract_text(column_meta))


def _cell_id_first(cell_id: str | int | list) -> str | int:
    if isinstance(cell_id, list):
        return cell_id[0]
    return cell_id


def _cell_text(cell_id: str | int, meta: dict[str, Any]) -> str | float:
    cell_meta = meta["CellIdToCellMetadata"][str(cell_id)]
    value_meta_id = cell_meta["ValueMetadataIds"][0]
    value_meta = meta["ValueMetadataIdToValueMetadata"][str(value_meta_id)]
    return _extract_text(value_meta)


def _find_pivot_tables(root: dict[str, Any]) -> dict[tuple[str, str | None], dict]:
    if root.get("Name") == "ProductPresentations":
        nodes = [root]
    else:
        nodes = [root]
    stack: list[Any] = list(nodes)
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("Name") == "ProductPresentations":
                tables: dict[tuple[str, str | None], dict] = {}

                def title(item: dict[str, Any]) -> str:
                    return item["Display"]["Title"]

                for product in node["Data"]:
                    product_title = title(product)
                    children = [product, *product.get("Children", [])]
                    for subtype in children:
                        subtype_title = title(subtype)
                        key = (
                            (product_title, None)
                            if product_title == subtype_title
                            else (product_title, subtype_title)
                        )
                        tables[key] = subtype["Table"]
                return tables
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    raise ValueError("ProductPresentations table not found in browse JSON")


def _parse_table(table: dict[str, Any]) -> list[dict[str, str | float]]:
    primary_col_ids = table["Transformations"]["PrimaryProductGroup"]["ColumnIds"]
    if not primary_col_ids:
        primary_col_ids = table["ColumnIds"]
    primary_keys = {str(col_id) for col_id in primary_col_ids}
    meta = table["Metadata"]
    rows: list[dict[str, str | float]] = []
    for row in table["Rows"]:
        cells = {
            k: v
            for k, v in row["ColumnIdToCellIdMap"].items()
            if str(k) in primary_keys
        }
        parsed = {
            _header_text(col_id, meta): _cell_text(_cell_id_first(cell_id), meta)
            for col_id, cell_id in cells.items()
        }
        rows.append(parsed)
    return rows


def parse_product_presentations(payload: dict[str, Any]) -> list[BrowseRow]:
    """Flatten ProductPresentations tables into rows with a Part Number column."""
    tables = _find_pivot_tables(payload)
    browse_rows: list[BrowseRow] = []
    for (product_type, subtype), table in tables.items():
        for row in _parse_table(table):
            part_number = str(row.get("Part Number", "")).strip()
            if not part_number:
                continue
            fields = {k: v for k, v in row.items() if k != "Part Number"}
            browse_rows.append(
                BrowseRow(
                    part_number=part_number,
                    fields=fields,
                    product_type=product_type or "",
                    product_subtype=subtype or "",
                )
            )
    return browse_rows


def find_row_by_part_number(
    rows: list[BrowseRow],
    part_number: str,
) -> BrowseRow | None:
    target = part_number.strip().upper()
    for row in rows:
        if row.part_number.upper() == target:
            return row
    return None
