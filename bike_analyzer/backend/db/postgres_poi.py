"""PostgreSQL-backed persistence for Points of Interest (POI).

When DATABASE_URL is configured (production on Render) POI data must
live on the managed PostgreSQL database, not on the ephemeral container-local
SQLite file. On SQLite (local / offline) the synchronous layer in
database.py is still the authoritative store; this module is only ever
invoked through the thin dispatch guards added at the top of the
database.py functions.

The public function names mirror database.py 1:1 so the routes keep
importing the same symbols. All column sets, defaults and return shapes are
deliberately aligned with the SQLite implementation so the two stores stay
swap-compatible.
"""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import UTC, datetime
from typing import Any

from ..settings import get_settings

_s = get_settings()
logger = logging.getLogger(__name__)


def _url() -> str:
    return (os.environ.get("DATABASE_URL") or _s.database_url or "").strip()


def has_postgres() -> bool:
    return bool(_url())


def _connect():
    """Open a real psycopg2 connection to the managed PostgreSQL backend."""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        conn = psycopg2.connect(_url(), cursor_factory=RealDictCursor)
        logger.warning("PostgreSQL connection opened successfully")
        return conn
    except Exception as exc:
        logger.error("PostgreSQL connection failed: %s", exc)
        raise


def _ensure_tables(conn) -> None:  # pragma: no cover - kept for standalone bootstrap
    """Best-effort CREATE TABLE IF NOT EXISTS fallback.

    On Render the tables are already created at startup by
    async_db.init_async_db (driven by the SQLAlchemy models in
    db/models.py), so every statement here is a no-op.
    Uses PostgreSQL-native SERIAL (never SQLite AUTOINCREMENT).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pois (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                type TEXT NOT NULL,
                photos TEXT,
                video_url TEXT,
                difficulty_note TEXT,
                tags TEXT,
                itinerary_id INTEGER REFERENCES itineraries(id) ON DELETE SET NULL,
                created_by INTEGER REFERENCES athletes(id) ON DELETE SET NULL,
                tenant_id INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pois_coords_pg ON pois(lat, lon)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pois_type_pg ON pois(type)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pois_tenant_pg ON pois(tenant_id)")
    conn.commit()


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    d = {}
    for key in row:
        val = row[key]
        if isinstance(val, datetime):
            d[key] = val.isoformat()
        else:
            d[key] = val
    return d


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


def save_poi(poi: dict) -> int:
    """Create a Point of Interest in PostgreSQL. Returns the new row id."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        now = datetime.now(UTC).isoformat()
        cols = [
            "name", "description", "lat", "lon", "type", "photos", "video_url",
            "difficulty_note", "tags", "itinerary_id", "created_by", "tenant_id", "created_at",
        ]
        vals = [
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
            now,
        ]
        placeholders = ", ".join(["%s"] * len(vals))
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO pois ({', '.join(cols)}) VALUES ({placeholders}) RETURNING id",
                vals,
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        conn.close()


def get_poi(poi_id: int, tenant_id: int | None = None) -> dict | None:
    """Retrieve a single POI by id, optionally filtered by tenant."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE id=%s AND tenant_id=%s",
                    (poi_id, tenant_id),
                )
            else:
                cur.execute("SELECT * FROM pois WHERE id=%s", (poi_id,))
            row = cur.fetchone()
            return _row_to_poi(row) if row else None
    finally:
        conn.close()


def get_nearby_pois(lat: float, lon: float, radius_km: float = 5.0, tenant_id: int | None = None) -> list[dict]:
    """Return POIs within radius_km of (lat, lon) using the haversine distance.

    A coarse lat/lon bounding box narrows the candidate set before the exact
    distance filter, which keeps the query efficient without PostGIS.

    When tenant_id is provided, only POIs belonging to that tenant are
    returned, preventing cross-tenant GPS data disclosure.
    """
    from ...core.models import haversine_distance_m

    radius_m = max(0.0, radius_km) * 1000.0
    delta_lat = radius_km / 111.0
    delta_lon = radius_km / (111.320 * max(0.000001, abs(math.cos(math.radians(lat)))))

    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE tenant_id=%s AND lat BETWEEN %s AND %s AND lon BETWEEN %s AND %s",
                    (tenant_id, lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
                )
            else:
                cur.execute(
                    "SELECT * FROM pois WHERE lat BETWEEN %s AND %s AND lon BETWEEN %s AND %s",
                    (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    nearby = []
    for row in rows:
        poi = _row_to_poi(row)
        distance_m = haversine_distance_m(lat, lon, poi["lat"], poi["lon"])
        if distance_m <= radius_m:
            poi["distance_m"] = round(distance_m)
            nearby.append(poi)
    nearby.sort(key=lambda p: p["distance_m"])
    return nearby


def list_pois(itinerary_id: int | None = None, tenant_id: int | None = None) -> list[dict]:
    """Return all POIs, optionally filtered by itinerary_id and/or tenant_id.

    When tenant_id is provided, only POIs belonging to that tenant are
    returned, preventing cross-tenant data disclosure.
    """
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if itinerary_id is not None and tenant_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE itinerary_id=%s AND tenant_id=%s ORDER BY id DESC",
                    (itinerary_id, tenant_id),
                )
            elif itinerary_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE itinerary_id=%s ORDER BY id DESC",
                    (itinerary_id,),
                )
            elif tenant_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE tenant_id=%s ORDER BY id DESC",
                    (tenant_id,),
                )
            else:
                cur.execute("SELECT * FROM pois ORDER BY id DESC")
            rows = cur.fetchall()
    finally:
        conn.close()
    return [_row_to_poi(r) for r in rows]


def delete_poi(poi_id: int) -> bool:
    """Delete a POI by id. Returns True if deleted."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pois WHERE id=%s", (poi_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
    finally:
        conn.close()
