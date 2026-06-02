"""App factory and initialization"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.dependencies import DEFAULT_DB_URL
from backend.db.session import init_db
from backend.api import rides


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DEFAULT_DB_URL)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Bike Analyzer API",
        description="GPS Analytics System for Cycling Performance",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(rides.router, prefix="/api/rides", tags=["rides"])
    app.include_router(rides.router_prefixless, tags=["health"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "bike-analyzer"}

    return app
