from asyncio import create_task, gather

from pandas import DataFrame

from ._api.scraper import get_product_api_response
from ._api.table_parser import get_products_table
from ._utils.cache import get_cached, set_cached
from ._utils.event_loop_wrapper import run_in_loop_async


async def get_products_from_url(url: str, refresh: bool = False) -> DataFrame:
    """Gets product tables from a McMaster-Carr URL.

    See Also
    --------
    sync_api.get_products_from_url
    """
    cached = get_cached(url)
    if cached and not refresh:
        data = cached
    else:
        data = await run_in_loop_async(get_product_api_response(url))
        set_cached(url, data)

    return get_products_table(data)


async def get_products_from_urls(
    urls: list[str], refresh: bool = False
) -> list[DataFrame]:
    """Gets product tables from a list of McMaster-Carr URLs.

    See Also
    --------
    sync_api.get_products_from_urls
    """
    tasks = [create_task(get_products_from_url(url, refresh)) for url in urls]
    return await gather(*tasks)
