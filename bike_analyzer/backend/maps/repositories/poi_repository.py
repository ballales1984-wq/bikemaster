"""POI repository for maps domain - data access for POI and SerpApi usage."""

from __future__ import annotations


class MapsPOIRepository:
    @staticmethod
    def _ensure_usage_table(conn) -> None:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS serpapi_usage (
                month TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )"""
        )

    @staticmethod
    def get_usage(month: str | None = None) -> int:
        """Return the number of SerpApi searches recorded for month (YYYY-MM)."""
        from ...db.database import get_maps_usage

        return get_maps_usage(month)

    @staticmethod
    def record_call(month: str | None = None, n: int = 1) -> None:
        """Record SerpApi API calls for usage tracking."""
        from ...db.database import record_maps_call

        record_maps_call(month, n)

    @staticmethod
    def get_nearby_pois(lat: float, lon: float, radius_km: float = 5.0, tenant_id: int = 0) -> list[dict]:
        """Find nearby POIs within radius."""
        from ...db.database import get_nearby_pois as _get_nearby_pois
        return _get_nearby_pois(lat, lon, radius_km, tenant_id=tenant_id)

    @staticmethod
    def save_poi(poi: dict) -> int:
        """Save a POI to the database."""
        from ...db.database import save_poi as _save_poi
        return _save_poi(poi)
