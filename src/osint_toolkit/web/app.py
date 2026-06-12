"""FastAPI 应用 / FastAPI application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from osint_toolkit.web.routes import api, pages

_STATIC = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="OSINT Toolkit Web", version="0.1.0")
    app.include_router(pages.router)
    app.include_router(api.router)
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
    return app
