from __future__ import annotations

import os
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.debug_log import configure_logging
from backend.routers import bom_router, debug_router, feedback_router, import_router, notebooks_router

configure_logging()

app = FastAPI(
    title="MakerWorld BOM → McMaster-Carr",
    description="Import MakerWorld projects and generate McMaster-Carr hardware links.",
    version="0.1.0",
)

allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router.router, prefix="/api")
app.include_router(bom_router.router, prefix="/api")
app.include_router(feedback_router.router, prefix="/api")
app.include_router(notebooks_router.router, prefix="/api")
app.include_router(debug_router.router, prefix="/api")


@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if config.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "traceback": traceback.format_exc(),
                "path": str(request.url.path),
            },
        )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "debug": config.DEBUG,
        "rate_limit": {
            "enabled": config.RATE_LIMIT_ENABLED,
            "import_per_minute": config.RATE_LIMIT_IMPORT_PER_MINUTE,
            "outbound_min_interval_sec": config.RATE_LIMIT_OUTBOUND_MIN_INTERVAL,
            "max_concurrent_scrapes": config.RATE_LIMIT_MAX_CONCURRENT_SCRAPES,
        },
    }


# Serve built frontend in production
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
