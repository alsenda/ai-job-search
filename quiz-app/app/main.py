"""FastAPI application factory.

Serves the JSON API under ``/api`` and, when a built frontend exists in
``frontend/dist``, the static app at ``/`` (single deployment, no CORS).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import quiz, results, sets

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create tables on startup (no-op when they already exist)."""
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Interview Quiz", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(sets.router)
    app.include_router(quiz.router)
    app.include_router(results.router)

    if FRONTEND_DIST.is_dir():
        # html=True serves index.html at "/" — mounted last so /api wins.
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app


app = create_app()
