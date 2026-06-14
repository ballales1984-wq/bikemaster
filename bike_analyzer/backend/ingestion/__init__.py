"""Ingestion package."""

from typing import Any

_INGESTION_ATTRS = {
    "parse_fit_file": ("gps_parser", "parse_fit_file"),
    "parse_gpx_file": ("gps_parser", "parse_gpx_file"),
    "points_to_ride": ("gps_parser", "points_to_ride"),
    "strava_to_ride": ("strava_client", "strava_to_ride"),
    "fetch_strava_activities": ("strava_client", "fetch_activities"),
    "get_strava_token": ("strava_client", "get_valid_token"),
    "garmin_to_ride": ("garmin_client", "garmin_to_ride"),
    "fetch_garmin_activities": ("garmin_client", "fetch_activities"),
    "get_garmin_token": ("garmin_client", "get_valid_token"),
}


def __getattr__(name: str) -> Any:
    if name not in _INGESTION_ATTRS:
        raise AttributeError(name)
    module_name, attr_name = _INGESTION_ATTRS[name]
    module = __import__(f"bike_analyzer.backend.ingestion.{module_name}", fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = sorted(_INGESTION_ATTRS)
