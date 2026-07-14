"""Site adapter registry — MakerWorld can_handle + lookup (scaffold)."""

from __future__ import annotations

from backend.services.sites import (
    MakerWorldAdapter,
    get_adapter,
    get_adapter_for_url,
    registered_adapters,
)


def test_makerworld_can_handle_makerworld_urls():
    adapter = MakerWorldAdapter()
    assert adapter.can_handle("https://makerworld.com/en/models/12345")
    assert adapter.can_handle("https://www.makerworld.com/en/models/12345?foo=1")
    assert not adapter.can_handle("https://printables.com/model/1")
    assert not adapter.can_handle("https://www.thingiverse.com/thing:1")


def test_registry_returns_makerworld_for_known_urls():
    adapters = registered_adapters()
    assert any(a.site_id == "makerworld" for a in adapters)
    assert get_adapter("makerworld") is not None
    assert isinstance(get_adapter("makerworld"), MakerWorldAdapter)

    found = get_adapter_for_url("https://makerworld.com/en/models/999")
    assert found is not None
    assert found.site_id == "makerworld"


def test_registry_returns_none_for_other_hosts():
    assert get_adapter_for_url("https://printables.com/model/1") is None
    assert get_adapter_for_url("https://www.thingiverse.com/thing:42") is None
    assert get_adapter_for_url("https://example.com/project/1") is None
    assert get_adapter_for_url("https://github.com/org/repo") is None
