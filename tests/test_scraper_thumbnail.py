from bs4 import BeautifulSoup

from backend.services.scraper import _extract_thumbnail


def test_extract_thumbnail_og_image():
    html = """
    <html><head>
      <meta property="og:image" content="https://cdn.makerworld.com/cover.jpg" />
    </head></html>
    """
    soup = BeautifulSoup(html, "lxml")
    url = _extract_thumbnail(soup, "https://makerworld.com/en/models/123")
    assert url == "https://cdn.makerworld.com/cover.jpg"


def test_extract_thumbnail_relative_url():
    html = '<meta property="og:image" content="/images/model.png" />'
    soup = BeautifulSoup(html, "lxml")
    url = _extract_thumbnail(soup, "https://makerworld.com/en/models/123")
    assert url == "https://makerworld.com/images/model.png"


def test_extract_thumbnail_missing():
    soup = BeautifulSoup("<html></html>", "lxml")
    assert _extract_thumbnail(soup, "https://makerworld.com/en/models/123") == ""
