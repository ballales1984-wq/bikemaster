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

import asyncio
import logging
import os
import sqlite3
import time
from collections.abc import Coroutine
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

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
from .routes import admin_router, router
from .routers.calendar_routes import router as calendar_router
from .routers.weather_routes import router as weather_router
from .routers.legal_routes import router as legal_router
from .routers.badges_routes import router as badges_router
from .routers.traffic_routes import router as traffic_router
from .routers.knowledge_routes import router as knowledge_router
from .routers.charts_routes import router as charts_router
from .routers.notifications_routes import router as notifications_router
from .routers.ble_routes import router as ble_router
from .routers.hr_routes import router as hr_router
from .routers.maps_routes import router as maps_router
from .routers.itineraries_routes import router as itineraries_router
from .routers.training_routes import router as training_router
from .routers.coach_routes import router as coach_router
from .routers.analytics_routes import router as analytics_router
from .routers.import_routes import router as import_router
from .routers.auth_routes import router as auth_router
from .routers.sync_routes import router as sync_router
from .routers.performance_routes import router as performance_router
from .routers.metabolism_routes import router as metabolism_router
from .routers.rides_routes import router as rides_router
from .routers.aethermap_routes import router as aethermap_router
from .utils import _trusted_forwarded_value

logger = logging.getLogger(__name__)

_s = get_settings()
STATIC_DIR = Path(__file__).parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
SERVE_STATIC = os.getenv("SERVE_STATIC", "false").lower() == "true"

if _s.google_maps_api_key:
    logger.warning(
        "SECURITY REMINDER: Google Maps JS API key is configured. "
        "Ensure HTTP referrer restrictions are set in Google Cloud Console "
        "(APIs & Services > Credentials > restrict key to your domains). "
        "The backend enforces origin checks as defense-in-depth."
    )


def _static_file_response(file_path: Path, media_type: str | None = None, headers: dict | None = None) -> Response:
    """Serve a static file from disk, inferring media type when not provided."""
    if file_path.exists() and media_type:
        content = file_path.read_bytes() if media_type.startswith("image/") else file_path.read_text(encoding="utf-8")
        return Response(content=content, media_type=media_type, headers=headers or {})
    if file_path.exists() and media_type is None:
        return Response(content=file_path.read_bytes(), media_type="application/octet-stream", headers=headers or {})
    return Response(status_code=404, headers=headers or {})


STARTUP_TASK_TIMEOUT = int(os.getenv("STARTUP_TASK_TIMEOUT", "30"))


def _log_flush(msg: str) -> None:
    print(f"[startup] {msg}", flush=True)
    logger.info(msg)
    for handler in logging.getLogger().handlers:
        handler.flush()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo di vita dell'applicazione: startup e shutdown dei servizi.

    Allo startup avvia tutti i servizi in task in background cosicche'
    uvicorn inizia ad accettare connessioni immediatamente, permettendo
    a Render di rilevare la porta e superare il healthcheck senza
    attendere il completamento di tutte le inizializzazioni.

    Ogni task di inizializzazione ha un timeout esplicito (default 30s,
    configurabile via STARTUP_TASK_TIMEOUT) per evitare che un passo
    bloccante (es. connessione Postgres in retry) impedisca il binding
    della porta e causi il timeout di Render.

    Allo shutdown termina nell'ordine: event bus, task queue, Redis.
    Ogni passo e' protetto da try/except per garantire che un errore in
    un servizio non impedisca lo shutdown degli altri.
    """
    from ..db.database import init_db
    from ..logging_config import setup_logging

    setup_logging()
    app.state._bg_tasks: list[asyncio.Task] = []
    app.state._startup_steps: dict[str, str] = {}

    _log_flush("lifespan: setup logging completed")

    async def _run_with_timeout(
        name: str, coro: Coroutine[Any, Any, Any], timeout: float = STARTUP_TASK_TIMEOUT
    ) -> None:
        """Run a coroutine with a timeout, logging start/complete/fail/timeout."""
        app.state._startup_steps[name] = "running"
        _log_flush(f"startup: {name} — starting")
        try:
            await asyncio.wait_for(coro, timeout=timeout)
            app.state._startup_steps[name] = "completed"
            _log_flush(f"startup: {name} — completed")
        except TimeoutError:
            app.state._startup_steps[name] = "timed_out"
            logger.warning(
                "startup: %s — TIMED OUT after %ds (continuing startup anyway)",
                name,
                timeout,
            )
        except Exception:
            app.state._startup_steps[name] = "failed"
            logger.exception("startup: %s — failed (continuing startup anyway)", name)

    async def _init_sqlite() -> None:
        try:
            await asyncio.to_thread(init_db)
            logger.info("SQLite init completed successfully.")
        except Exception:  # noqa: BLE001
            logger.exception("SQLite init failed; continuing startup.")

    async def _run_migrations_bg() -> None:
        if not _s.database_url:
            return
        from ..db.migrations import run_migrations_on_startup

        try:
            await asyncio.to_thread(run_migrations_on_startup)
            logger.info("Database migrations completed successfully.")
        except Exception:  # noqa: BLE001
            logger.exception("Background database migration failed; continuing startup.")

    async def _init_async_db_bg_task() -> None:
        from ..db.async_db import init_async_db

        try:
            await init_async_db()
            logger.info("Async database initialized successfully.")
        except Exception:  # noqa: BLE001
            logger.exception("Async database initialization failed; continuing startup.")

    async def _init_redis_bg() -> None:
        if not _s.redis_url:
            logger.warning("Redis not configured (REDIS_URL not set) — cache disabled")
            return
        try:
            await get_redis()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialize Redis client")

    async def _start_task_queue_bg() -> None:
        queue = get_task_queue()
        try:
            await queue.start()
            app.state.task_queue = queue
        except Exception:  # noqa: BLE001
            logger.exception("Failed to start background task queue")

    async def _start_event_bus_bg() -> None:
        try:
            from ..events import start_event_bus
            await start_event_bus()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to start domain event bus")

    # Launch initialization as two serial chains (DB first, then infra/services)
    # so that dependent steps wait for their prerequisites, while still yielding
    # to uvicorn immediately for Render port detection and health checks.
    async def _db_init_chain() -> None:
        await _run_with_timeout("sqlite-init", _init_sqlite())
        await _run_with_timeout("migrations", _run_migrations_bg())
        await _run_with_timeout("async-db-init", _init_async_db_bg_task())

    async def _infra_init_chain() -> None:
        await _run_with_timeout("redis-init", _init_redis_bg())
        await _run_with_timeout("task-queue-start", _start_task_queue_bg())
        await _run_with_timeout("event-bus-start", _start_event_bus_bg())

    app.state._bg_tasks.append(asyncio.create_task(_db_init_chain()))
    app.state._bg_tasks.append(asyncio.create_task(_infra_init_chain()))
    _log_flush("startup: all background initialization tasks launched, yielding to uvicorn")
    _t_yield = time.monotonic()
    _log_flush(f"startup: YIELD t={_t_yield:.3f} (since create_app start)")
    yield
    _log_flush(f"startup: AFTER YIELD t={time.monotonic():.3f} — uvicorn now serving")

    # Graceful shutdown: cancel background tasks, then stop services.
    SHUTDOWN_TIMEOUT = float(os.getenv("SHUTDOWN_TIMEOUT_SECONDS", "25"))
    logger.info("Shutting down background services (timeout=%.0fs)", SHUTDOWN_TIMEOUT)
    for t in getattr(app.state, "_bg_tasks", []):
        if not t.done():
            t.cancel()
    if app.state._bg_tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*app.state._bg_tasks, return_exceptions=True),
                timeout=SHUTDOWN_TIMEOUT,
            )
        except TimeoutError:
            logger.warning("Background task cancellation timed out; proceeding with service shutdown")

    try:
        from ..events import stop_event_bus

        await asyncio.wait_for(stop_event_bus(), timeout=5)
    except TimeoutError:
        logger.warning("Event bus stop timed out")
    except Exception:  # noqa: BLE001
        logger.exception("Failed to stop domain event bus")
    try:
        if hasattr(app.state, "task_queue"):
            await asyncio.wait_for(app.state.task_queue.stop(), timeout=5)
    except TimeoutError:
        logger.warning("Task queue stop timed out")
    except Exception:  # noqa: BLE001
        logger.exception("Failed to stop background task queue")
    try:
        await asyncio.wait_for(close_redis(), timeout=5)
    except TimeoutError:
        logger.warning("Redis close timed out")
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
    _t0 = time.monotonic()
    _log_flush(f"create_app: START t={_t0:.3f}")
    app = FastAPI(
        title="BikeMaster API",
        description="GPS-based cycling intelligence",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
        redoc_url="/redoc" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
        openapi_url="/openapi.json" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
    )
    _log_flush(f"create_app: FastAPI() done +{time.monotonic()-_t0:.3f}s")

    # Initialize unified observability (Sentry + OpenTelemetry + Zipkin)
    init_observability(app)
    _log_flush(f"create_app: init_observability done +{time.monotonic()-_t0:.3f}s")

    # Conditional Prometheus instrumentation for compatibility
    if _s.environment.lower() not in ("test", "testing"):
        try:
            instrumentator = Instrumentator(
                should_group_status_codes=True,
                should_ignore_untemplated=True,
                excluded_handlers=["/metrics", "/health", "/healthz"],
            )
            instrumentator.add(metrics.requests())
            instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        except Exception:
            logger.debug("Prometheus instrumentation setup failed", exc_info=True)
    _log_flush(f"create_app: prometheus done +{time.monotonic()-_t0:.3f}s")
    # Skip OpenTelemetry instrumentation in test environment
    if _s.environment.lower() in ("test", "testing"):
        pass  # Observability already skipped
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(MetricsMiddleware)
    _log_flush(f"create_app: middleware + exception handlers done +{time.monotonic()-_t0:.3f}s")

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

    @app.exception_handler(sqlite3.IntegrityError)
    async def sqlite_integrity_error_handler(request: Request, exc: sqlite3.IntegrityError):
        """Return 409 for SQLite constraint violations."""
        logger.warning("SQLite integrity error: %s", exc)
        return JSONResponse(
            status_code=409,
            content={"detail": "Conflicto nei dati o vincolo di integrita violato"},
        )

    AUDIT_SKIP_PATHS = {
        "/healthz",
        "/health",
        "/metrics",
        "/api/v1/health",
        "/api/v1/health/redis",
        "/api/v1/health/detailed",
        "/api/v1/health/comprehensive",
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

    from ..request_context import parse_user_keys_header, set_request_user_keys, reset_request_user_keys

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
        import re

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
        _SAFE_LOG = re.compile(r"[^\x20-\x7e]")
        user_id_safe = _SAFE_LOG.sub("", user_id)
        client_ip_safe = _SAFE_LOG.sub("", client_ip)
        path_safe = _SAFE_LOG.sub("", request.url.path)
        logger.info(
            "AUDIT %s %s %s user=%s ip=%s %dms request_id=%s",
            request.method,
            path_safe,
            response.status_code,
            user_id_safe,
            client_ip_safe,
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
        if not request.url.path.startswith("/api/"):
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if _s.environment.lower() in ("production", "prod", "staging"):
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
            if "content-security-policy" not in response.headers:
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; img-src 'self' data: https:; "
                    "script-src 'self' "
                    "https://cdn.jsdelivr.net https://code.jquery.com "
                    "https://unpkg.com; "
                    "style-src 'self' "
                    "https://cdn.jsdelivr.net https://netdna.bootstrapcdn.com "
                    "https://unpkg.com; "
                    "connect-src 'self' https: http://localhost:* http://127.0.0.1:*"
                )
        return response

    @app.middleware("http")
    async def limit_request_size(request: Request, call_next):
        """Reject requests with body larger than 10 MB to prevent memory exhaustion."""
        if request.headers.get("content-length"):
            try:
                size = int(request.headers["content-length"])
                if size > 10 * 1024 * 1024:
                    return JSONResponse(status_code=413, content={"detail": "Request body too large"})
            except (ValueError, TypeError):
                pass
        return await call_next(request)

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
    logger.info(
        "CORS configured: origins=%s regex=%s",
        cors_origins,
        r"https://(bikemaster-[a-zA-Z0-9-]+\.vercel\.app|bikemaster\.onrender\.com)",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"https://(bikemaster-[a-zA-Z0-9-]+\.vercel\.app|bikemaster\.onrender\.com)",
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
    app.include_router(calendar_router, prefix="/api/v1")
    app.include_router(weather_router, prefix="/api/v1")
    app.include_router(legal_router, prefix="/api/v1")
    app.include_router(badges_router, prefix="/api/v1")
    app.include_router(traffic_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")
    app.include_router(charts_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(ble_router, prefix="/api/v1")
    app.include_router(hr_router, prefix="/api/v1")
    app.include_router(maps_router, prefix="/api/v1")
    app.include_router(itineraries_router, prefix="/api/v1")
    app.include_router(training_router, prefix="/api/v1")
    app.include_router(coach_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(import_router, prefix="/api/v1")
    app.include_router(sync_router, prefix="/api/v1")
    app.include_router(performance_router, prefix="/api/v1")
    app.include_router(metabolism_router, prefix="/api/v1")
    app.include_router(rides_router, prefix="/api/v1")
    app.include_router(aethermap_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    _log_flush(f"create_app: include_router(admin) done +{time.monotonic()-_t0:.3f}s")
    @app.get("/healthz")
    async def healthz():
        """Root-level liveness probe for platform health checks (Render default)."""
        return {"status": "ok", "service": "bikemaster"}

    @app.get("/health")
    async def health_root():
        """Root-level health check (aliased to /healthz)."""
        return {"status": "ok", "service": "bikemaster"}

    @app.get("/api/v1/health")
    async def health_api_v1():
        """API v1 health check matching Render's default healthCheckPath."""
        return {"status": "ok", "service": "bikemaster"}

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        if SERVE_STATIC and STATIC_DIR.exists() and INDEX_FILE.exists():
            return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="https://bikemaster-xi.vercel.app", status_code=302)

    if SERVE_STATIC and STATIC_DIR.exists() and INDEX_FILE.exists():
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
            # Se la richiesta è per un file statico (JS, CSS, WASM, JSON, PNG ecc.)
            # non trovato nella root, restituisce 404
            # per evitare che importScripts/script tag riceva la pagina HTML di index.html.
            if any(
                full_path.endswith(ext)
                for ext in (
                    ".js", ".css", ".wasm", ".json", ".png", ".svg", ".webmanifest"
                )
            ):
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

    _log_flush(f"create_app: RETURN app +{time.monotonic()-_t0:.3f}s")
    return app



