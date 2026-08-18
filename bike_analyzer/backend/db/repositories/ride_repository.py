"""Ride repository — SQLite persistence for rides."""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


def _row_to_ride(row) -> dict:
    """Convert a SQLite ``rides`` row into a plain dict, parsing JSON GPS points."""
    try:
        gps = json.loads(row["gps_points"]) if row["gps_points"] else None
    except (json.JSONDecodeError, TypeError):
        gps = None
    keys = row.keys()
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
        "external_source": row["external_source"] if "external_source" in keys else None,
        "external_id": row["external_id"] if "external_id" in keys else None,
        "title": row["title"] if "title" in keys else None,
        "tenant_id": row["tenant_id"] if "tenant_id" in keys else 0,
        "activity_type": row["activity_type"] if "activity_type" in keys else "ride",
        "is_official": bool(row["is_official"]) if "is_official" in keys else True,
        "source": row["source"] if "source" in keys else "manual",
    }


def _find_existing_external_ride(conn, external_source: str | None, external_id: str | None) -> int | None:
    """Return the local ride id for a given external source/id pair, or None."""
    if not external_source or not external_id:
        return None
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM rides WHERE external_source = ? AND external_id = ? LIMIT 1",
        (str(external_source), str(external_id)),
    )
    row = cur.fetchone()
    return int(row["id"]) if row else None


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def save_ride(ride: dict) -> int:
    """Inserisce una nuova attivita' (ride) nel database.

    Effettua la deduplicazione automatica per sorgenti esterne (Strava,
    Garmin, ecc.) confrontando ``external_source`` + ``external_id``. Se
    l'attivita' esiste gia', restituisce l'id esistente senza inserire
    duplicati.

    Stima automaticamente le calorie se mancanti tramite ``ensure_calories``
    e serializza i punti GPS come JSON. Riprova fino a 5 volte in caso di
    lock SQLite con backoff esponenziale.
    """


    max_retries = 5
    retry_delay = 0.2
    last_error = None
    for attempt in range(max_retries):
        try:
            with _get_db_connection() as conn:
                cur = conn.cursor()
                external_source = str(ride.get("external_source") or "").strip() or None
                external_id = str(ride.get("external_id") or "").strip() or None
                existing_ride_id = _find_existing_external_ride(conn, external_source, external_id)
                if existing_ride_id is not None:
                    return existing_ride_id
                gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
                tenant_id = ride.get("tenant_id", ride.get("athlete_id", 0))
                cur.execute(
                    """INSERT INTO rides
                    (athlete_id, date, distance_km, duration_minutes, avg_speed_kmh,
                     weight_kg, calories, heart_rate_avg, elevation_gain_m, gps_points,
                     external_source, external_id, title, activity_type, is_official,
                     source, created_at, tenant_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
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
                        1 if ride.get("is_official", True) else 0,
                        ride.get("source", "manual"),
                        datetime.now(UTC).isoformat(),
                        tenant_id,
                    ),
                )
                conn.commit()
                return cur.lastrowid
        except sqlite3.OperationalError as e:
            last_error = e
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise
        except sqlite3.IntegrityError:
            existing_ride_id = _find_existing_external_ride(conn, external_source, external_id)
            if existing_ride_id is not None:
                return existing_ride_id
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to save ride after retries")


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def get_ride(ride_id: int, tenant_id: int | None = None) -> dict | None:
    """Recupera una singola attivita' per id, opzionalmente filtrata per tenant.

    Restituisce un dict con tutti i campi della tabella ``rides`` oppure
    ``None`` se l'attivita' non esiste o non appartiene al tenant.
    """

    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE id = ? AND tenant_id = ?", (ride_id, tenant_id))
        else:
            cur.execute("SELECT * FROM rides WHERE id = ?", (ride_id,))
        row = cur.fetchone()
        if row:
            return _row_to_ride(row)
        return None


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def get_rides_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    """Restituisce tutte le attivita' di un atleta, opzionalmente filtrate per tenant.

    I risultati sono ordinati per id crescente (dal piu' vecchio al piu'
    recente). Usa ``_row_to_ride`` per deserializzare i punti GPS da JSON.
    """

    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ?", (athlete_id,))
        rows = cur.fetchall()
        return [_row_to_ride(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def get_all_rides(athlete_id: int | None = None, tenant_id: int | None = None) -> list[dict]:
    """Return rides filtered by athlete and/or tenant, or all rides if none provided."""

    with _get_db_connection() as conn:
        cur = conn.cursor()
        if athlete_id is not None and tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        elif athlete_id is not None:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ?", (athlete_id,))
        elif tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE tenant_id = ?", (tenant_id,))
        else:
            cur.execute("SELECT * FROM rides")
        rows = cur.fetchall()
        return [_row_to_ride(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def delete_ride(ride_id: int, tenant_id: int | None = None) -> bool:
    """Delete a ride by id, optionally scoped to a tenant. Returns True if deleted."""

    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("DELETE FROM rides WHERE id = ? AND tenant_id = ?", (ride_id, tenant_id))
        else:
            cur.execute("DELETE FROM rides WHERE id = ?", (ride_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def update_ride(ride_id: int, ride: dict, tenant_id: int | None = None) -> bool:
    """Partially update an existing ride (PATCH semantics).

    Only the columns present in ``ride`` are written, so a NOT-NULL column (e.g.
    ``date``) is never clobbered with NULL when the caller passes a subset of
    fields. Returns True if a row was modified.
    """

    cols = [
        c
        for c in (
            "athlete_id", "date", "distance_km", "duration_minutes", "avg_speed_kmh",
            "weight_kg", "calories", "heart_rate_avg", "elevation_gain_m",
            "gps_points", "external_source", "external_id", "title", "activity_type",
            "is_official", "source", "created_at", "tenant_id",
        )
        if c in ride and c != "id"
    ]
    if not cols:
        return False
    assignments = []
    params = []
    for c in cols:
        val = ride.get(c)
        if c == "gps_points":
            val = json.dumps(val) if val else None
        elif c == "is_official":
            val = 1 if val else 0
        elif c == "activity_type":
            val = val or "ride"
        elif c == "source":
            val = val or "manual"
        assignments.append(f"{c} = ?")
        params.append(val)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            params += [ride_id, tenant_id]
            cur.execute(f"UPDATE rides SET {', '.join(assignments)} WHERE id = ? AND tenant_id = ?", params)
        else:
            params.append(ride_id)
            cur.execute(f"UPDATE rides SET {', '.join(assignments)} WHERE id = ?", params)
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def save_metric(metric: dict, tenant_id: int = 0) -> int:
    """Insert a metrics row (fatigue, recovery, calories, efficiency) for a ride."""
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO metrics
            (athlete_id, ride_id, fatigue_score, recovery_hours,
             calories_per_km, efficiency_score, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                metric.get("athlete_id"),
                metric.get("ride_id"),
                metric.get("fatigue_score"),
                metric.get("recovery_hours"),
                metric.get("calories_per_km"),
                metric.get("efficiency_score"),
                now,
                metric.get("tenant_id", tenant_id),
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def get_metrics_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM metrics WHERE athlete_id = ? AND tenant_id = ? ORDER BY created_at ASC",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM metrics WHERE athlete_id = ? ORDER BY created_at ASC",
                (athlete_id,),
            )
        rows = cur.fetchall()
    return [dict(r) for r in rows]
