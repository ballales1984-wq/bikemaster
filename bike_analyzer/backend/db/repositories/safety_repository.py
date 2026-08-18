"""Safety repository — SQLite persistence for road incidents and route safety scores."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_safety")
def save_road_incident(incident: dict) -> int:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT OR IGNORE INTO road_incidents
            (source_id, lat, lon, incident_date, severity, description,
             road_type, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_safety")
def save_route_safety_score(score_data: dict, tenant_id: int = 0) -> int:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO route_safety_scores
            (ride_id, athlete_id, risk_score, label, advice,
             road_type_counts, has_bike_infrastructure, incident_count,
             route_length_km, computed_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ride_id) DO UPDATE SET
                risk_score = excluded.risk_score,
                label = excluded.label,
                advice = excluded.advice,
                road_type_counts = excluded.road_type_counts,
                has_bike_infrastructure = excluded.has_bike_infrastructure,
                incident_count = excluded.incident_count,
                route_length_km = excluded.route_length_km,
                computed_at = excluded.computed_at,
                tenant_id = excluded.tenant_id""",
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
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_safety")
def get_route_safety_score(ride_id: int, tenant_id: int | None = None) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM route_safety_scores WHERE ride_id = ? AND tenant_id = ? ORDER BY id DESC LIMIT 1",
                (ride_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM route_safety_scores WHERE ride_id = ? ORDER BY id DESC LIMIT 1",
                (ride_id,),
            )
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "ride_id": row[1],
                "athlete_id": row[2],
                "risk_score": row[3],
                "label": row[4],
                "advice": row[5],
                "road_type_counts": json.loads(row[6]) if row[6] else {},
                "has_bike_infrastructure": bool(row[7]),
                "incident_count": row[8],
                "route_length_km": row[9],
                "computed_at": row[10],
            }
        return None
