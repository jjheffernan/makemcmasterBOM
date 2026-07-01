from fractions import Fraction

_STANDARD_HEADERS = {
    "PART_NUMBER": "Part Number",
    "PRICING": "Price",
}


def get_header_text(col_id: int, meta: dict):
    # Column Id -> Column Metadata
    column_metas = meta["ColumnIdToMetadata"]
    column_meta = column_metas[col_id]

    header_type = column_meta.get("Type")
    if isinstance(header_type, str) and header_type in _STANDARD_HEADERS:
        return _STANDARD_HEADERS[header_type]
    else:
        # Column Metadata -> Header
        return _extract_text(column_meta)


def get_cell_text(cell_id: int, meta: dict):
    # Cell ID -> Value Metadata ID
    cell_metas = meta["CellIdToCellMetadata"]
    cell_meta = cell_metas[cell_id]
    value_meta_id = cell_meta["ValueMetadataIds"][0]

    # Value Metadata ID -> Value Metadata
    value_metas = meta["ValueMetadataIdToValueMetadata"]
    value_meta = value_metas[value_meta_id]

    # Value Metadata -> Value
    return _extract_text(value_meta)


def _extract_text(meta_item: dict):
    components = meta_item["Name"]["Components"]
    text = " ".join(c["Text"] for c in components)

    return _parse_number(text)


# TODO parse units and normalize imperial vs metric based on pref
def _parse_number(text: str):
    t = text.replace('"', "").strip()

    if t == "":
        return t

    try:
        return float(t)
    except ValueError:
        pass

    try:
        fraction = sum(Fraction(part) for part in t.split())
        return float(fraction)
    except ValueError:
        pass

    return text
