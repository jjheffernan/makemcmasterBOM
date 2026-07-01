from pandas import DataFrame

from . import async_api
from ._utils.event_loop_wrapper import run_in_loop_sync


def get_products_from_url(url: str, refresh: bool = False) -> DataFrame:
    """Gets product tables from a McMaster-Carr URL.

    If there are multiple product tables, they will be merged,
    and an additional "Product Type" column will be added.

    Parameters
    ----------
    url : str
        The URL to scrape.
        Must be a valid McMaster-Carr URL.
        The product tables must be visible on the webpage.
    refresh : bool, default False
        Whether to refresh the cached data. Default is False.

    Returns
    -------
    DataFrame
        A pandas DataFrame containing the combined product tables.

    Raises
    ------
    ValueError
        If the URL is not a valid McMaster-Carr URL.
    UnsupportedOperation
        If product table extraction is unsupported for the URL.
    """
    return run_in_loop_sync(async_api.get_products_from_url(url, refresh))


def get_products_from_urls(urls: list[str], refresh: bool = False) -> list[DataFrame]:
    """Gets product tables from a list of McMaster-Carr URLs.

    See Also
    --------
    get_products_from_url
    """
    return run_in_loop_sync(async_api.get_products_from_urls(urls, refresh))
