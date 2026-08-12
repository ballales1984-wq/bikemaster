"""PostgreSQL-backed persistence for Points of Interest."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime

from ...core.models import haversine_distance_m
from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_pois_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pois (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                type TEXT NOT NULL,
                photos JSONB DEFAULT '[]'::jsonb,
                video_url TEXT,
                difficulty_note TEXT,
                tags JSONB DEFAULT '[]'::jsonb,
                itinerary_id INTEGER,
                created_by INTEGER,
                tenant_id INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_pois_tenant_lat_lon_name_type
            ON pois(tenant_id, lat, lon, name, type)
            """
        )
        conn.commit()


def save_poi(poi: dict) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_pois_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM pois WHERE tenant_id = %s AND lat = %s AND lon = %s AND name = %s AND type = %s",
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
                return row[0]
            cur.execute(
                """
                INSERT INTO pois
                (name, description, lat, lon, type, photos, video_url,
                 difficulty_note, tags, itinerary_id, created_by, tenant_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
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
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_poi(poi_id: int, tenant_id: int | None = None) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_pois_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute("SELECT * FROM pois WHERE id = %s AND tenant_id = %s", (poi_id, tenant_id))
            else:
                cur.execute("SELECT * FROM pois WHERE id = %s", (poi_id,))
            row = cur.fetchone()
            return _row_to_poi(row) if row else None
    finally:
        _safe_close(conn)


def get_nearby_pois(lat: float, lon: float, radius_km: float = 5.0, tenant_id: int | None = None) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_pois_table(conn)
        radius_m = max(0.0, radius_km) * 1000.0
        delta_lat = radius_km / 111.0
        delta_lon = radius_km / (111.320 * max(0.000001, abs(math.cos(math.radians(lat)))))
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE tenant_id = %s AND lat BETWEEN %s AND %s AND lon BETWEEN %s AND %s",
                    (tenant_id, lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
                )
            else:
                cur.execute(
                    "SELECT * FROM pois WHERE lat BETWEEN %s AND %s AND lon BETWEEN %s AND %s",
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
    finally:
        _safe_close(conn)


def list_pois(itinerary_id: int | None = None, tenant_id: int | None = None) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_pois_table(conn)
        with conn.cursor() as cur:
            if itinerary_id is not None and tenant_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE itinerary_id = %s AND tenant_id = %s ORDER BY id DESC",
                    (itinerary_id, tenant_id),
                )
            elif itinerary_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE itinerary_id = %s ORDER BY id DESC",
                    (itinerary_id,),
                )
            elif tenant_id is not None:
                cur.execute(
                    "SELECT * FROM pois WHERE tenant_id = %s ORDER BY id DESC",
                    (tenant_id,),
                )
            else:
                cur.execute("SELECT * FROM pois ORDER BY id DESC")
            rows = cur.fetchall()
        return [_row_to_poi(r) for r in rows]
    finally:
        _safe_close(conn)


def delete_poi(poi_id: int) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_pois_table(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pois WHERE id = %s", (poi_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def _row_to_poi(row) -> dict:
    if not row:
        return None
    photos = row.get("photos")
    tags = row.get("tags")
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "description": row.get("description"),
        "lat": row.get("lat"),
        "lon": row.get("lon"),
        "type": row.get("type"),
        "photos": json.loads(photos) if photos else [],
        "video_url": row.get("video_url"),
        "difficulty_note": row.get("difficulty_note"),
        "tags": json.loads(tags) if tags else [],
        "itinerary_id": row.get("itinerary_id"),
        "created_by": row.get("created_by"),
        "tenant_id": row.get("tenant_id", 0),
        "created_at": row.get("created_at"),
    }
