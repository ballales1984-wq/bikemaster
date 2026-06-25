"""
Bike Analyzer - Unified Entrypoint.

Supports three modes:
  python main.py api      -> start FastAPI backend + dashboard (default)
  python main.py web      -> alias for api, serving the web dashboard
  python main.py cli      -> run CLI analytics on sample data
"""
import argparse
import asyncio
import logging
import os
import sys
import traceback

import uvicorn

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("bikemaster.startup")

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("MPLBACKEND", "Agg")

try:
    from bike_analyzer.backend.api.app_factory import create_app

    app = create_app()
except Exception:
    logger.error("FATAL: failed to build FastAPI app")
    traceback.print_exc()
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Bike Analyzer")
    parser.add_argument("mode", nargs="?", default="api", choices=["api", "web", "cli"])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.mode in {"api", "web"}:
        print(f"Starting API + Dashboard on http://localhost:{args.port}")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=args.port,
            reload=args.reload,
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
    print(f"Avg Speed: {summary['avg_speed']} km/h")
    print(f"Avg Fatigue: {summary['avg_fatigue']}/10")


if __name__ == "__main__":
    main()
