"""POI repository - data access abstraction for Points of Interest."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


class POIRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    @property
    def _table(self):
        from ...db.models import POIModel

        return POIModel

    @staticmethod
    def _parse_json_fields(data: dict) -> dict:
        for key in ("photos", "tags"):
            value = data.get(key)
            if isinstance(value, str):
                try:
                    data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
        return data

    async def create(self, poi: dict[str, Any]) -> int:
        if self._session_factory:
            return await self._create_async(poi)
        if self._sync_conn:
            return self._sync_conn.save_poi(poi)
        return self._create_sync(poi)

    def _create_sync(self, poi: dict) -> int:
        from ...db.database import save_poi

        return save_poi(poi)

    async def _create_async(self, poi: dict) -> int:
        from sqlalchemy import insert

        tenant_id = poi.get("tenant_id", 0)
        async with self._session_factory() as session:
            stmt = (
                insert(self._table)
                .values(
                    name=poi.get("name"),
                    description=poi.get("description"),
                    lat=poi.get("lat"),
                    lon=poi.get("lon"),
                    type=poi.get("type"),
                    photos=json.dumps(poi.get("photos", [])),
                    video_url=poi.get("video_url"),
                    difficulty_note=poi.get("difficulty_note"),
                    tags=json.dumps(poi.get("tags", [])),
                    itinerary_id=poi.get("itinerary_id"),
                    created_by=poi.get("created_by"),
                    tenant_id=tenant_id,
                    created_at=datetime.now(UTC),
                )
                .returning(self._table.id)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def get_by_id(self, poi_id: int) -> dict | None:
        if self._session_factory:
            return await self._get_by_id_async(poi_id)
        if self._sync_conn:
            return self._sync_conn.get_poi(poi_id)
        return self._get_by_id_sync(poi_id)

    def _get_by_id_sync(self, poi_id: int) -> dict | None:
        from ...db.database import get_poi

        return get_poi(poi_id)

    async def _get_by_id_async(self, poi_id: int) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.id == poi_id)
            row = (await session.execute(stmt)).scalars().first()
            if row is None:
                return None
            data = {c.name: getattr(row, c.name) for c in self._table.__table__.columns}
            return self._parse_json_fields(data)

    async def get_nearby(
        self, lat: float, lon: float, radius_km: float = 5.0
    ) -> list[dict]:
        if self._session_factory:
            return await self._get_nearby_async(lat, lon, radius_km)
        if self._sync_conn:
            return self._sync_conn.get_nearby_pois(lat, lon, radius_km)
        return self._get_nearby_sync(lat, lon, radius_km)

    def _get_nearby_sync(self, lat: float, lon: float, radius_km: float) -> list[dict]:
        from ...db.database import get_nearby_pois

        return get_nearby_pois(lat, lon, radius_km)

    async def _get_nearby_async(
        self, lat: float, lon: float, radius_km: float
    ) -> list[dict]:
        from sqlalchemy import select

        from ....core.models import haversine_distance_m

        radius_m = max(0.0, radius_km) * 1000.0
        async with self._session_factory() as session:
            stmt = select(self._table)
            rows = (await session.execute(stmt)).scalars().all()
        nearby = []
        for row in rows:
            data = {c.name: getattr(row, c.name) for c in self._table.__table__.columns}
            distance_m = haversine_distance_m(lat, lon, data["lat"], data["lon"])
            if distance_m <= radius_m:
                data["distance_m"] = round(distance_m)
                nearby.append(self._parse_json_fields(data))
        nearby.sort(key=lambda p: p["distance_m"])
        return nearby
