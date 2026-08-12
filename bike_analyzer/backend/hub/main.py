"""Hub backend entrypoint — FastAPI app for cloud deployment.

Run with:
    python main.py hub --port 8001

Or directly:
    python -m bike_analyzer.backend.hub.main

The hub uses PostgreSQL (async_db) as its primary store and exposes only
multi-tenant endpoints: auth, admin, and knowledge base.

Note:
    DATABASE_URL is REQUIRED for hub mode. Set it in .env.hub or the
    environment before starting the hub. Without it the app starts but
    database-dependent endpoints will fail.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from pydantic import ValidationError

from bike_analyzer.backend.api.voice_routes import router as voice_router
from bike_analyzer.backend.db.async_db import init_async_db
from bike_analyzer.backend.hub.routes import hub_router
from bike_analyzer.backend.hub.sync_routes import hub_sync_router
from bike_analyzer.backend.observability import init_observability
from bike_analyzer.backend.rate_limiter import limiter
from bike_analyzer.backend.redis_client import close_redis, get_redis
from bike_analyzer.backend.settings import get_settings
from bike_analyzer.backend.task_queue import get_task_queue

logger = logging.getLogger(__name__)
_s = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo di vita dell'applicazione Hub.

    Allo startup avvia tutti i servizi in task in background cosicche'
    uvicorn inizia ad accettare connessioni immediatamente, permettendo
    a Render di rilevare la porta e superare il healthcheck senza
    attendere il completamento di tutte le inizializzazioni.

    Allo shutdown termina la task queue e chiude la connessione Redis.
    Ogni passo e' protetto da try/except per garantire che un errore in
    un servizio non impedisca lo shutdown degli altri.
    """
    if not _s.database_url:
        logger.warning(
            "Hub started without DATABASE_URL — PostgreSQL is required for hub mode. "
            "Set DATABASE_URL in .env.hub or environment."
        )

    async def _init_async_db_bg() -> None:
        try:
            await init_async_db()
            logger.info("Async database initialized successfully.")
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialize PostgreSQL async database")

    async def _init_redis_bg() -> None:
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

    app.state._bg_tasks: list[asyncio.Task] = []
    app.state._bg_tasks.append(asyncio.create_task(_init_async_db_bg()))
    app.state._bg_tasks.append(asyncio.create_task(_init_redis_bg()))
    app.state._bg_tasks.append(asyncio.create_task(_start_task_queue_bg()))
    app.state.start_time = time.time()

    yield

    SHUTDOWN_TIMEOUT = float(os.getenv("SHUTDOWN_TIMEOUT_SECONDS", "25"))
    logger.info("Shutting down hub background services (timeout=%.0fs)", SHUTDOWN_TIMEOUT)
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


def create_hub_app() -> FastAPI:
    """Crea l'applicazione FastAPI del backend Hub (cloud, multi-tenant).

    Configura osservabilita', Prometheus, CORS limitato a Vercel/ngrok,
    rate limiting e include i router per auth, admin, knowledge e sync.
    Espone anche un endpoint /health per il health check.
    """
    app = FastAPI(
        title="BikeMaster Hub API",
        description="Central multi-tenant backend for BikeMaster (cloud)",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
        redoc_url="/redoc" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
        openapi_url="/openapi.json" if _s.environment.lower() in ("development", "dev", "test", "testing") else None,
    )

    init_observability(app)

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

    app.state.limiter = limiter

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handler per errori di validazione Pydantic (422)."""
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=422,
            content={"detail": "Dati non validi", "errors": exc.errors()},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handler per ValueError (400)."""
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # Hub CORS: exact allowed origins + regex fallback for Vercel/Render domains
    from fastapi.middleware.cors import CORSMiddleware

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
        "Hub CORS configured: origins=%s regex=%s",
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

    @app.middleware("http")
    async def limit_request_size(request: Request, call_next):
        """Reject requests with body larger than 10 MB to prevent memory exhaustion."""
        if request.headers.get("content-length"):
            try:
                size = int(request.headers["content-length"])
                if size > 10 * 1024 * 1024:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(status_code=413, content={"detail": "Request body too large"})
            except (ValueError, TypeError):
                pass
        return await call_next(request)

    app.include_router(hub_router)
    app.include_router(hub_sync_router, prefix="/api/v1", tags=["sync"])
    app.include_router(voice_router, prefix="/api/v1", tags=["voice"])

    @app.get("/healthz")
    async def healthz():
        """Root-level liveness probe for platform health checks (Render default)."""
        return {"status": "ok", "mode": "hub"}

    @app.get("/health")
    async def health():
        """Health check endpoint per load balancer e monitoring."""
        return {"status": "ok", "mode": "hub"}

    return app
