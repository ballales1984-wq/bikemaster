"""Weather repository - data access abstraction for weather cache."""

from __future__ import annotations

from ...db.database import get_weather_cache, save_weather_cache


class WeatherRepository:
    @staticmethod
    def get_weather_cache(lat: float, lon: float, date: str) -> dict | None:
        """Retrieve cached weather data for coordinates and date."""
        return get_weather_cache(lat, lon, date)

    @staticmethod
    def save_weather_cache(lat: float, lon: float, date: str, weather: dict) -> int:
        """Save weather data to cache."""
        return save_weather_cache(lat, lon, date, weather)
