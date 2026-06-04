"""
Bike Analyzer - Unified Entrypoint.

Supports three modes:
  python main.py api      -> start FastAPI backend (default)
  python main.py web      -> start web frontend
  python main.py cli      -> run CLI analytics on sample data
"""
import argparse
import asyncio
import uvicorn
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bike_analyzer.backend.api.app_factory import create_app


DEFAULT_DB_URL = "sqlite:///./bike_analyzer.db"
WEB_PORT = 8080


def main():
    parser = argparse.ArgumentParser(description="Bike Analyzer")
    parser.add_argument("mode", nargs="?", default="api", choices=["api", "web", "cli"])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.mode == "api":
        print(f"Starting API on http://localhost:{args.port}")
        print(f"Web UI available at http://localhost:{args.port}/web/")
        uvicorn.run(
            create_app(),
            host="0.0.0.0",
            port=args.port,
            reload=args.reload,
        )
    elif args.mode == "web":
        print(f"Starting Web on http://localhost:{WEB_PORT}")
        uvicorn.run(
            create_web_app(),
            host="0.0.0.0",
            port=WEB_PORT,
            reload=args.reload,
        )
    elif args.mode == "cli":
        asyncio.run(run_cli())


def create_web_app():
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    app = FastAPI(title="Bike Analyzer Web")
    web_dir = Path(__file__).parent / "frontend" / "map"

    @app.get("/")
    async def root():
        return FileResponse(str(web_dir / "route.html"))

    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

    return app


async def run_cli():
    """Run CLI analytics on sample data."""
    from bike_analyzer.backend.db.database import get_all_rides, init_db
    from bike_analyzer.backend.analytics.analytics import calculate_summary
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