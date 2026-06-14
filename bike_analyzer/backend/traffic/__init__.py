"""Traffic and road safety package for BikeMaster."""

from typing import Any

_TRAFFIC_ATTRS = {
    "fetch_incidents": ("incident_fetcher", "fetch_incidents"),
    "get_incident_stats": ("incident_fetcher", "get_incident_stats"),
    "fetch_bike_lanes": ("overpass_client", "fetch_bike_lanes"),
    "fetch_road_data": ("overpass_client", "fetch_road_data"),
    "get_road_type_summary": ("overpass_client", "get_road_type_summary"),
    "analyze_route_safety": ("safety_analyzer", "analyze_route_safety"),
    "compute_risk_score": ("safety_analyzer", "compute_risk_score"),
}


def __getattr__(name: str) -> Any:
    if name not in _TRAFFIC_ATTRS:
        raise AttributeError(name)
    module_name, attr_name = _TRAFFIC_ATTRS[name]
    module = __import__(f"bike_analyzer.backend.traffic.{module_name}", fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = sorted(_TRAFFIC_ATTRS)
