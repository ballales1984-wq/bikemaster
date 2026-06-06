"""
Bike Analyzer - Unified Entrypoint.

Supports two modes:
  python main.py api      -> start FastAPI backend + dashboard (default)
  python main.py cli      -> run CLI analytics on sample data
"""
import argparse
import asyncio
import uvicorn
import sys
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

from bike_analyzer.backend.api.app_factory import create_app


def main():
    parser = argparse.ArgumentParser(description="Bike Analyzer")
    parser.add_argument("mode", nargs="?", default="api", choices=["api", "cli"])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.mode == "api":
        print(f"Starting API + Dashboard on http://localhost:{args.port}")
        uvicorn.run(
            create_app(),
            host="0.0.0.0",
            port=args.port,
            reload=args.reload,
        )
    elif args.mode == "cli":
        asyncio.run(run_cli())


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
