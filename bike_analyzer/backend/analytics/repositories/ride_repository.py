"""Ride repository - data access abstraction for rides."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


class RideRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    @property
    def _table(self):
        from ...db.models import RideModel
        return RideModel

    async def save(self, ride: dict[str, Any]) -> int:
        if self._session_factory:
            return await self._save_async(ride)
        if self._sync_conn:
            return self._sync_conn.save_ride(ride)
        return self._save_sync(ride)

    async def _save_async(self, ride: dict) -> int:
        from sqlalchemy import insert

        gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
        async with self._session_factory() as session:
            stmt = (
                insert(self._table)
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
                .returning(self._table.id)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    def _save_sync(self, ride: dict) -> int:
        from ...db.database import save_ride
        return save_ride(ride)

    async def get_by_id(self, ride_id: int) -> dict | None:
        if self._session_factory:
            return await self._get_by_id_async(ride_id)
        if self._sync_conn:
            return self._sync_conn.get_ride(ride_id)
        return self._get_by_id_sync(ride_id)

    async def _get_by_id_async(self, ride_id: int) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.id == ride_id)
            result = await session.execute(stmt)
            row = result.mappings().first()
            if not row:
                return None
            data = dict(row)
            if data.get("gps_points"):
                data["gps_points"] = json.loads(data["gps_points"])
            return data

    def _get_by_id_sync(self, ride_id: int) -> dict | None:
        from ...db.database import get_ride
        return get_ride(ride_id)

    async def get_by_athlete(self, athlete_id: int) -> list[dict]:
        if self._session_factory:
            return await self._get_by_athlete_async(athlete_id)
        if self._sync_conn:
            return self._sync_conn.get_rides_by_athlete(athlete_id)
        return self._get_by_athlete_sync(athlete_id)

    async def _get_by_athlete_async(self, athlete_id: int) -> list[dict]:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = (
                select(self._table)
                .where(self._table.athlete_id == athlete_id)
                .order_by(self._table.date.desc())
            )
            result = await session.execute(stmt)
            rows = result.mappings().all()
            rides = []
            for row in rows:
                data = dict(row)
                if data.get("gps_points"):
                    data["gps_points"] = json.loads(data["gps_points"])
                rides.append(data)
            return rides

    def _get_by_athlete_sync(self, athlete_id: int) -> list[dict]:
        from ...db.database import get_rides_by_athlete
        return get_rides_by_athlete(athlete_id)

    async def list_all(self) -> list[dict]:
        if self._session_factory:
            return await self._list_all_async()
        if self._sync_conn:
            return self._sync_conn.get_all_rides()
        return self._list_all_sync()

    async def _list_all_async(self) -> list[dict]:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).order_by(self._table.date.desc())
            result = await session.execute(stmt)
            rows = result.mappings().all()
            rides = []
            for row in rows:
                data = dict(row)
                if data.get("gps_points"):
                    data["gps_points"] = json.loads(data["gps_points"])
                rides.append(data)
            return rides

    def _list_all_sync(self) -> list[dict]:
        from ...db.database import get_all_rides
        return get_all_rides()

    async def delete(self, ride_id: int) -> bool:
        if self._session_factory:
            return await self._delete_async(ride_id)
        if self._sync_conn:
            return self._sync_conn.delete_ride(ride_id)
        return self._delete_sync(ride_id)

    async def _delete_async(self, ride_id: int) -> bool:
        from sqlalchemy import delete

        async with self._session_factory() as session:
            stmt = delete(self._table).where(self._table.id == ride_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    def _delete_sync(self, ride_id: int) -> bool:
        from ...db.database import delete_ride
        return delete_ride(ride_id)