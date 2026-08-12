"""PostgreSQL-backed persistence for road incidents and route safety scores."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_road_incidents_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS road_incidents (
                id SERIAL PRIMARY KEY,
                source_id TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                incident_date TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                description TEXT NOT NULL DEFAULT '',
                road_type TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'local',
                created_at TEXT NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.commit()


def _ensure_route_safety_scores_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS route_safety_scores (
                id SERIAL PRIMARY KEY,
                ride_id INTEGER NOT NULL,
                athlete_id INTEGER NOT NULL,
                risk_score REAL,
                label TEXT,
                advice TEXT,
                road_type_counts JSONB DEFAULT '{}'::jsonb,
                has_bike_infrastructure BOOLEAN DEFAULT FALSE,
                incident_count INTEGER DEFAULT 0,
                route_length_km REAL DEFAULT 0,
                computed_at TEXT NOT NULL DEFAULT NOW(),
                tenant_id INTEGER DEFAULT 0,
                UNIQUE(ride_id)
            )
            """
        )
        conn.commit()


def save_road_incident(incident: dict) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_road_incidents_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO road_incidents
                (source_id, lat, lon, incident_date, severity, description, road_type, source, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(source_id) DO NOTHING
                RETURNING id
                """,
                (
                    str(incident.get("id", incident.get("source_id", ""))),
                    incident.get("lat"),
                    incident.get("lon"),
                    incident.get("date", incident.get("incident_date", "")),
                    incident.get("severity", "medium"),
                    incident.get("description", "")[:500],
                    incident.get("road_type", ""),
                    incident.get("source", "local"),
                    datetime.now(UTC).isoformat(),
                ),
            )
            result = cur.fetchone()
            conn.commit()
            return result[0] if result else -1
    finally:
        _safe_close(conn)


def save_route_safety_score(score_data: dict, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_route_safety_scores_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO route_safety_scores
                (ride_id, athlete_id, risk_score, label, advice,
                 road_type_counts, has_bike_infrastructure, incident_count,
                 route_length_km, computed_at, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(ride_id) DO UPDATE SET
                    risk_score = excluded.risk_score,
                    label = excluded.label,
                    advice = excluded.advice,
                    road_type_counts = excluded.road_type_counts,
                    has_bike_infrastructure = excluded.has_bike_infrastructure,
                    incident_count = excluded.incident_count,
                    route_length_km = excluded.route_length_km,
                    computed_at = excluded.computed_at,
                    tenant_id = excluded.tenant_id
                RETURNING id
                """,
                (
                    score_data.get("ride_id"),
                    score_data.get("athlete_id"),
                    score_data.get("risk_score"),
                    score_data.get("label"),
                    score_data.get("advice"),
                    json.dumps(score_data.get("road_type_counts", {})),
                    1 if score_data.get("has_bike_infrastructure") else 0,
                    score_data.get("incident_count", 0),
                    score_data.get("route_length_km", 0),
                    datetime.now(UTC).isoformat(),
                    score_data.get("tenant_id", tenant_id),
                ),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_route_safety_score(ride_id: int, tenant_id: int | None = None) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_route_safety_scores_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM route_safety_scores WHERE ride_id = %s AND tenant_id = %s ORDER BY id DESC LIMIT 1",
                    (ride_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM route_safety_scores WHERE ride_id = %s ORDER BY id DESC LIMIT 1",
                    (ride_id,),
                )
            row = cur.fetchone()
            if row:
                return {
                    "id": row.get("id"),
                    "ride_id": row.get("ride_id"),
                    "athlete_id": row.get("athlete_id"),
                    "risk_score": row.get("risk_score"),
                    "label": row.get("label"),
                    "advice": row.get("advice"),
                    "road_type_counts": json.loads(row["road_type_counts"]) if row.get("road_type_counts") else {},
                    "has_bike_infrastructure": bool(row.get("has_bike_infrastructure")),
                    "incident_count": row.get("incident_count", 0),
                    "route_length_km": row.get("route_length_km", 0),
                    "computed_at": row.get("computed_at"),
                }
            return None
    finally:
        _safe_close(conn)
