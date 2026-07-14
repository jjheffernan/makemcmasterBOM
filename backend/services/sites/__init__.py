"""Multi-site BOM ingestion adapters (scaffold — MakerWorld only for now)."""

from backend.services.sites.base import SiteAdapter
from backend.services.sites.makerworld import MakerWorldAdapter
from backend.services.sites.registry import (
    get_adapter,
    get_adapter_for_url,
    register,
    registered_adapters,
)

__all__ = [
    "MakerWorldAdapter",
    "SiteAdapter",
    "get_adapter",
    "get_adapter_for_url",
    "register",
    "registered_adapters",
]
