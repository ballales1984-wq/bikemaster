"""Processing package."""

from typing import Any

_PROCESSING_ATTRS = {
    "GPSPoint": ("bike_analyzer.backend.models.models", "GPSPoint"),
    "haversine_distance_m": ("bike_analyzer.backend.models.models", "haversine_distance_m"),
    "build_segments": ("bike_analyzer.backend.processing.processing", "build_segments"),
    "compute_statistics": ("bike_analyzer.backend.processing.processing", "compute_statistics"),
    "detect_pauses": ("bike_analyzer.backend.processing.processing", "detect_pauses"),
    "process_route": ("bike_analyzer.backend.processing.processing", "process_route"),
    "remove_outliers": ("bike_analyzer.backend.processing.processing", "remove_outliers"),
}


def __getattr__(name: str) -> Any:
    if name not in _PROCESSING_ATTRS:
        raise AttributeError(name)
    module_name, attr_name = _PROCESSING_ATTRS[name]
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = sorted(_PROCESSING_ATTRS)
