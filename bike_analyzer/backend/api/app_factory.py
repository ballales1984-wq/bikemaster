"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from .routes import router
from ..config import CORS_ORIGINS

STATIC_DIR = Path(__file__).parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from ..db.database import init_db
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="BikeMaster API", description="GPS-based cycling intelligence", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/v1")

    if STATIC_DIR.exists() and INDEX_FILE.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/")
        async def dashboard_root():
            return RedirectResponse(url="/static/index.html")

        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            return INDEX_FILE.read_text(encoding="utf-8")

    @app.get("/favicon.ico")
    async def favicon():
        return Response(
            content='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#4ecca3"/><text x="50" y="55" font-size="40" text-anchor="middle">🚴</text></svg>',
            media_type="image/svg+xml",
        )

    return app
