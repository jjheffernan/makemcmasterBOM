"""Site adapter registry — MakerWorld today; other hosts stubbed for later."""

from __future__ import annotations

from backend.services.sites.base import SiteAdapter
from backend.services.sites.makerworld import MakerWorldAdapter

_ADAPTERS: list[SiteAdapter] = []


def register(adapter: SiteAdapter) -> None:
    """Append an adapter. Idempotent on ``site_id`` (replace existing)."""
    global _ADAPTERS
    _ADAPTERS = [a for a in _ADAPTERS if a.site_id != adapter.site_id]
    _ADAPTERS.append(adapter)


def registered_adapters() -> tuple[SiteAdapter, ...]:
    return tuple(_ADAPTERS)


def get_adapter(site_id: str) -> SiteAdapter | None:
    for adapter in _ADAPTERS:
        if adapter.site_id == site_id:
            return adapter
    return None


def get_adapter_for_url(url: str) -> SiteAdapter | None:
    """Return the first registered adapter whose ``can_handle`` matches ``url``."""
    for adapter in _ADAPTERS:
        if adapter.can_handle(url):
            return adapter
    return None


def _bootstrap() -> None:
    register(MakerWorldAdapter())
    # Future: printables
    # register(PrintablesAdapter())
    # Future: thingiverse
    # register(ThingiverseAdapter())


_bootstrap()
