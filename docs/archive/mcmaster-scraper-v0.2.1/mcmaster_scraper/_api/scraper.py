import json
import logging
import re

from .._utils.page_provider import get_page

logger = logging.getLogger(__name__)


async def get_product_api_response(url: str) -> dict:
    if not _is_valid_url(url):
        raise ValueError("Not a McMaster-Carr URL")

    logger.info("Finding API for product page...")

    # Using Playwright because the API can only be discovered by loading the JavaScript
    page = await get_page()
    await page.goto(url, wait_until="commit")

    # If the JSON is too large, the response will be evicted
    # from the inspector cache before we can access it

    # As a workaround, we can navigate to the API URL
    # and extract the response from the page's body

    product_api = "**/ProdPageWebPart.aspx**"
    async with page.expect_request(product_api, timeout=5000) as request:
        api_url = (await request.value).url

    logger.info("Getting API response...")
    await page.goto(api_url)

    res = await page.locator("body").text_content()
    assert res is not None

    data = _extract_json_from_response(res)

    await page.close()
    return data


def _extract_json_from_response(res: str) -> dict:
    start = res.find("{")
    end = res.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON found in API response")

    json_str = res[start : end + 1]
    return json.loads(json_str)


def _is_valid_url(url: str) -> bool:
    pattern = re.compile(r"^https?://(www\.)?mcmaster\.com(/\S*)?$")
    return bool(pattern.match(url))
