"""PostgreSQL-backed persistence for rides, metrics and training-stress days.

When ``DATABASE_URL`` is configured (production on Render) the ``rides``,
``metrics`` and ``training_stress_days`` tables must live on the *managed*
PostgreSQL database, not on the ephemeral, container-local SQLite file. This
module is only ever invoked through the thin dispatch guards added at the top
of the ``database.py`` functions — mirroring the pattern already used by
``postgres_athlete.py`` for the athlete profile.

The public function names and return shapes mirror ``database.py`` 1:1 so the
two stores stay swap-compatible: a route calling ``save_ride`` / ``get_rides`` /
``upsert_training_stress_day`` ... gets identical behavior whether the active
store is SQLite (local / offline) or PostgreSQL (cloud / production).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from ..settings import get_settings

_s = get_settings()
logger = logging.getLogger(__name__)

# Reuse the connection / dispatch primitives defined once in postgres_athlete
# so there is a single source of truth for "is postgres configured" and for the
# psycopg2 connection factory.
from .postgres_athlete import _connect, has_postgres  # noqa: E402,F401


def _ensure_tables(conn) -> None:  # pragma: no cover - best-effort bootstrap
    """Best-effort ``CREATE TABLE IF NOT EXISTS`` fallback.

    On Render the tables are already created at startup by
    ``async_db.init_async_db`` (driven by the SQLAlchemy models in
    ``db/models.py``), so every statement here is a no-op. This only matters
    when the sync pg layer is used standalone (e.g. ad-hoc scripts / the
    integration test fixture that builds the schema directly).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rides (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER,
                tenant_id INTEGER DEFAULT 0,
                date TEXT NOT NULL,
                distance_km REAL DEFAULT 0,
                duration_minutes REAL DEFAULT 0,
                avg_speed_kmh REAL DEFAULT 0,
                weight_kg REAL DEFAULT 70,
                calories REAL DEFAULT 0,
                heart_rate_avg REAL,
                elevation_gain_m REAL,
                gps_points TEXT,
                external_source TEXT,
                external_id TEXT,
                title TEXT,
                activity_type TEXT DEFAULT 'ride',
                is_official BOOLEAN DEFAULT TRUE,
                source TEXT DEFAULT 'manual',
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER,
                ride_id INTEGER,
                fatigue_score REAL,
                recovery_hours REAL,
                calories_per_km REAL,
                efficiency_score REAL,
                created_at TEXT,
                tenant_id INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS training_stress_days (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                tss REAL,
                atl REAL,
                ctl REAL,
                tsb REAL,
                created_at TEXT,
                updated_at TEXT,
                tenant_id INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_rides_external_identity ON rides (external_source, external_id)"
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_training_stress_days ON training_stress_days (athlete_id, date)"
        )
    conn.commit()


_RIDE_COLS = [
    "athlete_id",
    "date",
    "distance_km",
    "duration_minutes",
    "avg_speed_kmh",
    "weight_kg",
    "calories",
    "heart_rate_avg",
    "elevation_gain_m",
    "gps_points",
    "external_source",
    "external_id",
    "title",
    "activity_type",
    "is_official",
    "source",
    "created_at",
    "tenant_id",
]


def _dict_from_row(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _ride_row_to_dict(row) -> dict | None:
    """Convert a PostgreSQL ``rides`` row into the same shape as
    ``database._row_to_ride`` (parses JSON GPS points, casts is_official)."""
    if row is None:
        return None
    try:
        gps = json.loads(row["gps_points"]) if row.get("gps_points") else None
    except (json.JSONDecodeError, TypeError):
        gps = None
    is_official = row.get("is_official")
    return {
        "id": row["id"],
        "athlete_id": row["athlete_id"],
        "date": row["date"],
        "distance_km": row["distance_km"],
        "duration_minutes": row["duration_minutes"],
        "avg_speed_kmh": row["avg_speed_kmh"],
        "weight_kg": row["weight_kg"],
        "calories": row["calories"],
        "heart_rate_avg": row["heart_rate_avg"],
        "elevation_gain_m": row["elevation_gain_m"],
        "gps_points": gps,
        "created_at": row["created_at"],
        "external_source": row.get("external_source"),
        "external_id": row.get("external_id"),
        "title": row.get("title"),
        "tenant_id": row.get("tenant_id") or 0,
        "activity_type": row.get("activity_type") or "ride",
        "is_official": bool(is_official) if is_official is not None else True,
        "source": row.get("source") or "manual",
    }


def _find_existing_external_ride(conn, external_source: str | None, external_id: str | None) -> int | None:
    """Return the ride id for a given external source/id pair, or None."""
    if not external_source or not external_id:
        return None
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM rides WHERE external_source = %s AND external_id = %s LIMIT 1",
            (external_source, external_id),
        )
        row = cur.fetchone()
    return int(row["id"]) if row else None


def save_ride(ride: dict) -> int:
    """Insert a new ride on PostgreSQL, mirroring ``database.save_ride``.

    * Deduplicates by ``external_source`` + ``external_id`` (returns the existing
      id when the activity was already imported).
    * Estimates calories via ``ensure_calories`` when missing, exactly like the
      SQLite implementation so the two stores stay swap-compatible.
    * Serializes GPS points as JSON.
    * Uses ``RETURNING id`` (PostgreSQL equivalent of SQLite ``lastrowid``).
    """
    external_source = str(ride.get("external_source") or "").strip() or None
    external_id = str(ride.get("external_id") or "").strip() or None
    if not ride.get("calories"):
        try:
            from ..analytics.calories import ensure_calories
            from ..models.models import Ride

            allowed = set(Ride.__dataclass_fields__.keys())
            clean = {k: v for k, v in ride.items() if k in allowed and k not in ("gps_points", "id")}
            ride["calories"] = ensure_calories(Ride(**clean))
        except Exception as exc:
            logger.warning("Calorie estimate failed for ride %s: %s", ride.get("id"), exc)
    gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
    tenant_id = ride.get("tenant_id", ride.get("athlete_id", 0))
    now = datetime.now(UTC).isoformat()
    params = [
        ride.get("athlete_id"),
        ride.get("date"),
        ride.get("distance_km", 0),
        ride.get("duration_minutes", 0),
        ride.get("avg_speed_kmh", 0),
        ride.get("weight_kg", 70),
        ride.get("calories", 0),
        ride.get("heart_rate_avg"),
        ride.get("elevation_gain_m"),
        gps_points,
        external_source,
        external_id,
        ride.get("title"),
        ride.get("activity_type", "ride"),
        bool(ride.get("is_official", True)),
        ride.get("source", "manual"),
        now,
        tenant_id,
    ]
    placeholders = ", ".join(["%s"] * len(params))
    conn = _connect()
    try:
        _ensure_tables(conn)
        existing = _find_existing_external_ride(conn, external_source, external_id)
        if existing is not None:
            return existing
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO rides ({', '.join(_RIDE_COLS)}) VALUES ({placeholders}) RETURNING id",
                params,
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        conn.close()


def get_ride(ride_id: int, tenant_id: int | None = None) -> dict | None:
    """Recupera una singola attivita' per id, opzionalmente filtrata per tenant."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute("SELECT * FROM rides WHERE id = %s AND tenant_id = %s", (ride_id, tenant_id))
            else:
                cur.execute("SELECT * FROM rides WHERE id = %s", (ride_id,))
            return _ride_row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_rides_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    """Restituisce tutte le attivita' di un atleta, opzionalmente filtrate per tenant (oldest-first)."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM rides WHERE athlete_id = %s AND tenant_id = %s ORDER BY date ASC, id ASC",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM rides WHERE athlete_id = %s ORDER BY date ASC, id ASC",
                    (athlete_id,),
                )
            return [_ride_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_all_rides(athlete_id: int | None = None, tenant_id: int | None = None) -> list[dict]:
    """Return rides filtered by athlete and/or tenant, or all rides if none provided."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if athlete_id is not None and tenant_id is not None:
                cur.execute(
                    "SELECT * FROM rides WHERE athlete_id = %s AND tenant_id = %s ORDER BY date ASC, id ASC",
                    (athlete_id, tenant_id),
                )
            elif athlete_id is not None:
                cur.execute("SELECT * FROM rides WHERE athlete_id = %s ORDER BY date ASC, id ASC", (athlete_id,))
            elif tenant_id is not None:
                cur.execute("SELECT * FROM rides WHERE tenant_id = %s ORDER BY date ASC, id ASC", (tenant_id,))
            else:
                cur.execute("SELECT * FROM rides ORDER BY date ASC, id ASC")
            return [_ride_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def delete_ride(ride_id: int, tenant_id: int | None = None) -> bool:
    """Delete a ride by id, optionally scoped to a tenant. Returns True if deleted."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute("DELETE FROM rides WHERE id = %s AND tenant_id = %s", (ride_id, tenant_id))
            else:
                cur.execute("DELETE FROM rides WHERE id = %s", (ride_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def update_ride(ride_id: int, ride: dict, tenant_id: int | None = None) -> bool:
    """Partially update an existing ride (PATCH semantics).

    Only the columns present in ``ride`` are written, so a NOT-NULL column (e.g.
    ``date``) is never clobbered with NULL when the caller passes a subset of
    fields. Returns True if a row was modified.
    """
    cols = [c for c in _RIDE_COLS if c in ride and c != "id"]
    if not cols:
        return False
    assignments = []
    params = []
    for c in cols:
        val = ride.get(c)
        if c == "gps_points":
            val = json.dumps(val) if val else None
        elif c == "is_official":
            val = bool(val)
        elif c == "activity_type":
            val = val or "ride"
        elif c == "source":
            val = val or "manual"
        assignments.append(f"{c} = %s")
        params.append(val)
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                params += [ride_id, tenant_id]
                cur.execute(
                    f"UPDATE rides SET {', '.join(assignments)} WHERE id = %s AND tenant_id = %s",
                    params,
                )
            else:
                params.append(ride_id)
                cur.execute(
                    f"UPDATE rides SET {', '.join(assignments)} WHERE id = %s",
                    params,
                )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def save_metric(metric: dict, tenant_id: int = 0) -> int:
    """Insert a metrics row (fatigue, recovery, calories, efficiency) for a ride."""
    now = datetime.now(UTC).isoformat()
    params = [
        metric.get("athlete_id"),
        metric.get("ride_id"),
        metric.get("fatigue_score"),
        metric.get("recovery_hours"),
        metric.get("calories_per_km"),
        metric.get("efficiency_score"),
        now,
        metric.get("tenant_id", tenant_id),
    ]
    cols = (
        "athlete_id, ride_id, fatigue_score, recovery_hours, calories_per_km, efficiency_score, created_at, tenant_id"
    )
    placeholders = ", ".join(["%s"] * len(params))
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(f"INSERT INTO metrics ({cols}) VALUES ({placeholders}) RETURNING id", params)
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        conn.close()


def upsert_training_stress_day(
    athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float, tenant_id: int = 0
) -> None:
    now = datetime.now(UTC).isoformat()
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO training_stress_days
                (athlete_id, date, tss, atl, ctl, tsb, created_at, updated_at, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id, date) DO UPDATE SET
                    tss=excluded.tss, atl=excluded.atl, ctl=excluded.ctl,
                    tsb=excluded.tsb, updated_at=excluded.updated_at,
                    tenant_id=excluded.tenant_id""",
                (athlete_id, date, tss, atl, ctl, tsb, now, now, tenant_id),
            )
            conn.commit()
    finally:
        conn.close()


def get_training_stress_days(athlete_id: int, limit: int = 90, tenant_id: int | None = None) -> list[dict]:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT date, tss, atl, ctl, tsb "
                    "FROM training_stress_days WHERE athlete_id = %s AND tenant_id = %s "
                    "ORDER BY date DESC LIMIT %s",
                    (athlete_id, tenant_id, limit),
                )
            else:
                cur.execute(
                    "SELECT date, tss, atl, ctl, tsb "
                    "FROM training_stress_days WHERE athlete_id = %s "
                    "ORDER BY date DESC LIMIT %s",
                    (athlete_id, limit),
                )
            return [
                {"date": r["date"], "tss": r["tss"], "atl": r["atl"], "ctl": r["ctl"], "tsb": r["tsb"]}
                for r in cur.fetchall()
            ]
    finally:
        conn.close()


def get_latest_training_stress(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT date, tss, atl, ctl, tsb "
                    "FROM training_stress_days WHERE athlete_id = %s AND tenant_id = %s "
                    "ORDER BY date DESC LIMIT 1",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT date, tss, atl, ctl, tsb "
                    "FROM training_stress_days WHERE athlete_id = %s "
                    "ORDER BY date DESC LIMIT 1",
                    (athlete_id,),
                )
            row = cur.fetchone()
            if row:
                return {"date": row["date"], "tss": row["tss"], "atl": row["atl"], "ctl": row["ctl"], "tsb": row["tsb"]}
            return None
    finally:
        conn.close()


def get_metrics_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    """Return all metrics rows for an athlete, optionally filtered by tenant."""
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM metrics WHERE athlete_id = %s AND tenant_id = %s ORDER BY created_at ASC",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM metrics WHERE athlete_id = %s ORDER BY created_at ASC",
                    (athlete_id,),
                )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


__all__ = [
    "has_postgres",
    "save_ride",
    "get_ride",
    "get_rides_by_athlete",
    "get_all_rides",
    "delete_ride",
    "update_ride",
    "save_metric",
    "get_metrics_by_athlete",
    "upsert_training_stress_day",
    "get_training_stress_days",
    "get_latest_training_stress",
]
