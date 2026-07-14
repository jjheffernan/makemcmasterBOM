"""McMaster-Carr URL helpers — product, category, and filtered browse paths."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import quote_plus, urlparse

from backend.services.mcmaster_handler import _is_excluded_route

MCMASTER_SITE_BASE = "https://www.mcmaster.com"
MCMASTER_API_BASE = "https://api.mcmaster.com/v1"

_PART_NUMBER_IN_URL = re.compile(
    r"mcmaster\.com/(?:products/)?([0-9]{4,5}[A-Z][0-9]{2,3})(?:/|$|\?)",
    re.I,
)


def mcmaster_product_url(part_number: str, search_query: str = "") -> str:
    """Product detail URL with optional search context."""
    pn = part_number.strip()
    if not pn:
        return ""
    query = search_query.strip()
    if query:
        return f"{MCMASTER_SITE_BASE}/{pn}/?searchQuery={quote_plus(query)}"
    return f"{MCMASTER_SITE_BASE}/{pn}"


def category_search_url(route: str, query: str) -> str:
    """Category-scoped search (`?searchQuery=` only)."""
    if not query.strip() or _is_excluded_route(route):
        return ""
    encoded = quote_plus(query.strip())
    path = route if route.startswith("/") else f"/{route}"
    if not path.endswith("/"):
        path = f"{path}/"
    return f"{MCMASTER_SITE_BASE}{path}?searchQuery={encoded}"


def filtered_browse_url(
    browse_root: str,
    filter_path: str,
    *,
    search_query: str = "",
) -> str:
    """
    Filtered category browse URL.

  Example root + filters:
    /products/screws/socket-head-screws-2~/steel-socket-head-screws~~/
    system-of-measurement~metric/thread-size~m3/length~16-mm/
    """
    root = browse_root.strip()
    if not root.startswith("/"):
        root = f"/{root}"
    if not root.endswith("/"):
        root = f"{root}/"

    filters = filter_path.strip().strip("/")
    if filters and not filters.endswith("/"):
        filters = f"{filters}/"

    url = f"{MCMASTER_SITE_BASE}{root}{filters}"
    if search_query.strip():
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}searchQuery={quote_plus(search_query.strip())}"
    return url


def part_number_from_url(url: str) -> str | None:
    match = _PART_NUMBER_IN_URL.search(url)
    return match.group(1).upper() if match else None


def _hostname_allowed_for_domain(url: str, base_domain: str) -> bool:
    """True when URL is http(s) with host exactly base_domain or a subdomain thereof.

    Rejects private / link-local / loopback IP literals.
    """
    if not url or not str(url).strip():
        return False
    parsed = urlparse(str(url).strip())
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
        # Public IP literals are never valid vendor hostnames.
        return False
    return host == base_domain or host.endswith(f".{base_domain}")


def is_mcmaster_url(url: str) -> bool:
    return _hostname_allowed_for_domain(url, "mcmaster.com")
