"""PostgreSQL-backed persistence for the itinerary domain.

When ``DATABASE_URL`` is configured (production on Render) the
``itineraries``, ``stages`` and ``pois`` tables must live on the *managed*
PostgreSQL database, not on the ephemeral, container-local SQLite file. This
module is only ever invoked through the thin dispatch guards added at the top
of the ``database.py`` functions — mirroring the pattern already used by
``postgres_athlete.py`` and ``postgres_rides.py``.

The public function names mirror ``database.py`` 1:1 so the routes keep
importing the same symbols. All column sets, defaults and return shapes are
deliberately aligned with the SQLite implementation so the two stores stay
swap-compatible.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..settings import get_settings

_s = get_settings()

# Reuse the connection / dispatch primitives defined once in postgres_athlete
# so there is a single source of truth for "is postgres configured" and for the
# psycopg2 connection factory.
from .postgres_athlete import _connect, has_postgres  # noqa: E402,F401

_ITINERARY_COLS = [
    "athlete_id", "tenant_id", "name", "description",
    "start_date", "end_date", "total_km", "total_elevation_m",
    "created_at", "updated_at",
]

_STAGE_COLS = [
    "itinerary_id", "stage_day", "title", "distance_km", "elevation_gain_m",
    "estimated_km", "estimated_elevation_m", "ride_id", "poi_id", "notes",
    "tenant_id", "created_at", "updated_at",
]

_POI_COLS = [
    "name", "description", "lat", "lon", "type",
    "photos", "video_url", "difficulty_note", "tags",
    "itinerary_id", "created_by", "tenant_id", "created_at",
]


def _ensure_tables(conn) -> None:  # pragma: no cover - kept for standalone bootstrap
    """Best-effort ``CREATE TABLE IF NOT EXISTS`` fallback.

    On Render the tables are already created at startup by
    ``async_db.init_async_db`` (driven by the SQLAlchemy models in
    ``db/models.py``), so every statement here is a no-op. This only matters
    when the sync pg layer is used standalone (e.g. ad-hoc scripts).
    Uses PostgreSQL-native ``SERIAL`` (never SQLite ``AUTOINCREMENT``).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS itineraries (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER REFERENCES athletes(id) ON DELETE CASCADE,
                tenant_id INTEGER DEFAULT 0,
                name TEXT NOT NULL,
                description TEXT,
                start_date TEXT,
                end_date TEXT,
                total_km REAL DEFAULT 0,
                total_elevation_m REAL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stages (
                id SERIAL PRIMARY KEY,
                itinerary_id INTEGER NOT NULL REFERENCES itineraries(id) ON DELETE CASCADE,
                stage_day INTEGER DEFAULT 1,
                title TEXT,
                distance_km REAL,
                elevation_gain_m REAL,
                estimated_km REAL,
                estimated_elevation_m REAL,
                ride_id INTEGER REFERENCES rides(id) ON DELETE SET NULL,
                poi_id INTEGER REFERENCES pois(id) ON DELETE SET NULL,
                notes TEXT,
                tenant_id INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_stages_itinerary_pg ON stages(itinerary_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_stages_poi_pg ON stages(poi_id)")


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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def save_itinerary(itinerary: dict) -> int:
    """Create an itinerary in PostgreSQL. Returns the new row id."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        now = _now_iso()
        cols = [c for c in _ITINERARY_COLS if itinerary.get(c) is not None or c == "name"]
        vals = [itinerary.get(c) for c in cols]
        if "total_km" not in cols:
            cols.append("total_km")
            vals.append(itinerary.get("total_km", 0))
        if "total_elevation_m" not in cols:
            cols.append("total_elevation_m")
            vals.append(itinerary.get("total_elevation_m", 0))
        cols.extend(["created_at", "updated_at"])
        vals.extend([now, now])
        placeholders = ", ".join(["%s"] * len(vals))
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO itineraries ({', '.join(cols)}) VALUES ({placeholders}) RETURNING id",
                vals,
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        conn.close()


def get_itinerary(itinerary_id: int, tenant_id: int | None = None) -> dict | None:
    """Retrieve a single itinerary by id, optionally filtered by tenant."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM itineraries WHERE id=%s AND tenant_id=%s",
                    (itinerary_id, tenant_id),
                )
            else:
                cur.execute("SELECT * FROM itineraries WHERE id=%s", (itinerary_id,))
            return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def list_itineraries(
    athlete_id: int | None = None, tenant_id: int | None = None
) -> list[dict]:
    """Return all itineraries, optionally filtered by athlete or tenant."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if athlete_id is not None and tenant_id is not None:
                cur.execute(
                    "SELECT * FROM itineraries WHERE athlete_id=%s AND tenant_id=%s "
                    "ORDER BY id DESC",
                    (athlete_id, tenant_id),
                )
            elif athlete_id is not None:
                cur.execute(
                    "SELECT * FROM itineraries WHERE athlete_id=%s ORDER BY id DESC",
                    (athlete_id,),
                )
            elif tenant_id is not None:
                cur.execute(
                    "SELECT * FROM itineraries WHERE tenant_id=%s ORDER BY id DESC",
                    (tenant_id,),
                )
            else:
                cur.execute("SELECT * FROM itineraries ORDER BY id DESC")
            return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def save_stage(stage: dict) -> int:
    """Create a stage for an itinerary in PostgreSQL. Returns the new row id."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        now = _now_iso()
        cols = [c for c in _STAGE_COLS if stage.get(c) is not None]
        vals = [stage.get(c) for c in cols]
        # Always include stage_day default
        if "stage_day" not in cols:
            cols.append("stage_day")
            vals.append(stage.get("stage_day", 1))
        cols.extend(["created_at", "updated_at"])
        vals.extend([now, now])
        placeholders = ", ".join(["%s"] * len(vals))
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO stages ({', '.join(cols)}) VALUES ({placeholders}) RETURNING id",
                vals,
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        conn.close()


def list_stages(itinerary_id: int, tenant_id: int | None = None) -> list[dict]:
    """Return all stages for an itinerary, ordered by stage_day."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM stages WHERE itinerary_id=%s AND tenant_id=%s "
                    "ORDER BY stage_day ASC, id ASC",
                    (itinerary_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM stages WHERE itinerary_id=%s "
                    "ORDER BY stage_day ASC, id ASC",
                    (itinerary_id,),
                )
            return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_itinerary(itinerary_id: int, data: dict, tenant_id: int | None = None) -> bool:
    """Update an itinerary. Returns True if the row was modified."""
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
            updates.append(f"{col}=%s")
            vals.append(data[key])
    if not updates:
        return False
    updates.append("updated_at=%s")
    vals.append(_now_iso())

    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            where = "id=%s"
            params = [itinerary_id]
            if tenant_id is not None:
                where += " AND tenant_id=%s"
                params.append(tenant_id)
            vals.extend(params)
            cur.execute(
                f"UPDATE itineraries SET {', '.join(updates)} WHERE {where}",
                vals,
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def delete_itinerary(itinerary_id: int, tenant_id: int | None = None) -> bool:
    """Delete an itinerary. Returns True if the row was deleted."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "DELETE FROM itineraries WHERE id=%s AND tenant_id=%s",
                    (itinerary_id, tenant_id),
                )
            else:
                cur.execute("DELETE FROM itineraries WHERE id=%s", (itinerary_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def update_stage(stage_id: int, data: dict, tenant_id: int | None = None) -> bool:
    """Update a stage. Returns True if the row was modified."""
    field_map = {
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
            updates.append(f"{col}=%s")
            vals.append(data[key])
    if not updates:
        return False
    updates.append("updated_at=%s")
    vals.append(_now_iso())

    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            where = "id=%s"
            params = [stage_id]
            if tenant_id is not None:
                where += " AND tenant_id=%s"
                params.append(tenant_id)
            vals.extend(params)
            cur.execute(
                f"UPDATE stages SET {', '.join(updates)} WHERE {where}",
                vals,
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def delete_stage(stage_id: int, tenant_id: int | None = None) -> bool:
    """Delete a stage. Returns True if the row was deleted."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "DELETE FROM stages WHERE id=%s AND tenant_id=%s",
                    (stage_id, tenant_id),
                )
            else:
                cur.execute("DELETE FROM stages WHERE id=%s", (stage_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def reorder_stages(itinerary_id: int, stage_order: list[int], tenant_id: int | None = None) -> bool:
    """Reorder stages by updating stage_day values. Returns True on success."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        for day, stage_id in enumerate(stage_order, start=1):
            where = "id=%s AND itinerary_id=%s"
            params = [stage_id, itinerary_id]
            if tenant_id is not None:
                where += " AND tenant_id=%s"
                params.append(tenant_id)
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE stages SET stage_day=%s, updated_at=%s WHERE {where}",
                    (day, _now_iso(), *params),
                )
        conn.commit()
        return True
    finally:
        conn.close()
