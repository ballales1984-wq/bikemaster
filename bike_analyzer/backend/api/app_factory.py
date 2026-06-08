"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .routes import router, admin_router
from ..config import CORS_ORIGINS

STATIC_DIR = Path(__file__).parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"

limiter = Limiter(key_func=get_remote_address)
DEFAULT_LIMIT = "100/hour"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from ..db.database import init_db
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="BikeMaster API", description="GPS-based cycling intelligence", version="0.1.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])

    if STATIC_DIR.exists() and INDEX_FILE.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")

        @app.get("/")
        async def dashboard_root():
            return RedirectResponse(url="/static/index.html")

        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            return INDEX_FILE.read_text(encoding="utf-8")

        @app.get("/manifest.json")
        async def manifest():
            mf = STATIC_DIR / "manifest.json"
            if mf.exists():
                return Response(content=mf.read_text(encoding="utf-8"), media_type="application/json")
            return Response(status_code=404)

        CEO_FILE = STATIC_DIR / "ceo_dashboard.html"
        if CEO_FILE.exists():
            @app.get("/ceo", response_class=HTMLResponse)
            async def ceo_dashboard():
                return CEO_FILE.read_text(encoding="utf-8")

    @app.get("/favicon.ico")
    async def favicon():
        return Response(
            content='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#4ecca3"/><text x="50" y="55" font-size="40" text-anchor="middle">🚴</text></svg>',
            media_type="image/svg+xml",
        )

    return app
