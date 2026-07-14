"""BOM export pack: CSV (default), TSV, and XLSX."""

from __future__ import annotations

import io

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import store
from backend.main import app
from backend.models.part import Part
from backend.models.project import Project
from backend.services.pipeline import parts_to_csv, parts_to_tsv, parts_to_xlsx


def _sample_parts() -> list[Part]:
    return [
        Part(original_name="M3 bolt", quantity=4, specification="Stainless"),
        Part(
            original_name="PLA printed spacer",
            quantity=1,
            mcmaster_status="not_applicable",
        ),
    ]


def test_parts_to_csv_and_tsv_roundtrip_columns():
    parts = _sample_parts()
    csv_text = parts_to_csv(parts)
    tsv_text = parts_to_tsv(parts)

    assert "M3 bolt" in csv_text
    assert "PLA printed spacer" in csv_text
    assert "," in csv_text.splitlines()[0]

    assert "M3 bolt" in tsv_text
    assert "\t" in tsv_text
    assert tsv_text.count("\n") >= 3

    csv_df = pd.read_csv(io.StringIO(csv_text))
    tsv_df = pd.read_csv(io.StringIO(tsv_text), sep="\t")
    assert list(csv_df.columns) == list(tsv_df.columns)
    assert list(csv_df["original_name"]) == list(tsv_df["original_name"])


def test_parts_to_xlsx_readable():
    raw = parts_to_xlsx(_sample_parts())
    assert raw[:2] == b"PK"  # zip/xlsx magic
    df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
    assert "M3 bolt" in set(df["original_name"])
    assert "PLA printed spacer" in set(df["original_name"])


@pytest.mark.asyncio
async def test_export_endpoint_formats():
    project = Project(title="Test BOM", parts=_sample_parts())
    project_id = store.save(project)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        csv_res = await client.get(f"/api/bom/{project_id}/export")
        tsv_res = await client.get(f"/api/bom/{project_id}/export?format=tsv")
        xlsx_res = await client.get(f"/api/bom/{project_id}/export?format=xlsx")
        bad_res = await client.get(f"/api/bom/{project_id}/export?format=pdf")

    assert csv_res.status_code == 200
    assert csv_res.headers["content-type"].startswith("text/csv")
    assert "Test_BOM.csv" in csv_res.headers["content-disposition"]
    assert b"M3 bolt" in csv_res.content

    assert tsv_res.status_code == 200
    assert "tab-separated-values" in tsv_res.headers["content-type"]
    assert "Test_BOM.tsv" in tsv_res.headers["content-disposition"]
    assert b"\t" in tsv_res.content

    assert xlsx_res.status_code == 200
    assert "spreadsheetml" in xlsx_res.headers["content-type"]
    assert "Test_BOM.xlsx" in xlsx_res.headers["content-disposition"]
    assert xlsx_res.content[:2] == b"PK"

    assert bad_res.status_code == 422


@pytest.mark.asyncio
async def test_export_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/bom/does-not-exist/export?format=csv")
    assert response.status_code == 404
