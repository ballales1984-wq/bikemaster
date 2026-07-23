"""BikeMaster - Lifestyle health intelligence system — health state as dynamic balance of lifestyle variables."""

from typing import Any
import importlib

__version__ = "0.1.0"

_TOP_LEVEL_ATTRS = {
    "Ride": ("bike_analyzer.backend.models.models", "Ride"),
    "GPSPoint": ("bike_analyzer.backend.models.models", "GPSPoint"),
    "Segment": ("bike_analyzer.backend.models.models", "Segment"),
    "RouteStatistics": ("bike_analyzer.backend.models.models", "RouteStatistics"),
    "Pause": ("bike_analyzer.backend.models.models", "Pause"),
    "calculate_summary": ("bike_analyzer.backend.analytics.analytics", "calculate_summary"),
    "analyze_ride": ("bike_analyzer.backend.analytics.analytics", "analyze_ride"),
    "process_route": ("bike_analyzer.backend.processing.processing", "process_route"),
    "haversine_distance_m": (
        "bike_analyzer.backend.processing.processing",
        "haversine_distance_m",
    ),
    "create_route_map": ("bike_analyzer.backend.maps.map_renderer", "create_route_map"),
    "save_ride": ("bike_analyzer.backend.db.database", "save_ride"),
    "get_ride": ("bike_analyzer.backend.db.database", "get_ride"),
    "get_all_rides": ("bike_analyzer.backend.db.database", "get_all_rides"),
    "delete_ride": ("bike_analyzer.backend.db.database", "delete_ride"),
    "init_db": ("bike_analyzer.backend.db.database", "init_db"),
    "parse_gpx_file": ("bike_analyzer.backend.ingestion.gps_parser", "parse_gpx_file"),
    "points_to_ride": ("bike_analyzer.backend.ingestion.gps_parser", "points_to_ride"),
}


def __getattr__(name: str) -> Any:
    if name not in _TOP_LEVEL_ATTRS:
        raise AttributeError(name)
    module_name, attr_name = _TOP_LEVEL_ATTRS[name]
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


__all__ = sorted({"__version__", *_TOP_LEVEL_ATTRS})
