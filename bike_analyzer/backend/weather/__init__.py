"""Weather package for bike ride planning."""

from typing import Any

_WEATHER_ATTRS = {
    "get_forecast_for_date": ("weather_service", "get_forecast_for_date"),
    "get_weather_for_coordinates": ("weather_service", "get_weather_for_coordinates"),
    "get_weather_score": ("weather_service", "get_weather_score"),
}


def __getattr__(name: str) -> Any:
    if name not in _WEATHER_ATTRS:
        raise AttributeError(name)
    module = __import__("bike_analyzer.backend.weather.weather_service", fromlist=[name])
    return getattr(module, name)


__all__ = sorted(_WEATHER_ATTRS)
