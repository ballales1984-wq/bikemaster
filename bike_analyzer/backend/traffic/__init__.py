"""Traffic and road safety module for BikeMaster.

Provides:
- OSM Overpass API integration for road/bike lane data
- Route safety scoring based on road type, bike infrastructure, and incident data
- Incident data fetching (configurable sources)
- Risk heatmap generation for routes

Integrations:
- OpenStreetMap Overpass API (free, no key required)
- Configurable incident data sources (local JSON, ANAS open data, etc.)
"""

from .incident_fetcher import fetch_incidents, get_incident_stats
from .overpass_client import fetch_bike_lanes, fetch_road_data, get_road_type_summary
from .safety_analyzer import analyze_route_safety, compute_risk_score

__all__ = [
    "fetch_road_data",
    "fetch_bike_lanes",
    "get_road_type_summary",
    "analyze_route_safety",
    "compute_risk_score",
    "fetch_incidents",
    "get_incident_stats",
]
