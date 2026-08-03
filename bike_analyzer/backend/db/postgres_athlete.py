"""PostgreSQL-backed persistence for the athlete profile + metric log.

When ``DATABASE_URL`` is configured (production on Render) the athlete
profile (including ``weight_kg``) and its history/log must live on the *managed*
PostgreSQL database, not on the ephemeral, container-local SQLite file. On
SQLite (local / offline) the synchronous layer in ``database.py`` is still the
authoritative store; this module is only ever invoked through the thin dispatch
guards added at the top of the ``database.py`` functions.

The public function names mirror ``database.py`` 1:1 so the routes keep
importing the same symbols. All column sets, defaults and return shapes are
deliberately aligned with the SQLite implementation so the two stores stay
swap-compatible.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from ..settings import get_settings

_s = get_settings()


def _url() -> str:
    return (os.environ.get("DATABASE_URL") or _s.database_url or "").strip()


def has_postgres() -> bool:
    return bool(_url())


def _connect():
    """Open a real psycopg2 connection to the managed PostgreSQL backend.

    The schema (``athletes`` / ``athlete_metric_log`` / ``athlete_history``) is
    owned by the async SQLAlchemy layer in ``async_db.py`` (created from
    ``db/models.py`` at startup via ``init_async_db``), so this module only
    issues data statements against tables that already exist.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor

    return psycopg2.connect(_url(), cursor_factory=RealDictCursor)


def _ensure_tables(conn) -> None:  # pragma: no cover - kept for standalone bootstrap
    """Best-effort ``CREATE TABLE IF NOT EXISTS`` fallback.

    Only meaningful when the sync pg layer is used *without* the async
    SQLAlchemy bootstrap (e.g. ad-hoc scripts); on Render the tables are already
    created by ``async_db.init_async_db`` so every statement here is a no-op.
    Uses PostgreSQL-native ``SERIAL`` (never SQLite ``AUTOINCREMENT``).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS athletes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                name TEXT NOT NULL,
                email TEXT,
                picture TEXT,
                age INTEGER DEFAULT 30,
                weight_kg REAL DEFAULT 70,
                height_cm REAL,
                fat_percentage REAL,
                years_active INTEGER DEFAULT 1,
                weekly_sessions INTEGER DEFAULT 3,
                monthly_hours REAL DEFAULT 0,
                annual_hours REAL DEFAULT 0,
                experience_level TEXT DEFAULT 'Beginner',
                goals TEXT,
                preferred_terrain TEXT,
                weekly_volume_km REAL DEFAULT 0,
                best_segments TEXT,
                medical_notes TEXT,
                equipment TEXT,
                ftp_watts REAL,
                body_water_percentage REAL,
                muscle_mass_percentage REAL,
                bmr_kcal REAL,
                fat_mass_kg REAL,
                subcutaneous_fat_kg REAL,
                subcutaneous_fat_percentage REAL,
                visceral_fat_level REAL,
                visceral_fat_percentage REAL,
                visceral_fat_kg REAL,
                muscle_mass_kg REAL,
                bone_mass_kg REAL,
                protein_percentage REAL,
                protein_kg REAL,
                body_age INTEGER,
                apparent_age INTEGER,
                bmi REAL,
                lean_body_mass_kg REAL,
                password_hash TEXT,
                tenant_id INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS athlete_metric_log (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER,
                tenant_id INTEGER DEFAULT 0,
                metric_type TEXT NOT NULL,
                value REAL,
                unit TEXT,
                note TEXT,
                source TEXT DEFAULT 'manual',
                recorded_at TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS athlete_history (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                recorded_at TEXT,
                changed_by INTEGER,
                name TEXT, email TEXT, picture TEXT,
                age INTEGER,
                weight_kg REAL,
                height_cm REAL,
                fat_percentage REAL,
                years_active INTEGER,
                weekly_sessions INTEGER,
                monthly_hours REAL,
                annual_hours REAL,
                experience_level TEXT,
                goals TEXT,
                preferred_terrain TEXT,
                weekly_volume_km REAL,
                best_segments TEXT,
                medical_notes TEXT,
                equipment TEXT,
                ftp_watts REAL,
                body_water_percentage REAL,
                muscle_mass_percentage REAL,
                bmr_kcal REAL,
                fat_mass_kg REAL,
                subcutaneous_fat_kg REAL,
                subcutaneous_fat_percentage REAL,
                visceral_fat_level REAL,
                visceral_fat_percentage REAL,
                visceral_fat_kg REAL,
                muscle_mass_kg REAL,
                bone_mass_kg REAL,
                protein_percentage REAL,
                protein_kg REAL,
                body_age INTEGER,
                apparent_age INTEGER
            )
            """
        )
    conn.commit()


# Ordered column sets, kept in sync with db/database.py sqlite definitions.
_INSERT_COLS = [
    "name", "email", "picture", "age", "weight_kg", "height_cm", "fat_percentage",
    "years_active", "weekly_sessions", "monthly_hours", "annual_hours",
    "experience_level", "goals", "preferred_terrain", "weekly_volume_km",
    "best_segments", "medical_notes", "equipment", "ftp_watts",
    "body_water_percentage", "muscle_mass_percentage", "bmr_kcal", "fat_mass_kg",
    "subcutaneous_fat_kg", "subcutaneous_fat_percentage", "visceral_fat_level",
    "visceral_fat_percentage", "visceral_fat_kg", "muscle_mass_kg", "bone_mass_kg",
    "protein_percentage", "protein_kg", "body_age", "apparent_age", "bmi",
    "lean_body_mass_kg", "password_hash", "tenant_id", "created_at", "updated_at",
]

_INSERT_DEFAULTS = {
    "age": 30, "weight_kg": 70.0, "years_active": 1, "weekly_sessions": 3,
    "monthly_hours": 0, "annual_hours": 0, "experience_level": "Beginner",
    "weekly_volume_km": 0,
}

# UPDATE column set mirrors update_athlete() (no picture/created_at).
_UPDATE_COLS = [
    "name", "email", "age", "weight_kg", "height_cm", "fat_percentage",
    "years_active", "weekly_sessions", "monthly_hours", "annual_hours",
    "experience_level", "goals", "preferred_terrain", "weekly_volume_km",
    "best_segments", "medical_notes", "equipment", "ftp_watts",
    "body_water_percentage", "muscle_mass_percentage", "bmr_kcal", "fat_mass_kg",
    "subcutaneous_fat_kg", "subcutaneous_fat_percentage", "visceral_fat_level",
    "visceral_fat_percentage", "visceral_fat_kg", "muscle_mass_kg", "bone_mass_kg",
    "protein_percentage", "protein_kg", "body_age", "apparent_age", "bmi",
    "lean_body_mass_kg", "password_hash", "tenant_id", "updated_at",
]

_UPDATE_DEFAULTS = {
    "age": 30, "weight_kg": 70, "years_active": 1, "weekly_sessions": 3,
    "monthly_hours": 0, "annual_hours": 0, "experience_level": "Beginner",
    "weekly_volume_km": 0,
}

_SNAPSHOT_COLS = [
    "athlete_id", "tenant_id", "recorded_at", "changed_by", "name", "email",
    "picture", "age", "weight_kg", "height_cm", "fat_percentage", "years_active",
    "weekly_sessions", "monthly_hours", "annual_hours", "experience_level",
    "goals", "preferred_terrain", "weekly_volume_km", "best_segments",
    "medical_notes", "equipment", "ftp_watts", "body_water_percentage",
    "muscle_mass_percentage", "bmr_kcal", "fat_mass_kg", "subcutaneous_fat_kg",
    "subcutaneous_fat_percentage", "visceral_fat_level", "visceral_fat_percentage",
    "visceral_fat_kg", "muscle_mass_kg", "bone_mass_kg", "protein_percentage",
    "protein_kg", "body_age", "apparent_age",
]

_LOG_COLS = ["athlete_id", "tenant_id", "metric_type", "value", "unit",
             "note", "source", "recorded_at", "created_at"]


def _dict_from_row(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


def get_athlete(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM athletes WHERE id=%s AND tenant_id=%s",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute("SELECT * FROM athletes WHERE id=%s", (athlete_id,))
            return _dict_from_row(cur.fetchone())
    finally:
        conn.close()


def get_athlete_by_email(email: str, tenant_id: int | None = None) -> dict | None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM athletes WHERE email=%s AND tenant_id=%s",
                    (email, tenant_id),
                )
            else:
                cur.execute("SELECT * FROM athletes WHERE email=%s", (email,))
            return _dict_from_row(cur.fetchone())
    finally:
        conn.close()


def save_athlete(
    athlete: dict,
    athlete_id: int | None = None,
    tenant_id: int = 0,
    user_id: int | None = None,
) -> int:
    now = datetime.now(UTC).isoformat()
    # Apply defaults per-column to mirror db/database.py sqlite save_athlete.
    vals = []
    for c in _INSERT_COLS:
        if c in ("created_at", "updated_at"):
            vals.append(now)
        elif c == "tenant_id":
            vals.append(athlete.get("tenant_id", tenant_id))
        else:
            vals.append(athlete.get(c, _INSERT_DEFAULTS.get(c)))

    conn = _connect()
    try:
        with conn.cursor() as cur:
            existing = get_athlete(athlete_id) if athlete_id is not None else None
            if existing:
                # UPSERT: row exists -> UPDATE in place, preserving existing fields.
                merged = {**existing, **athlete}
                _do_update(cur, athlete_id, merged, now)
                conn.commit()
                return athlete_id
            cols = list(_INSERT_COLS)
            params: list[Any] = list(vals)
            if athlete_id is not None:
                cols.insert(0, "id")
                params.insert(0, athlete_id)
            if user_id is not None:
                cols.insert(1 if athlete_id is not None else 0, "user_id")
                params.insert(1 if athlete_id is not None else 0, user_id)
            placeholders = ", ".join(["%s"] * len(params))
            cur.execute(
                f"INSERT INTO athletes ({', '.join(cols)}) VALUES ({placeholders}) "
                "RETURNING id",
                params,
            )
            row = cur.fetchone()
            conn.commit()
            return athlete_id if athlete_id is not None else int(row["id"])
    finally:
        conn.close()


def _do_update(cur, athlete_id: int, merged: dict, now: str) -> None:
    params = [merged.get(c, _UPDATE_DEFAULTS.get(c)) for c in _UPDATE_COLS]
    params[-2] = merged.get("tenant_id", athlete_id)  # tenant_id
    params[-1] = now  # updated_at
    params.append(athlete_id)
    cols = list(_UPDATE_COLS)
    set_clause = ", ".join(f"{c}=%s" for c in cols)
    cur.execute(
        f"UPDATE athletes SET {set_clause} WHERE id=%s",
        params,
    )


def update_athlete(athlete_id: int, athlete_data: dict) -> bool:
    existing = get_athlete(athlete_id)
    if not existing:
        return False
    merged = {**existing, **athlete_data}
    now = datetime.now(UTC).isoformat()
    conn = _connect()
    try:
        with conn.cursor() as cur:
            params = [merged.get(c, _UPDATE_DEFAULTS.get(c)) for c in _UPDATE_COLS]
            params[-2] = merged.get("tenant_id", athlete_id)  # tenant_id
            params[-1] = now  # updated_at
            params.append(athlete_id)
            cols = list(_UPDATE_COLS)
            set_clause = ", ".join(f"{c}=%s" for c in cols)
            cur.execute(
                f"UPDATE athletes SET {set_clause} WHERE id=%s",
                params,
            )
            rowcount = cur.rowcount
        save_athlete_snapshot(existing, tenant_id=existing.get("tenant_id", athlete_id), changed_by=None)
        return rowcount > 0
    finally:
        conn.close()


def log_athlete_metric(
    athlete_id: int,
    metric_type: str,
    value: float | None,
    *,
    tenant_id: int = 0,
    unit: str | None = None,
    note: str | None = None,
    source: str = "manual",
    recorded_at: str | None = None,
) -> int:
    if value is None:
        return 0
    if not recorded_at:
        recorded_at = datetime.now(UTC).isoformat()
    now = datetime.now(UTC).isoformat()
    params = [
        athlete_id,
        tenant_id,
        metric_type,
        value,
        unit,
        note,
        source,
        recorded_at,
        now,
    ]
    cols = ", ".join(_LOG_COLS)
    placeholders = ", ".join(["%s"] * len(params))
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO athlete_metric_log ({cols}) VALUES ({placeholders}) RETURNING id",
                params,
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        conn.close()


def get_athlete_metric_log(
    athlete_id: int,
    metric_type: str,
    *,
    tenant_id: int | None = None,
    days: int = 365,
    limit: int = 2000,
) -> list[dict]:
    from datetime import timedelta

    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, value, unit, note, source, recorded_at
                   FROM athlete_metric_log
                   WHERE athlete_id=%s AND metric_type=%s
                     AND (recorded_at IS NULL OR recorded_at >= %s)
                   ORDER BY recorded_at ASC LIMIT %s""",
                (athlete_id, metric_type, since, limit),
            )
            return [_dict_from_row(r) for r in cur.fetchall()]
    finally:
        conn.close()


def save_athlete_snapshot(
    athlete: dict,
    tenant_id: int = 0,
    changed_by: int | None = None,
    conn=None,
) -> int:
    now = datetime.now(UTC).isoformat()
    params = [
        athlete.get("id"),
        athlete.get("tenant_id", tenant_id),
        now,
        changed_by,
    ]
    for c in _SNAPSHOT_COLS[4:]:
        params.append(athlete.get(c))
    cols = ", ".join(_SNAPSHOT_COLS)
    placeholders = ", ".join(["%s"] * len(params))

    own_conn = conn is None
    if own_conn:
        conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO athlete_history ({cols}) VALUES ({placeholders}) RETURNING id",
                params,
            )
            row = cur.fetchone()
            if own_conn:
                conn.commit()
            return int(row["id"]) if row else 0
    finally:
        if own_conn:
            conn.close()


def get_athlete_history(
    athlete_id: int, *, tenant_id: int | None = None, limit: int = 100
) -> list[dict]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM athlete_history WHERE athlete_id=%s AND tenant_id=%s "
                    "ORDER BY recorded_at DESC, id DESC LIMIT %s",
                    (athlete_id, tenant_id, limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM athlete_history WHERE athlete_id=%s "
                    "ORDER BY recorded_at DESC, id DESC LIMIT %s",
                    (athlete_id, limit),
                )
            return [_dict_from_row(r) for r in cur.fetchall()]
    finally:
        conn.close()
