"""Weather cache repository — data-access abstraction for weather caching.

Owns the only weather <-> database interaction so that ``weather_service``
(Service layer) never imports ``db.database`` directly.

Layering enforced:

    Router  ->  WeatherService  ->  WeatherRepository  ->  db.database
                                                    ^  no Service -> Database edge

This mirrors ``analytics/repositories/metabolism_repository.py`` and follows
the project's Repository convention (static-method façade over db.database).
"""

from __future__ import annotations

from ..db.database import get_weather_cache, save_weather_cache


class WeatherRepository:
    @staticmethod
    def get_cached(lat: float, lon: float, date: str) -> dict | None:
        """Return a cached weather record for (lat, lon, date) or None."""
        return get_weather_cache(lat, lon, date)

    @staticmethod
    def cache(lat: float, lon: float, date: str, weather: dict) -> None:
        """Persist a weather record in the cache."""
        return save_weather_cache(lat, lon, date, weather)
