from __future__ import annotations

import asyncio
import json
import traceback
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend import config
from backend.api.store import save
from backend.debug_log import record
from backend.models.project import Project
from backend.models.progress import PIPELINE_STAGES, StageEvent
from backend.rate_limit import check_import_rate_limit
from backend.services.http_client import format_fetch_error
from backend.services.parsers.upload import ALLOWED_UPLOAD_EXTENSIONS, SUPPORTED_FORMAT_LABELS
from backend.services.pipeline import import_from_file, import_from_url

REPO_ROOT = Path(__file__).resolve().parents[2]
REGRESSION_URLS_PATH = REPO_ROOT / "data" / "regression_urls.json"

router = APIRouter(prefix="/import", tags=["import"])


def _upload_too_large_detail(max_bytes: int) -> str:
    return f"Upload exceeds maximum size of {max_bytes} bytes"


def _reject_if_content_length_too_large(request: Request, max_bytes: int) -> None:
    """Reject early when Content-Length is present and exceeds the upload cap."""
    raw = request.headers.get("content-length")
    if raw is None:
        return
    try:
        length = int(raw)
    except ValueError:
        return
    if length > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=_upload_too_large_detail(max_bytes),
        )


async def _read_upload_bytes(request: Request, file: UploadFile) -> bytes:
    """Read upload bytes with Content-Length + post-read size guards (HTTP 413)."""
    max_bytes = config.MAX_UPLOAD_BYTES
    _reject_if_content_length_too_large(request, max_bytes)
    # Cap the read so chunked / missing Content-Length cannot force unbounded memory use.
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=_upload_too_large_detail(max_bytes),
        )
    return content


class ImportRequest(BaseModel):
    url: str = Field(..., description="MakerWorld project URL")


class ImportResponse(BaseModel):
    project_id: str
    project: Project


class MakerWorldExample(BaseModel):
    url: str
    label: str


class ImportSourcesResponse(BaseModel):
    sources: list[dict[str, str]]
    makerworld_examples: list[MakerWorldExample]
    upload_formats: list[str]
    upload_extensions: list[str]


def _unwrap_error(exc: BaseException) -> str:
    from backend.services.http_client import unwrap_exception

    exc = unwrap_exception(exc)
    if isinstance(exc, RuntimeError):
        return str(exc)
    return format_fetch_error(exc)


async def _sse_import(
    runner: Callable[[Callable[[StageEvent], None]], Awaitable[Project]],
) -> StreamingResponse:
    queue: asyncio.Queue[StageEvent | dict] = asyncio.Queue()

    def on_progress(event: StageEvent) -> None:
        queue.put_nowait(event)

    async def run_import() -> None:
        try:
            record("import", "Starting import stream")
            project = await runner(on_progress)
            project_id = save(project)
            record(
                "import",
                "Import complete",
                data={"project_id": project_id, "parts": len(project.parts)},
            )
            await queue.put(
                {
                    "type": "complete",
                    "project_id": project_id,
                    "project": project.model_dump(),
                }
            )
        except ValueError as exc:
            record("import", "Validation error", data={"error": str(exc)})
            payload: dict = {"type": "error", "detail": str(exc), "status": 400}
            if config.DEBUG:
                payload["traceback"] = traceback.format_exc()
            await queue.put(payload)
        except Exception as exc:
            detail = _unwrap_error(exc)
            record("import", "Import failed", data={"error": detail})
            payload = {"type": "error", "detail": detail, "status": 502}
            if config.DEBUG:
                payload["traceback"] = traceback.format_exc()
            await queue.put(payload)

    async def event_stream():
        task = asyncio.create_task(run_import())
        try:
            while True:
                item = await queue.get()
                if isinstance(item, StageEvent):
                    yield f"data: {json.dumps({'type': 'stage', **item.model_dump()})}\n\n"
                elif item.get("type") == "complete":
                    yield f"data: {json.dumps(item)}\n\n"
                    break
                elif item.get("type") == "error":
                    yield f"data: {json.dumps(item)}\n\n"
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stages")
async def list_import_stages() -> dict:
    return {"stages": PIPELINE_STAGES}


@router.get("/sources", response_model=ImportSourcesResponse)
async def list_import_sources() -> ImportSourcesResponse:
    """Import UI metadata — source types, example MakerWorld URLs, upload formats."""
    examples: list[MakerWorldExample] = []
    if REGRESSION_URLS_PATH.is_file():
        raw = json.loads(REGRESSION_URLS_PATH.read_text(encoding="utf-8"))
        for item in raw.get("urls", []):
            if item.get("ui_example", item.get("expect_bom")):
                examples.append(
                    MakerWorldExample(
                        url=item["url"],
                        label=item.get("label", item["url"]),
                    )
                )

    return ImportSourcesResponse(
        sources=[
            {
                "id": "makerworld",
                "label": "MakerWorld project",
                "description": "Scrape embedded BOM, attachments, and description hardware lists",
            },
        ],
        makerworld_examples=examples,
        upload_formats=list(SUPPORTED_FORMAT_LABELS),
        upload_extensions=sorted(ALLOWED_UPLOAD_EXTENSIONS),
    )


@router.post("", response_model=ImportResponse, dependencies=[Depends(check_import_rate_limit)])
async def import_project(body: ImportRequest) -> ImportResponse:
    try:
        project = await import_from_url(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=_unwrap_error(exc),
        ) from exc

    project_id = save(project)
    return ImportResponse(project_id=project_id, project=project)


@router.post("/stream", dependencies=[Depends(check_import_rate_limit)])
async def import_project_stream(body: ImportRequest) -> StreamingResponse:
    return await _sse_import(
        lambda on_progress: import_from_url(body.url, on_progress=on_progress)
    )


@router.post("/file", response_model=ImportResponse, dependencies=[Depends(check_import_rate_limit)])
async def import_bom_file(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
) -> ImportResponse:
    content = await _read_upload_bytes(request, file)
    filename = file.filename or "bom.csv"
    try:
        project = await import_from_file(content, filename, title=title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=_unwrap_error(exc),
        ) from exc

    project_id = save(project)
    return ImportResponse(project_id=project_id, project=project)


@router.post("/file/stream", dependencies=[Depends(check_import_rate_limit)])
async def import_bom_file_stream(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
) -> StreamingResponse:
    content = await _read_upload_bytes(request, file)
    filename = file.filename or "bom.csv"

    async def runner(on_progress: Callable[[StageEvent], None]) -> Project:
        return await import_from_file(
            content, filename, title=title, on_progress=on_progress
        )

    return await _sse_import(runner)
