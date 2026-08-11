"""Weather cache repository — data-access port for weather caching.

Isolates the WeatherService (Service layer) from ``db.database`` so the service
holds no ``Service -> Database`` dependency:

    Router -> WeatherService -> WeatherRepository -> db.database

Following the project's Repository convention (``analytics/repositories/``,
``db/repositories/``): this package is ``weather/repositories/``.

The ``db.database`` import is *lazy* (inside the methods) because
``db.database`` imports ``db/repositories/*`` at module load and, in the
current tree, triggers a load-time cycle; resolving the foreign functions at
call time (when the DB layer is fully initialized) mirrors the original
weather_service behaviour and keeps the import graph acyclic at load time.
"""

from __future__ import annotations


class WeatherRepository:
    """Façade over the weather-cache persistence helpers in ``db.database``."""

    @staticmethod
    def get_weather_cache(lat: float, lon: float, date: str) -> dict | None:
        """Return a cached weather record for (lat, lon, date) or None."""
        from ...db.database import get_weather_cache

        return get_weather_cache(lat, lon, date)

    @staticmethod
    def save_weather_cache(lat: float, lon: float, date: str, weather: dict) -> int:
        """Persist a weather record in the cache."""
        from ...db.database import save_weather_cache

        return save_weather_cache(lat, lon, date, weather)
