"""Strict hostname URL validation (SSRF guards)."""

from __future__ import annotations

import pytest

from backend.services.scraper import normalize_makerworld_url
from backend.services.vendors.mcmaster.urls import is_mcmaster_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.mcmaster.com/91290A110",
        "https://mcmaster.com/91290A110",
        "http://api.mcmaster.com/v1/parts",
        "https://www.mcmaster.com/products/screws/",
        "https://WWW.MCMASTER.COM/91290A110",
    ],
)
def test_is_mcmaster_url_allows_vendor_hosts(url: str) -> None:
    assert is_mcmaster_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "ftp://www.mcmaster.com/x",
        "javascript:alert(1)",
        "https://evil.com/mcmaster.com",
        "https://mcmaster.com.evil.com/x",
        "https://notmcmaster.com/x",
        "https://evil.com/?u=mcmaster.com",
        "https://user@evil.com/mcmaster.com",
        "http://127.0.0.1/mcmaster.com",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://192.168.1.1/",
        "http://10.0.0.5/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[fe80::1]/",
        "https://8.8.8.8/",
    ],
)
def test_is_mcmaster_url_denies_untrusted(url: str) -> None:
    assert is_mcmaster_url(url) is False


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://makerworld.com/en/models/123?profileId=9",
            "https://makerworld.com/en/models/123",
        ),
        (
            "https://www.makerworld.com/en/models/123/",
            "https://www.makerworld.com/en/models/123",
        ),
        (
            "http://cdn.makerworld.com/file.zip",
            "http://cdn.makerworld.com/file.zip",
        ),
    ],
)
def test_normalize_makerworld_url_allows(url: str, expected: str) -> None:
    assert normalize_makerworld_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/makerworld.com",
        "https://makerworld.com.evil.com/x",
        "ftp://makerworld.com/en/models/1",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://192.168.0.1/",
        "http://169.254.169.254/",
        "https://8.8.8.8/",
        "javascript:alert(1)",
    ],
)
def test_normalize_makerworld_url_denies(url: str) -> None:
    with pytest.raises(ValueError, match="makerworld.com"):
        normalize_makerworld_url(url)
