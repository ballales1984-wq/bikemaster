"""
BikeMaster - Unified Entrypoint.

Entrypoint principale dell'applicazione BikeMaster. Supporta quattro modalità
di esecuzione:

    python main.py api      -> Avvia il backend FastAPI locale + dashboard SPA (default)
    python main.py web      -> Alias per ``api``, serve la dashboard web
    python main.py hub      -> Avvia il backend cloud Hub (PostgreSQL, multi-tenant)
    python main.py cli      -> Esegue analytics CLI su dati di esempio

La modalità viene selezionata tramite il primo argomento posizionale. Il flag
``--port`` controlla la porta di ascolto (default 8000), mentre ``--reload``
abilita l'hot-reload di uvicorn (solo per sviluppo).
"""

import argparse
import asyncio
import logging
import os
import sys
import tempfile
import traceback

os.environ.setdefault("PYTHONUNBUFFERED", "1")

import uvicorn

from bike_analyzer.backend.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("bikemaster.startup")

_mpl_config_dir = os.path.join(tempfile.gettempdir(), "matplotlib")
os.environ.setdefault("MPLCONFIGDIR", _mpl_config_dir)
os.environ.setdefault("MPLBACKEND", "Agg")


def main():
    parser = argparse.ArgumentParser(description="Bike Analyzer")
    parser.add_argument(
        "mode", nargs="?", default="api", choices=["api", "web", "hub", "cli"]
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "10000")),
    )
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.mode == "hub":
        logger.info("Starting Hub API on http://localhost:%s", args.port)
        try:
            from bike_analyzer.backend.hub.main import create_hub_app

            app = create_hub_app()
        except Exception:
            logger.error("FATAL: failed to build Hub FastAPI app")
            traceback.print_exc()
            sys.exit(1)
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=args.port,
            timeout_graceful_shutdown=30,
        )
    elif args.mode in {"api", "web"}:
        logger.info("Starting API + Dashboard on http://localhost:%s", args.port)
        uvicorn.run(
            "bike_analyzer.backend.api.app_factory:create_app",
            factory=True,
            host="0.0.0.0",
            port=args.port,
            reload=args.reload,
            timeout_graceful_shutdown=30,
        )
    elif args.mode == "cli":
        asyncio.run(run_cli())


async def run_cli():
    """Run CLI analytics on sample data."""
    from bike_analyzer.backend.tracing import setup_tracing as _setup_tracing

    _setup_tracing()
    from bike_analyzer.backend.analytics.analytics import calculate_summary
    from bike_analyzer.backend.db.database import get_all_rides, init_db
    from bike_analyzer.backend.models.models import Ride

    init_db()
    rides = [Ride(**r) for r in get_all_rides()]
    summary = calculate_summary(rides)
    print(f"Total Rides: {summary['total_rides']}")
    print(f"Total Distance: {summary['total_km']} km")
    print(f"Total Calories: {summary['total_calories']}")
    print(f"Avg Speed: {summary['avg_speed_kmh']} km/h")
    print(f"Avg Fatigue: {summary['avg_fatigue']}/10")


if __name__ == "__main__":
    main()
