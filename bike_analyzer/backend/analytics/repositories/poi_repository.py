"""POI repository - data access abstraction for Points of Interest."""

from __future__ import annotations

import contextlib
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
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    data[key] = json.loads(value)
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

    async def get_by_id(self, poi_id: int, tenant_id: int | None = None) -> dict | None:
        if self._session_factory:
            return await self._get_by_id_async(poi_id, tenant_id)
        if self._sync_conn:
            return self._sync_conn.get_poi(poi_id, tenant_id)
        return self._get_by_id_sync(poi_id, tenant_id)

    def _get_by_id_sync(self, poi_id: int, tenant_id: int | None = None) -> dict | None:
        from ...db.database import get_poi

        return get_poi(poi_id, tenant_id=tenant_id)

    async def _get_by_id_async(self, poi_id: int, tenant_id: int | None = None) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.id == poi_id)
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
            row = (await session.execute(stmt)).scalars().first()
            if row is None:
                return None
            data = {c.name: getattr(row, c.name) for c in self._table.__table__.columns}
            return self._parse_json_fields(data)

    @staticmethod
    def list_pois(itinerary_id: int | None = None, tenant_id: int = 0):
        from ...db.database import list_pois

        return list_pois(itinerary_id, tenant_id=tenant_id)

    @staticmethod
    def delete_poi(poi_id: int):
        from ...db.database import delete_poi

        return delete_poi(poi_id)

    async def get_nearby(
        self, lat: float, lon: float, radius_km: float = 5.0, tenant_id: int | None = None
    ) -> list[dict]:
        if self._session_factory:
            return await self._get_nearby_async(lat, lon, radius_km, tenant_id)
        if self._sync_conn:
            return self._sync_conn.get_nearby_pois(lat, lon, radius_km, tenant_id)
        return self._get_nearby_sync(lat, lon, radius_km, tenant_id)

    def _get_nearby_sync(self, lat: float, lon: float, radius_km: float, tenant_id: int | None = None) -> list[dict]:
        from ...db.database import get_nearby_pois

        return get_nearby_pois(lat, lon, radius_km, tenant_id=tenant_id)

    async def _get_nearby_async(
        self, lat: float, lon: float, radius_km: float, tenant_id: int | None = None
    ) -> list[dict]:
        from sqlalchemy import select

        from ....core.models import haversine_distance_m

        radius_m = max(0.0, radius_km) * 1000.0
        async with self._session_factory() as session:
            stmt = select(self._table)
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
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
