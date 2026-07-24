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

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from pydantic import ValidationError

from bike_analyzer.backend.hub.routes import hub_router
from bike_analyzer.backend.hub.sync_routes import hub_sync_router
from bike_analyzer.backend.api.voice_routes import router as voice_router
from bike_analyzer.backend.logging_config import setup_logging
from bike_analyzer.backend.observability import init_observability
from bike_analyzer.backend.rate_limiter import limiter
from bike_analyzer.backend.settings import get_settings
from bike_analyzer.backend.redis_client import close_redis, get_redis
from bike_analyzer.backend.task_queue import get_task_queue
from bike_analyzer.backend.db.async_db import init_async_db

logger = logging.getLogger(__name__)
_s = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo di vita dell'applicazione Hub.

    Allo startup inizializza il database PostgreSQL asincrono, il client
    Redis e la task queue. Ogni servizio e' protetto da try/except perche'
    un errore in un servizio opzionale non deve bloccare l'avvio.

    Allo shutdown termina la task queue e chiude la connessione Redis.
    """

    if not _s.database_url:
        logger.warning(
            "Hub started without DATABASE_URL — PostgreSQL is required for hub mode. "
            "Set DATABASE_URL in .env.hub or environment."
        )

    try:
        await init_async_db()
    except Exception:
        logger.exception("Failed to initialize PostgreSQL async database")

    try:
        await get_redis()
    except Exception:
        logger.exception("Failed to initialize Redis client")

    task_queue = get_task_queue()
    try:
        await task_queue.start()
        app.state.task_queue = task_queue
    except Exception:
        logger.exception("Failed to start background task queue")

    yield

    logger.info("Shutting down hub background services")
    try:
        await task_queue.stop()
    except Exception:
        logger.exception("Failed to stop background task queue")
    try:
        await close_redis()
    except Exception:
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
                excluded_handlers=["/metrics", "/health"],
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

    # Hub CORS: only exact allowed origins, no wildcard regex
    from fastapi.middleware.cors import CORSMiddleware

    cors_origins = (
        [o.strip() for o in _s.cors_origins.split(",") if o.strip()]
        if isinstance(_s.cors_origins, str)
        else _s.cors_origins
    )
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

    app.include_router(hub_router)
    app.include_router(hub_sync_router, prefix="/api/v1", tags=["sync"])
    app.include_router(voice_router, prefix="/api/v1", tags=["voice"])

    @app.get("/health")
    async def health():
        """Health check endpoint per load balancer e monitoring."""
        return {"status": "ok", "mode": "hub", "database": "postgresql" if _s.database_url else "none"}

    return app
