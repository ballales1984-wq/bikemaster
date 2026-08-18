"""POI repository — SQLite persistence for points of interest."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime

from ....core.models import haversine_distance_m
from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


def _row_to_poi(row) -> dict:
    keys = row.keys() if hasattr(row, "keys") else []

    def _col(name, default=None):
        return row[name] if name in keys else default

    photos = _col("photos")
    tags = _col("tags")
    return {
        "id": _col("id"),
        "name": _col("name"),
        "description": _col("description"),
        "lat": _col("lat"),
        "lon": _col("lon"),
        "type": _col("type"),
        "photos": json.loads(photos) if photos else [],
        "video_url": _col("video_url"),
        "difficulty_note": _col("difficulty_note"),
        "tags": json.loads(tags) if tags else [],
        "itinerary_id": _col("itinerary_id"),
        "created_by": _col("created_by"),
        "tenant_id": _col("tenant_id", 0),
        "created_at": _col("created_at"),
    }


@pg_dispatch("bike_analyzer.backend.db.postgres_poi")
def save_poi(poi: dict) -> int:
    """Create a Point of Interest. Returns the new row id."""

    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM pois WHERE tenant_id = ? AND lat = ? AND lon = ? AND name = ? AND type = ?",
            (
                poi.get("tenant_id", 0),
                poi.get("lat"),
                poi.get("lon"),
                poi.get("name"),
                poi.get("type"),
            ),
        )
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            """INSERT INTO pois
            (name, description, lat, lon, type, photos, video_url,
             difficulty_note, tags, itinerary_id, created_by, tenant_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                poi.get("name"),
                poi.get("description"),
                poi.get("lat"),
                poi.get("lon"),
                poi.get("type"),
                json.dumps(poi.get("photos", [])),
                poi.get("video_url"),
                poi.get("difficulty_note"),
                json.dumps(poi.get("tags", [])),
                poi.get("itinerary_id"),
                poi.get("created_by"),
                poi.get("tenant_id", 0),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_poi")
def get_poi(poi_id: int, tenant_id: int | None = None) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM pois WHERE id = ? AND tenant_id = ?", (poi_id, tenant_id))
        else:
            cur.execute("SELECT * FROM pois WHERE id = ?", (poi_id,))
        row = cur.fetchone()
        return _row_to_poi(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_poi")
def get_nearby_pois(lat: float, lon: float, radius_km: float = 5.0, tenant_id: int | None = None) -> list[dict]:
    """Return POIs within ``radius_km`` of (lat, lon) using the haversine distance.

    A coarse lat/lon bounding box narrows the candidate set before the exact
    distance filter, which keeps the query efficient without PostGIS.

    When ``tenant_id`` is provided, only POIs belonging to that tenant are
    returned, preventing cross-tenant GPS data disclosure.
    """

    radius_m = max(0.0, radius_km) * 1000.0
    delta_lat = radius_km / 111.0
    delta_lon = radius_km / (111.320 * max(0.000001, abs(math.cos(math.radians(lat)))))

    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM pois WHERE tenant_id = ? AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?",
                (tenant_id, lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
            )
        else:
            cur.execute(
                "SELECT * FROM pois WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?",
                (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
            )
        rows = cur.fetchall()

    nearby = []
    for row in rows:
        poi = _row_to_poi(row)
        distance_m = haversine_distance_m(lat, lon, poi["lat"], poi["lon"])
        if distance_m <= radius_m:
            poi["distance_m"] = round(distance_m)
            nearby.append(poi)
    nearby.sort(key=lambda p: p["distance_m"])
    return nearby


@pg_dispatch("bike_analyzer.backend.db.postgres_poi")
def list_pois(itinerary_id: int | None = None, tenant_id: int | None = None) -> list[dict]:
    """Return all POIs, optionally filtered by ``itinerary_id`` and/or ``tenant_id``.

    When ``tenant_id`` is provided, only POIs belonging to that tenant are
    returned, preventing cross-tenant data disclosure.
    """

    with _get_db_connection() as conn:
        cur = conn.cursor()
        if itinerary_id is not None and tenant_id is not None:
            cur.execute(
                "SELECT * FROM pois WHERE itinerary_id = ? AND tenant_id = ? ORDER BY id DESC",
                (itinerary_id, tenant_id),
            )
        elif itinerary_id is not None:
            cur.execute(
                "SELECT * FROM pois WHERE itinerary_id = ? ORDER BY id DESC",
                (itinerary_id,),
            )
        elif tenant_id is not None:
            cur.execute(
                "SELECT * FROM pois WHERE tenant_id = ? ORDER BY id DESC",
                (tenant_id,),
            )
        else:
            cur.execute("SELECT * FROM pois ORDER BY id DESC")
        rows = cur.fetchall()
    return [_row_to_poi(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_poi")
def delete_poi(poi_id: int) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM pois WHERE id = ?", (poi_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
