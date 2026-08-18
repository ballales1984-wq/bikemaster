"""Itinerary repository — SQLite persistence for itineraries and stages."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


def _row_to_itinerary(row: tuple) -> dict:
    cols = (
        [d[0] for d in row.cursor_description]
        if hasattr(row, "cursor_description")
        else [
            "id",
            "athlete_id",
            "tenant_id",
            "name",
            "description",
            "start_date",
            "end_date",
            "total_km",
            "total_elevation_m",
            "created_at",
        ]
    )
    data = dict(zip(cols, row, strict=False))
    return {
        "id": data.get("id"),
        "athlete_id": data.get("athlete_id"),
        "tenant_id": data.get("tenant_id", 0),
        "name": data.get("name"),
        "description": data.get("description"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "total_km": data.get("total_km", 0),
        "total_elevation_m": data.get("total_elevation_m", 0),
        "created_at": data.get("created_at"),
    }


def _row_to_stage(row: tuple) -> dict:
    cols = (
        [d[0] for d in row.cursor_description]
        if hasattr(row, "cursor_description")
        else [
            "id",
            "itinerary_id",
            "stage_day",
            "title",
            "distance_km",
            "elevation_gain_m",
            "estimated_km",
            "estimated_elevation_m",
            "ride_id",
            "poi_id",
            "notes",
            "tenant_id",
            "created_at",
            "updated_at",
        ]
    )
    data = dict(zip(cols, row, strict=False))
    return {
        "id": data.get("id"),
        "itinerary_id": data.get("itinerary_id"),
        "stage_day": data.get("stage_day", 1),
        "title": data.get("title"),
        "distance_km": data.get("distance_km", 0),
        "elevation_gain_m": data.get("elevation_gain_m", 0),
        "estimated_km": data.get("estimated_km"),
        "estimated_elevation_m": data.get("estimated_elevation_m"),
        "ride_id": data.get("ride_id"),
        "poi_id": data.get("poi_id"),
        "notes": data.get("notes"),
        "tenant_id": data.get("tenant_id", 0),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def save_itinerary(itinerary: dict) -> int:
    """Create an itinerary. Returns the new row id."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO itineraries
            (athlete_id, tenant_id, name, description, start_date, end_date,
             total_km, total_elevation_m, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                itinerary.get("athlete_id"),
                itinerary.get("tenant_id", 0),
                itinerary.get("name"),
                itinerary.get("description"),
                itinerary.get("start_date"),
                itinerary.get("end_date"),
                itinerary.get("total_km", 0),
                itinerary.get("total_elevation_m", 0),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def get_itinerary(itinerary_id: int) -> dict | None:
    """Retrieve a single itinerary by id."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM itineraries WHERE id = ?", (itinerary_id,))
        row = cur.fetchone()
        return _row_to_itinerary(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def list_itineraries(athlete_id: int | None = None) -> list[dict]:
    """Return all itineraries, optionally filtered by athlete."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if athlete_id is not None:
            cur.execute(
                "SELECT * FROM itineraries WHERE athlete_id = ? ORDER BY id DESC",
                (athlete_id,),
            )
        else:
            cur.execute("SELECT * FROM itineraries ORDER BY id DESC")
        rows = cur.fetchall()
    return [_row_to_itinerary(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def save_stage(stage: dict) -> int:
    """Create a stage for an itinerary. Returns the new row id."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO stages
            (itinerary_id, stage_day, title, distance_km, elevation_gain_m,
             ride_id, poi_id, estimated_km, estimated_elevation_m, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                stage.get("itinerary_id"),
                stage.get("stage_day", 1),
                stage.get("title"),
                stage.get("distance_km"),
                stage.get("elevation_gain_m"),
                stage.get("ride_id"),
                stage.get("poi_id"),
                stage.get("estimated_km"),
                stage.get("estimated_elevation_m"),
                stage.get("notes"),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def list_stages(itinerary_id: int) -> list[dict]:
    """Return all stages for an itinerary, ordered by stage_day."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM stages WHERE itinerary_id = ? ORDER BY stage_day ASC, id ASC",
            (itinerary_id,),
        )
        rows = cur.fetchall()
    return [_row_to_stage(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def get_stage(stage_id: int) -> dict | None:
    """Retrieve a single stage by id."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stages WHERE id = ?", (stage_id,))
        row = cur.fetchone()
        return _row_to_stage(row) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def update_itinerary(itinerary_id: int, data: dict, tenant_id: int | None = None) -> bool:
    """Update an itinerary. Returns True if the row was modified."""
    existing = get_itinerary(itinerary_id)
    if not existing:
        return False
    if tenant_id is not None and existing.get("tenant_id", 0) != tenant_id:
        return False
    now = datetime.now(UTC).isoformat()
    field_map = {
        "name": "name",
        "description": "description",
        "start_date": "start_date",
        "end_date": "end_date",
        "total_km": "total_km",
        "total_elevation_m": "total_elevation_m",
    }
    updates = []
    vals = []
    for key, col in field_map.items():
        if key in data and data[key] is not None:
            updates.append(f"{col}=?")
            vals.append(data[key])
    if not updates:
        return False
    updates.append("updated_at=?")
    vals.append(now)
    vals.append(itinerary_id)
    if tenant_id is not None:
        updates.append("tenant_id=?")
        vals.append(tenant_id)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE itineraries SET {', '.join(updates)} WHERE id = ?",
            vals,
        )
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def delete_itinerary(itinerary_id: int, tenant_id: int | None = None) -> bool:
    """Delete an itinerary. Returns True if the row was deleted."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "DELETE FROM itineraries WHERE id = ? AND tenant_id = ?",
                (itinerary_id, tenant_id),
            )
        else:
            cur.execute("DELETE FROM itineraries WHERE id = ?", (itinerary_id,))
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def update_stage(stage_id: int, data: dict, tenant_id: int | None = None) -> bool:
    """Update a stage. Returns True if the row was modified."""
    existing = get_stage(stage_id)
    if not existing:
        return False
    now = datetime.now(UTC).isoformat()
    field_map = {
        "itinerary_id": "itinerary_id",
        "stage_day": "stage_day",
        "title": "title",
        "distance_km": "distance_km",
        "elevation_gain_m": "elevation_gain_m",
        "estimated_km": "estimated_km",
        "estimated_elevation_m": "estimated_elevation_m",
        "ride_id": "ride_id",
        "poi_id": "poi_id",
        "notes": "notes",
    }
    updates = []
    vals = []
    for key, col in field_map.items():
        if key in data and data[key] is not None:
            updates.append(f"{col}=?")
            vals.append(data[key])
    if not updates:
        return False
    updates.append("updated_at=?")
    vals.append(now)
    vals.append(stage_id)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE stages SET {', '.join(updates)} WHERE id = ?",
            vals,
        )
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def delete_stage(stage_id: int, tenant_id: int | None = None) -> bool:
    """Delete a stage. Returns True if the row was deleted."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "DELETE FROM stages WHERE id = ? AND tenant_id = ?",
                (stage_id, tenant_id),
            )
        else:
            cur.execute("DELETE FROM stages WHERE id = ?", (stage_id,))
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_itineraries")
def reorder_stages(itinerary_id: int, stage_order: list[int], tenant_id: int | None = None) -> bool:
    """Reorder stages by updating stage_day values. Returns True on success."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        for day, stage_id in enumerate(stage_order, start=1):
            cur.execute(
                "UPDATE stages SET stage_day=?, updated_at=? WHERE id=? AND itinerary_id=?",
                (day, datetime.now(UTC).isoformat(), stage_id, itinerary_id),
            )
        conn.commit()
        return True
