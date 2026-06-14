"""Backend package."""

from typing import Any

_BACKEND_ATTRS = {
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
}


def __getattr__(name: str) -> Any:
    if name not in _BACKEND_ATTRS:
        raise AttributeError(name)
    module_name, attr_name = _BACKEND_ATTRS[name]
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = sorted(_BACKEND_ATTRS)
