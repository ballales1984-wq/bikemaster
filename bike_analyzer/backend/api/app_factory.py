"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from pydantic import ValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from ..config import CORS_ORIGINS, ENVIRONMENT, SECRET_KEY
from ..monitoring import MetricsMiddleware
from ..observability import init_observability
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
    from ..monitoring import start_metrics_server

    init_db()
    try:
        from ..settings import get_settings
        settings = get_settings()
        if settings.environment.lower() not in ("test", "testing"):
            start_metrics_server()
    except Exception:
        pass
    await get_redis()
    task_queue = get_task_queue()
    await task_queue.start()
    app.state.task_queue = task_queue
    yield
    await task_queue.stop()
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title="BikeMaster API",
        description="GPS-based cycling intelligence",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Initialize unified observability (Sentry + OpenTelemetry + Zipkin)
    init_observability(app)

    # Conditional Prometheus instrumentation for compatibility
    if ENVIRONMENT.lower() not in ("test", "testing"):
        try:
            instrumentator = Instrumentator(
                should_group_status_codes=True,
                should_ignore_untemplated=True,
                excluded_handlers=["/metrics", "/health"],
            )
            instrumentator.add(metrics.requests())
            instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        except Exception:
            pass
    # Skip OpenTelemetry instrumentation in test environment
    if ENVIRONMENT.lower() in ("test", "testing"):
        pass  # Observability already skipped
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(MetricsMiddleware)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": "Dati non validi", "errors": exc.errors()},
        )

    from bike_analyzer.core.validators import ValidationError as BusinessValidationError

    @app.exception_handler(BusinessValidationError)
    async def business_validation_error_handler(request: Request, exc: BusinessValidationError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.middleware("http")
    async def audit_log_middleware(request: Request, call_next):
        import time
        start = time.time()
        user_id = "anonymous"
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                from ..security import _try_decode
                token = auth_header[7:]
                payload = _try_decode(token, SECRET_KEY)
                if payload:
                    user_id = str(payload.get("sub", "anonymous"))
        except Exception:
            pass
        response = await call_next(request)
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "AUDIT %s %s %s user=%s ip=%s %dms",
            request.method,
            request.url.path,
            response.status_code,
            user_id,
            request.client.host if request.client else "unknown",
            elapsed_ms,
        )
        if user_id != "anonymous":
            sentry_sdk.set_user({"id": user_id})
        return response

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

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        async def spa_fallback(full_path: str):
            if full_path.startswith(("api/", "static/", "assets/")):
                return Response(status_code=404)
            return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))

    return app
