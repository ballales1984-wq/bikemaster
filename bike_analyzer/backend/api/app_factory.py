"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from ..config import CORS_ORIGINS, ENVIRONMENT
from ..rate_limiter import limiter
from ..redis_client import close_redis, get_redis
from ..task_queue import get_task_queue
from .routes import admin_router, router

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


def _forwarded_value(header_value: str | None) -> str:
    if not header_value:
        return ""
    return header_value.split(",", 1)[0].strip()


def _static_file_response(file_path: Path, media_type: str | None = None) -> Response:
    if file_path.exists():
        content = (
            file_path.read_bytes()
            if media_type.startswith("image/")
            else file_path.read_text(encoding="utf-8")
        )
        return Response(content=content, media_type=media_type)
    return Response(status_code=404)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from ..db.database import init_db

    init_db()
    await get_redis()
    task_queue = get_task_queue()
    await task_queue.start()
    app.state.task_queue = task_queue
    yield
    await task_queue.stop()
    await close_redis()


def create_app() -> FastAPI:
    # Initialize Sentry if DSN provided
    sentry_dsn = None
    try:
        from ..settings import get_settings
        settings = get_settings()
        sentry_dsn = settings.sentry_dsn
        if sentry_dsn:
            import sentry_sdk
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=settings.sentry_traces_sample_rate,
                environment=settings.environment,
            )
            logger.info("Sentry initialized with DSN")
    except Exception as e:
        logger.warning(f"Sentry not initialized: {e}")

    app = FastAPI(
        title="BikeMaster API",
        description="GPS-based cycling intelligence",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if ENVIRONMENT.lower() in ("production", "prod"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data: https:; "
                "script-src 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net https://code.jquery.com "
                "https://cdnjs.cloudflare.com https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net https://netdna.bootstrapcdn.com "
                "https://cdnjs.cloudflare.com https://unpkg.com; "
                "connect-src 'self'"
            )
        return response

    cors_origins = (
        [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
        if isinstance(CORS_ORIGINS, str)
        else CORS_ORIGINS
    )
    if "*" in cors_origins:
        if ENVIRONMENT.lower() in ("production", "prod", "staging"):
            logger.error(
                "CORS wildcard origin detected in production — forbidding. "
                "Set CORS_ORIGINS to explicit allowed origins."
            )
            cors_origins = []
        else:
            logger.warning("Wildcard CORS origin detected - this is dangerous in production")
    if not cors_origins and ENVIRONMENT.lower() not in ("development", "dev", "test"):
        logger.error("No CORS origins configured in non-development environment")
        cors_origins = []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )
    app.include_router(router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])

    if STATIC_DIR.exists() and INDEX_FILE.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")

        @app.head("/")
        async def dashboard_root_head():
            return Response(status_code=200)

        @app.get("/")
        async def dashboard_root():
            return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))

        @app.get("/index.html")
        async def dashboard_index():
            return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))

        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            return INDEX_FILE.read_text(encoding="utf-8")

        @app.get("/registerSW.js")
        async def register_sw():
            return _static_file_response(STATIC_DIR / "registerSW.js", "text/javascript")

        @app.get("/manifest.json")
        async def manifest():
            return _static_file_response(STATIC_DIR / "manifest.json", "application/json")

        @app.get("/manifest.webmanifest")
        async def manifest_webmanifest():
            return _static_file_response(STATIC_DIR / "manifest.webmanifest", "application/manifest+json")

        CEO_FILE = STATIC_DIR / "ceo_dashboard.html"
        if CEO_FILE.exists():

            @app.get("/ceo", response_class=HTMLResponse)
            async def ceo_dashboard():
                return CEO_FILE.read_text(encoding="utf-8")

        @app.get("/sw.js")
        async def service_worker():
            return _static_file_response(STATIC_DIR / "sw.js", "application/javascript")

        @app.get("/pwa-192x192.png")
        async def pwa_icon_192():
            return _static_file_response(STATIC_DIR / "pwa-192x192.png", "image/png")

        @app.get("/pwa-512x512.png")
        async def pwa_icon_512():
            return _static_file_response(STATIC_DIR / "pwa-512x512.png", "image/png")

        @app.get("/favicon.svg")
        async def favicon_svg():
            return _static_file_response(STATIC_DIR / "favicon.svg", "image/svg+xml")

        @app.get("/apple-touch-icon.png")
        async def apple_touch_icon():
            icon = STATIC_DIR / "apple-touch-icon.png"
            if not icon.exists():
                icon = STATIC_DIR / "pwa-192x192.png"
            return _static_file_response(icon, "image/png")

        @app.get("/favicon.ico")
        async def favicon():
            return Response(
                content='<svg xmlns="http://www.w3.org/2000/svg" '
                        'viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#4ecca3"/>'
                        '<text x="50" y="55" font-size="40" text-anchor="middle">🚴</text></svg>',
                media_type="image/svg+xml",
            )

    return app