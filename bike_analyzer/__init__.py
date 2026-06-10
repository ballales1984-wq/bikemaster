"""BikeMaster - GPS-based cycling performance intelligence system."""

__version__ = "0.1.0"

from .backend.analytics.analytics import analyze_ride, calculate_summary
from .backend.db.database import (
    delete_ride,
    get_all_rides,
    get_ride,
    init_db,
    save_ride,
)
from .backend.ingestion.gps_parser import parse_gpx_file, points_to_ride
from .backend.maps.map_renderer import create_route_map
from .backend.models.models import GPSPoint, Pause, Ride, RouteStatistics, Segment
from .backend.processing.processing import haversine_distance_m, process_route

__all__ = [
    "Ride", "GPSPoint", "Segment", "RouteStatistics", "Pause",
    "calculate_summary", "analyze_ride",
    "process_route", "haversine_distance_m",
    "create_route_map",
    "save_ride", "get_ride", "get_all_rides", "delete_ride", "init_db",
    "parse_gpx_file", "points_to_ride"
]
