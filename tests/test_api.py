import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_import_stages():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/import/stages")
    assert response.status_code == 200
    body = response.json()
    assert len(body["stages"]) == 6
    assert body["stages"][0]["id"] == "validate"


@pytest.mark.asyncio
async def test_import_bom_file():
    transport = ASGITransport(app=app)
    csv_content = b"Qty,Part Name,Specification\n2,M3 bolt,Stainless\n"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/import/file",
            files={"file": ("bom.csv", csv_content, "text/csv")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"]
    assert len(body["project"]["parts"]) == 1


@pytest.mark.asyncio
async def test_list_notebooks():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/notebooks")
    assert response.status_code == 200
    body = response.json()
    assert "notebooks" in body
    assert "jupyter_url" in body
    filenames = {nb["filename"] for nb in body["notebooks"]}
    assert "mcmaster_browse.ipynb" in filenames
    assert "vendor/01_mcmaster_scraper.ipynb" not in filenames


@pytest.mark.asyncio
async def test_import_sources():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/import/sources")
    assert response.status_code == 200
    body = response.json()
    assert body["sources"][0]["id"] == "makerworld"
    example_urls = [e["url"] for e in body["makerworld_examples"]]
    assert len(example_urls) >= 1
    assert not any("574923" in url for url in example_urls)
    assert not any("600987" in url for url in example_urls)
    assert any("972938" in url for url in example_urls)
    assert ".json" in body["upload_extensions"]
    assert "Markdown" in body["upload_formats"]
