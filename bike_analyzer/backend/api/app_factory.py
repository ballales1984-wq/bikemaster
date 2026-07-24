"""FastAPI application factory.

Costruisce l'istanza ASGI di BikeMaster assemblando middleware, router,
servizio di file statici, osservabilita' e gestione del ciclo di vita.

Responsabilita' principali:
- Inizializzazione servizi allo startup (DB, Redis, task queue, event bus).
- Configurazione middleware: CORS, rate limiting, metriche, audit logging,
  correlation ID, security headers.
- Montaggio router principali: API v1, admin, BM2, sync, adaptation.
- Serving della dashboard SPA e risorse statiche (PWA manifest, service
  worker, icone).
- Gestione degli errori con handler personalizzati per ValidationError,
  ValueError e business validation errors.
"""

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

from ..logging_config import REQUEST_ID_HEADER
from ..monitoring import MetricsMiddleware
from ..observability import init_observability
from ..rate_limiter import limiter
from ..redis_client import close_redis, get_redis
from ..settings import get_settings
from ..task_queue import get_task_queue
from .adaptation_routes import router as adaptation_router
from .bm2_routes import bm2_router
from .performance_routes import performance_router
from .routes import admin_router, router
from .sync_routes import router as sync_router
from .utils import _trusted_forwarded_value
from .voice_routes import router as voice_router

logger = logging.getLogger(__name__)

_s = get_settings()
STATIC_DIR = Path(__file__).parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


def _static_file_response(file_path: Path, media_type: str | None = None, headers: dict | None = None) -> Response:
    """Serve a static file from disk, inferring media type when not provided."""
    if file_path.exists() and media_type:
        content = file_path.read_bytes() if media_type.startswith("image/") else file_path.read_text(encoding="utf-8")
        return Response(content=content, media_type=media_type, headers=headers or {})
    if file_path.exists() and media_type is None:
        return Response(content=file_path.read_bytes(), media_type="application/octet-stream", headers=headers or {})
    return Response(status_code=404, headers=headers or {})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo di vita dell'applicazione: startup e shutdown dei servizi.

    Allo startup inizializza:
    - Il database SQLite (schema + migrazioni).
    - Il database PostgreSQL asincrono (se ``DATABASE_URL`` configurato).
    - Il client Redis (opzionale, gli errori non bloccano l'avvio).
    - La task queue per job in background.
    - Il domain event bus (opzionale).

    Allo shutdown termina nell'ordine: event bus, task queue, Redis.
    Ogni passo e' protetto da try/except per garantire che un errore in
    un servizio non impedisca lo shutdown degli altri.
    """
    from ..db.database import init_db
    from ..logging_config import setup_logging

    setup_logging()
    init_db()
    if _s.database_url:
        from ..db.migrations import run_migrations_on_startup

        run_migrations_on_startup()
        from ..db.async_db import init_async_db

        try:
            await init_async_db()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialize async database")

    # Redis (optional): a downed Redis must not prevent startup.
    try:
        await get_redis()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to initialize Redis client")

    # Background task queue worker.
    task_queue = get_task_queue()
    try:
        await task_queue.start()
        app.state.task_queue = task_queue
    except Exception:  # noqa: BLE001
        logger.exception("Failed to start background task queue")

    # Domain event bus (optional but tracked for graceful shutdown).
    try:
        from ..events import start_event_bus

        await start_event_bus()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to start domain event bus")

    yield

    # Graceful shutdown: stop background services, guarding each step so one
    # failure does not block the others.
    logger.info("Shutting down background services")
    try:
        from ..events import stop_event_bus

        await stop_event_bus()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to stop domain event bus")
    try:
        await task_queue.stop()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to stop background task queue")
    try:
        await close_redis()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to close Redis client")


def create_app() -> FastAPI:
    """Crea e configura l'istanza FastAPI dell'applicazione BikeMaster.

    Questa funzione e' il punto di assemblaggio centrale del backend locale.
    Configura:
    - Middleware: CORS, rate limiting, metriche Prometheus, audit logging,
      correlation ID, security headers.
    - Router: API v1, admin, BM2, sync, adaptation.
    - Servizi: osservabilita' (Sentry/OpenTelemetry), task queue, Redis.
    - Static files: dashboard SPA, PWA manifest, service worker, icone.
    - Exception handlers: ValidationError, ValueError, business errors.
    """
    app = FastAPI(
        title="BikeMaster API",
        description="GPS-based cycling intelligence",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
        redoc_url="/redoc" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
        openapi_url="/openapi.json" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
    )

    # Initialize unified observability (Sentry + OpenTelemetry + Zipkin)
    init_observability(app)

    # Conditional Prometheus instrumentation for compatibility
    if _s.environment.lower() not in ("test", "testing"):
        try:
            instrumentator = Instrumentator(
                should_group_status_codes=True,
                should_ignore_untemplated=True,
                excluded_handlers=["/metrics", "/health"],
            )
            instrumentator.add(metrics.requests())
            instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        except Exception:
            logger.debug("Prometheus instrumentation setup failed", exc_info=True)
    # Skip OpenTelemetry instrumentation in test environment
    if _s.environment.lower() in ("test", "testing"):
        pass  # Observability already skipped
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(MetricsMiddleware)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Return localized 422 for Pydantic validation failures."""
        return JSONResponse(
            status_code=422,
            content={"detail": "Dati non validi", "errors": exc.errors()},
        )

    from bike_analyzer.core.validators import ValidationError as BusinessValidationError

    @app.exception_handler(BusinessValidationError)
    async def business_validation_error_handler(request: Request, exc: BusinessValidationError):
        """Return 400 for business-rule validation failures."""
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Return 400 for generic value errors raised in route handlers."""
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    AUDIT_SKIP_PATHS = {
        "/healthz",
        "/health",
        "/metrics",
        "/api/v1/health",
        "/api/v1/health/redis",
        "/api/v1/health/detailed",
    }

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        """Assign a request-scoped correlation id for tracing and logging."""
        import uuid

        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id
        from ..logging_config import set_request_id

        set_request_id(request_id)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled exception for request_id=%s", request_id)
            raise
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    from .user_keys import parse_user_keys_header, set_request_user_keys, reset_request_user_keys  # noqa: I001

    @app.middleware("http")
    async def user_api_keys_middleware(request: Request, call_next):
        """Inject per-request user-provided API keys via ContextVar."""
        keys = parse_user_keys_header(request.headers.get("x-user-api-keys"))
        token = set_request_user_keys(keys)
        try:
            response = await call_next(request)
        finally:
            reset_request_user_keys(token)
        return response

    @app.middleware("http")
    async def audit_log_middleware(request: Request, call_next):
        """Middleware di audit: logga metodo, path, status, utente, IP e durata."""
        import time

        if request.url.path in AUDIT_SKIP_PATHS:
            return await call_next(request)

        start = time.time()
        user_id = "anonymous"
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                from ..security import _try_decode

                token = auth_header[7:]
                payload = _try_decode(token, _s.secret_key)
                if payload:
                    user_id = str(payload.get("sub", "anonymous"))
        except Exception:
            logger.debug("Failed to extract user_id from auth header", exc_info=True)
        response = await call_next(request)
        elapsed_ms = int((time.time() - start) * 1000)
        request_id = getattr(request.state, "request_id", "-")
        # Honor X-Forwarded-For behind a reverse proxy so the audit log records
        # the real client IP instead of the proxy's.
        client_ip = _trusted_forwarded_value(request, "x-forwarded-for") or (
            request.client.host if request.client else "unknown"
        )
        logger.info(
            "AUDIT %s %s %s user=%s ip=%s %dms request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            user_id,
            client_ip,
            elapsed_ms,
            request_id,
            extra={"request_id": request_id},
        )
        if user_id != "anonymous":
            sentry_sdk.set_user({"id": user_id})
        return response

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Middleware di sicurezza: imposta header HTTP e CSP in produzione."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if _s.environment.lower() in ("production", "prod", "staging"):
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data: https:; "
                "script-src 'self' "
                "https://cdn.jsdelivr.net https://code.jquery.com "
                "https://cdnjs.cloudflare.com https://unpkg.com; "
                "style-src 'self' "
                "https://cdn.jsdelivr.net https://netdna.bootstrapcdn.com "
                "https://cdnjs.cloudflare.com https://unpkg.com; "
                "connect-src 'self' https: http://localhost:* http://127.0.0.1:*"
            )
        return response

    cors_origins = (
        [o.strip() for o in _s.cors_origins.split(",") if o.strip()]
        if isinstance(_s.cors_origins, str)
        else _s.cors_origins
    )
    if cors_origins and "*" in cors_origins:
        if _s.environment.lower() in ("production", "prod", "staging"):
            logger.error(
                "CORS wildcard origin detected in production — forbidding. "
                "Set CORS_ORIGINS to explicit allowed origins."
            )
            cors_origins = []
        else:
            logger.warning("Wildcard CORS origin detected - this is dangerous in production")
    if not cors_origins and _s.environment.lower() not in ("development", "dev", "test"):
        logger.error("No CORS origins configured in non-development environment")
        cors_origins = []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-User-Api-Keys",
        ],
    )
    app.include_router(router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(bm2_router, prefix="/api/v1/bm2", tags=["bm2"])
    app.include_router(sync_router, prefix="/api/v1", tags=["sync"])
    app.include_router(adaptation_router, prefix="/api/v1", tags=["adaptation"])
    app.include_router(performance_router, prefix="/api/v1", tags=["performance"])
    app.include_router(voice_router, prefix="/api/v1", tags=["voice"])

    if STATIC_DIR.exists() and INDEX_FILE.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")
        sqlite3_dir = STATIC_DIR / "sqlite3"
        if sqlite3_dir.exists():
            app.mount("/sqlite3", StaticFiles(directory=str(sqlite3_dir)), name="static-sqlite3")

        @app.head("/")
        async def dashboard_root_head():
            """Gestisce le richieste HEAD alla root della dashboard."""
            return Response(status_code=200)

        @app.get("/")
        async def dashboard_root():
            """Restituisce l'HTML della dashboard SPA per la root."""
            return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

        @app.get("/index.html")
        async def dashboard_index():
            """Restituisce l'HTML della dashboard SPA per /index.html."""
            return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            """Restituisce l'HTML della dashboard SPA per /dashboard."""
            return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

        @app.get("/registerSW.js")
        async def register_sw():
            """Serve il file registerSW.js per la registrazione del service worker."""
            return _static_file_response(
                STATIC_DIR / "registerSW.js",
                "text/javascript",
                headers={"Cache-Control": "no-store"},
            )

        @app.get("/manifest.json")
        async def manifest():
            """Serve il manifest.json della PWA."""
            return _static_file_response(
                STATIC_DIR / "manifest.json",
                "application/json",
                headers={"Cache-Control": "no-store"},
            )

        @app.get("/manifest.webmanifest")
        async def manifest_webmanifest():
            """Serve il manifest.webmanifest della PWA."""
            return _static_file_response(
                STATIC_DIR / "manifest.webmanifest",
                "application/manifest+json",
                headers={"Cache-Control": "no-store"},
            )

        CEO_FILE = STATIC_DIR / "ceo_dashboard.html"
        if CEO_FILE.exists():

            @app.get("/ceo", response_class=HTMLResponse)
            async def ceo_dashboard():
                """Restituisce la dashboard CEO se il file esiste."""
                return CEO_FILE.read_text(encoding="utf-8")

        @app.get("/sw.js")
        async def service_worker():
            """Serve il service worker sw.js."""
            return _static_file_response(
                STATIC_DIR / "sw.js",
                "application/javascript",
                headers={"Cache-Control": "no-store"},
            )

        @app.get("/pwa-192x192.png")
        async def pwa_icon_192():
            """Serve l'icona PWA 192x192."""
            return _static_file_response(STATIC_DIR / "pwa-192x192.png", "image/png")

        @app.get("/pwa-512x512.png")
        async def pwa_icon_512():
            """Serve l'icona PWA 512x512."""
            return _static_file_response(STATIC_DIR / "pwa-512x512.png", "image/png")

        @app.get("/favicon.svg")
        async def favicon_svg():
            """Serve il favicon in formato SVG."""
            return _static_file_response(STATIC_DIR / "favicon.svg", "image/svg+xml")

        @app.get("/apple-touch-icon.png")
        async def apple_touch_icon():
            """Serve l'icona Apple Touch Icon, con fallback all'icona PWA 192x192."""
            icon = STATIC_DIR / "apple-touch-icon.png"
            if not icon.exists():
                icon = STATIC_DIR / "pwa-192x192.png"
            return _static_file_response(icon, "image/png")

        @app.get("/favicon.ico")
        async def favicon():
            """Restituisce un favicon SVG inline di default."""
            return Response(
                content='<svg xmlns="http://www.w3.org/2000/svg" '
                'viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#4ecca3"/>'
                '<text x="50" y="55" font-size="40" text-anchor="middle"></text></svg>',
                media_type="image/svg+xml",
            )

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        async def spa_fallback(full_path: str):
            """Reindirizza le route non API/statiche all'index.html della SPA."""
            if full_path.startswith(("api/", "static/", "assets/", "sqlite3/")):
                return Response(status_code=404)
            # Se la richiesta è per un file statico JS, CSS, WASM, JSON, PNG ecc. non trovato nella root, restituisce 404
            # per evitare che importScripts/script tag riceva la pagina HTML di index.html.
            if any(full_path.endswith(ext) for ext in (".js", ".css", ".wasm", ".json", ".png", ".svg", ".webmanifest")):
                root_file = (STATIC_DIR / full_path).resolve()
                try:
                    root_file.relative_to(STATIC_DIR.resolve())
                except ValueError:
                    return Response(status_code=404)
                if root_file.exists() and root_file.is_file():
                    ext_map = {
                        ".js": "application/javascript",
                        ".css": "text/css",
                        ".wasm": "application/wasm",
                        ".json": "application/json",
                        ".webmanifest": "application/manifest+json",
                    }
                    media_type = ext_map.get(Path(full_path).suffix)
                    return _static_file_response(root_file, media_type)
                return Response(status_code=404)
            return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))

    return app
