from io import UnsupportedOperation

from pandas import DataFrame, concat

from ._text_parser import get_cell_text, get_header_text


def get_products_table(json: dict) -> DataFrame:
    tables = _find_pivot_tables(json)
    dataframes = {
        (product, subtype): _parse_pivot_table(table)
        for (product, subtype), table in tables.items()
    }

    # Only show the product type/subtype if there is more than 1 unique value
    unique_products = {p for p, _ in dataframes.keys()}
    unique_subtypes = {s for _, s in dataframes.keys()}
    show_product_type = len(unique_products) > 1
    show_subtype = len(unique_subtypes) > 1

    dataframes_with_product_type = [
        df.assign(
            **{
                **({"Product Type": product} if show_product_type else {}),
                **({"Product Subtype": subtype} if show_subtype else {}),
            }
        )
        for (product, subtype), df in dataframes.items()
    ]

    return concat(dataframes_with_product_type, ignore_index=True)


def _find_pivot_tables(root: dict) -> dict:
    stack = [root]
    while stack:
        node = stack.pop()

        if isinstance(node, dict):
            if node.get("Name") == "ProductPresentations":

                def get_table_title(item: dict) -> str:
                    return item["Display"]["Title"]

                def get_table_key(
                    product: dict, subtype: dict
                ) -> tuple[str, str | None]:
                    if product == subtype:
                        return get_table_title(product), None
                    else:
                        return get_table_title(product), get_table_title(subtype)

                tables = {
                    get_table_key(product, subtype): subtype["Table"]
                    for product in node["Data"]
                    for subtype in [product, *product["Children"]]
                }

                return tables
            else:
                stack.extend(node.values())

        elif isinstance(node, list):
            stack.extend(node)

    raise UnsupportedOperation("Product table extraction is unsupported for this page.")


def _parse_pivot_table(table: dict) -> DataFrame:
    # For tables with multiple products in the same row,
    # only get the columns for the primary product
    primary_col_ids = table["Transformations"]["PrimaryProductGroup"]["ColumnIds"]

    # For tables with only one product per row, PrimaryProductGroup will be empty
    # Fallback to all columns instead
    if len(primary_col_ids) == 0:
        primary_col_ids = table["ColumnIds"]

    rows = table["Rows"]
    meta = table["Metadata"]

    def get_row_data(row: dict):
        # Some tables have multiple primary parts in a single row
        # Those tables have a "horizontalPivotGrouping" key in each ColumnIdToCellIdMap
        # We only care about the entries that are column IDs, so we filter the rest out
        cells = {
            k: v for k, v in row["ColumnIdToCellIdMap"].items() if k in primary_col_ids
        }
        return {
            get_header_text(cell[0], meta): get_cell_text(cell[1], meta)
            for cell in cells.items()
        }

    data = [get_row_data(row) for row in rows]
    return DataFrame(data)
