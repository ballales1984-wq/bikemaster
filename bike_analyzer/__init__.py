"""BikeMaster - GPS-based cycling performance intelligence system."""

__version__ = "0.1.0"

from .backend.models.models import Ride, GPSPoint, Segment, RouteStatistics, Pause
from .backend.analytics.analytics import calculate_summary, analyze_ride
from .backend.processing.processing import process_route, haversine_distance_m
from .backend.maps.map_renderer import create_route_map
from .backend.db.database import save_ride, get_ride, get_all_rides, delete_ride, init_db
from .backend.ingestion.gps_parser import parse_gpx_file, points_to_ride

__all__ = [
    "Ride", "GPSPoint", "Segment", "RouteStatistics", "Pause",
    "calculate_summary", "analyze_ride",
    "process_route", "haversine_distance_m",
    "create_route_map",
    "save_ride", "get_ride", "get_all_rides", "delete_ride", "init_db",
    "parse_gpx_file", "points_to_ride"
]