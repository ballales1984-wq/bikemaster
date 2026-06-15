"""Ride repository - data access abstraction for rides."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence

from ..models.models import Ride


class RideRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    async def save(self, ride: dict) -> int:
        if self._session_factory:
            return await self._save_async(ride)
        return self._save_sync(ride)

    async def _save_async(self, ride: dict) -> int:
        import json

        from sqlalchemy import insert

        async with self._session_factory() as session:
            gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
            stmt = (
                insert(self._ride_model)
                .values(
                    athlete_id=ride.get("athlete_id"),
                    date=ride.get("date"),
                    distance_km=ride.get("distance_km", 0),
                    duration_minutes=ride.get("duration_minutes", 0),
                    avg_speed_kmh=ride.get("avg_speed_kmh", 0),
                    weight_kg=ride.get("weight_kg", 70),
                    calories=ride.get("calories", 0),
                    heart_rate_avg=ride.get("heart_rate_avg"),
                    elevation_gain_m=ride.get("elevation_gain_m"),
                    gps_points=gps_points,
                    created_at=datetime.now(UTC),
                )
                .returning(self._ride_model.id)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def get_by_id(self, ride_id: int) -> dict | None:
        if self._session_factory:
            return await self._get_by_id_async(ride_id)
        return self._get_by_id_sync(ride_id)

    async def get_by_athlete(self, athlete_id: int) -> list[dict]:
        if self._session_factory:
            return await self._get_by_athlete_async(athlete_id)
        return self._get_by_athlete_sync(athlete_id)

    async def delete(self, ride_id: int) -> bool:
        pass

    async def list_all(self) -> list[dict]:
        if self._session_factory:
            return await self._list_all_async()
        return self._list_all_sync()

    def _save_sync(self, ride: dict) -> int:
        from ..db.database import save_ride
        return save_ride(ride)

    def _get_by_id_sync(self, ride_id: int) -> dict | None:
        from ..db.database import get_ride
        return get_ride(ride_id)

    def _get_by_athlete_sync(self, athlete_id: int) -> list[dict]:
        from ..db.database import get_rides_by_athlete
        return get_rides_by_athlete(athlete_id)

    def _list_all_sync(self) -> list[dict]:
        from ..db.database import get_all_rides
        return get_all_rides()
