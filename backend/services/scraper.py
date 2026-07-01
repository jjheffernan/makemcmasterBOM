"""MakerWorld page scraper — prototype in notebooks/01_scrape.ipynb before changing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from backend import config
from backend.debug_log import record
from backend.models.part import Part
from backend.models.progress import ProgressCallback, StageEvent
from backend.services.http_client import format_fetch_error, outbound_client, unwrap_exception
from backend.services.description_bom import (
    merge_parts,
    parts_from_description,
    resolve_description_text,
)
from backend.rate_limit import outbound_request
from backend.services.page_fetch import fetch_makerworld_html

MAKERWORLD_BASE = "https://makerworld.com"

from backend.services.makerworld_bom import (
    best_attachment,
    extract_design,
    extract_next_data,
    find_attachment_urls,
    parts_from_design,
)

BomSource = Literal["file", "embedded", "description", "none"]


def _is_retryable_http_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.ProxyError):
        return False
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError))


@dataclass
class ScrapeResult:
    title: str
    description: str
    makerworld_url: str
    thumbnail_url: str
    bom_bytes: bytes | None
    bom_filename: str | None
    bom_content_type: str | None
    embedded_parts: list[Part] = field(default_factory=list)
    description_parts: list[Part] = field(default_factory=list)
    bom_source: BomSource = "none"
    warnings: list[str] = field(default_factory=list)


def normalize_makerworld_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if "makerworld.com" not in parsed.netloc:
        raise ValueError("URL must be a makerworld.com project link")
    return url.split("?")[0].rstrip("/")


@retry(
    retry=retry_if_exception(_is_retryable_http_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def fetch_page(url: str) -> str:
    html, method = await fetch_makerworld_html(url)
    record("scrape", f"Page fetched via {method}", data={"url": url, "bytes": len(html)})
    return html


def _extract_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return str(og["content"]).strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return ""


def _extract_description(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return str(og["content"]).strip()
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return str(meta["content"]).strip()
    return ""


def _extract_thumbnail(soup: BeautifulSoup, page_url: str) -> str:
    """Project cover image from Open Graph / Twitter meta tags."""
    candidates: list[str] = []

    for prop in ("og:image", "og:image:url", "twitter:image"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            candidates.append(str(tag["content"]).strip())

    link = soup.find("link", rel=re.compile(r"image_src", re.I))
    if link and link.get("href"):
        candidates.append(str(link["href"]).strip())

    for img in soup.find_all("img", src=True):
        src = str(img["src"])
        alt = (img.get("alt") or "").lower()
        cls = " ".join(img.get("class") or []).lower()
        if any(k in f"{src} {alt} {cls}" for k in ("cover", "thumbnail", "preview")):
            candidates.append(src.strip())

    for raw in candidates:
        if not raw:
            continue
        absolute = urljoin(page_url, raw)
        if absolute.startswith(("http://", "https://")):
            return absolute

    return ""


def _find_bom_link(soup: BeautifulSoup, page_url: str) -> tuple[str | None, str | None]:
    """Locate a BOM attachment link (CSV/XLSX) in page anchors."""
    bom_pattern = re.compile(r"bom|bill\s*of\s*materials", re.I)
    file_pattern = re.compile(r"\.(csv|xlsx|xls)$", re.I)

    candidates: list[tuple[str, str]] = []

    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        text = anchor.get_text(" ", strip=True)
        label = f"{text} {href}"
        if bom_pattern.search(label) or file_pattern.search(href):
            absolute = urljoin(page_url, href)
            filename = href.split("/")[-1] or "bom.csv"
            candidates.append((absolute, filename))

    return best_attachment(candidates) or (None, None)


@retry(
    retry=retry_if_exception(_is_retryable_http_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def download_bom(url: str) -> tuple[bytes, str, str | None]:
    async with outbound_request():
        async with outbound_client(follow_redirects=True, timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type")
            filename = url.split("/")[-1].split("?")[0] or "bom.csv"
            return response.content, filename, content_type


async def scrape_project(
    url: str,
    *,
    on_progress: ProgressCallback | None = None,
    skip_validate: bool = False,
) -> ScrapeResult:
    if not skip_validate:
        normalized = normalize_makerworld_url(url)
    else:
        normalized = url

    warnings: list[str] = []

    try:
        html = await fetch_page(normalized)
    except Exception as exc:
        record(
            "scrape",
            "Page fetch failed",
            data={"url": normalized, "error": str(unwrap_exception(exc))},
        )
        raise RuntimeError(format_fetch_error(exc)) from exc

    soup = BeautifulSoup(html, "lxml")
    next_data = extract_next_data(html)
    design = extract_design(next_data) if next_data else None

    title = _extract_title(soup)
    og_description = _extract_description(soup)
    thumbnail_url = _extract_thumbnail(soup, normalized)

    raw_description_html = og_description
    if design:
        design_title = str(design.get("title") or "").strip()
        if design_title:
            title = design_title
        for key in ("summary", "description", "detail", "content"):
            value = design.get(key)
            if isinstance(value, str) and value.strip():
                if len(value) > len(raw_description_html):
                    raw_description_html = value.strip()
        design_summary = str(design.get("summary") or "").strip()
        if design_summary and len(design_summary) > len(raw_description_html):
            raw_description_html = design_summary

    description = resolve_description_text(og_description, design)
    description_parts = parts_from_description(raw_description_html)

    scrape_debug = (
        {
            "url": normalized,
            "html_bytes": len(html),
            "title": title,
            "thumbnail_url": thumbnail_url,
            "has_next_data": design is not None,
        }
        if config.DEBUG
        else None
    )
    record("scrape", "Page downloaded", data=scrape_debug or {"url": normalized})

    if on_progress:
        on_progress(
            StageEvent(
                stage="scrape",
                status="done",
                message=title or "Project page downloaded",
                thumbnail_url=thumbnail_url or None,
                debug=scrape_debug,
            )
        )

    embedded_parts: list[Part] = []
    bom_url: str | None = None
    bom_filename: str | None = None

    if on_progress:
        on_progress(
            StageEvent(
                stage="extract_bom",
                status="running",
                message="Looking for BOM attachment…",
            )
        )

    if design:
        embedded_parts = parts_from_design(design)
        json_attachments = find_attachment_urls(design, normalized)
        attachment = best_attachment(json_attachments)
        if attachment:
            bom_url, bom_filename = attachment
        record(
            "extract_bom",
            "Embedded BOM parsed",
            data={
                "embedded_parts": len(embedded_parts),
                "json_attachments": len(json_attachments),
            },
        )

    if not bom_url:
        bom_url, bom_filename = _find_bom_link(soup, normalized)

    record(
        "extract_bom",
        "BOM link search",
        data={
            "bom_url": bom_url,
            "bom_filename": bom_filename,
            "embedded_parts": len(embedded_parts),
            "anchor_count": len(soup.find_all("a", href=True)),
        },
    )

    bom_bytes: bytes | None = None
    bom_content_type: str | None = None
    bom_source: BomSource = "none"

    if bom_url and bom_filename:
        if on_progress:
            on_progress(
                StageEvent(
                    stage="extract_bom",
                    status="running",
                    message=f"Downloading {bom_filename}…",
                )
            )
        try:
            bom_bytes, bom_filename, bom_content_type = await download_bom(bom_url)
            bom_source = "file"
        except Exception as exc:
            record("extract_bom", "BOM download failed", data={"url": bom_url})
            warnings.append(f"Could not download BOM file ({bom_filename}): {exc}")
            bom_bytes = None
        else:
            bom_debug = (
                {
                    "bom_url": bom_url,
                    "filename": bom_filename,
                    "bytes": len(bom_bytes),
                    "content_type": bom_content_type,
                }
                if config.DEBUG
                else None
            )
            record("extract_bom", "BOM downloaded", data=bom_debug or {"filename": bom_filename})
            if on_progress:
                on_progress(
                    StageEvent(
                        stage="extract_bom",
                        status="done",
                        message=f"Downloaded {bom_filename}",
                        debug=bom_debug,
                    )
                )
    elif embedded_parts:
        bom_source = "embedded"
        if on_progress:
            on_progress(
                StageEvent(
                    stage="extract_bom",
                    status="done",
                    message=f"Found {len(embedded_parts)} parts in MakerWorld BOM",
                    debug={"embedded_parts": len(embedded_parts)} if config.DEBUG else None,
                )
            )
    elif description_parts:
        bom_source = "description"
        record(
            "extract_bom",
            "Description BOM parsed",
            data={"description_parts": len(description_parts)},
        )
        if on_progress:
            on_progress(
                StageEvent(
                    stage="extract_bom",
                    status="done",
                    message=(
                        f"Found {len(description_parts)} parts in project description"
                    ),
                    debug={"description_parts": len(description_parts)}
                    if config.DEBUG
                    else None,
                )
            )
    else:
        warnings.append(
            "No bill of materials found on this project. "
            "Upload a BOM file manually or pick a model with Maker's Supply / BOM enabled."
        )
        if on_progress:
            on_progress(
                StageEvent(
                    stage="extract_bom",
                    status="done",
                    message="No BOM found on this project",
                )
            )

    if description_parts:
        embedded_parts = merge_parts(embedded_parts, description_parts)

    return ScrapeResult(
        title=title,
        description=description,
        makerworld_url=normalized,
        thumbnail_url=thumbnail_url,
        bom_bytes=bom_bytes,
        bom_filename=bom_filename,
        bom_content_type=bom_content_type,
        embedded_parts=embedded_parts,
        description_parts=description_parts,
        bom_source=bom_source,
        warnings=warnings,
    )
