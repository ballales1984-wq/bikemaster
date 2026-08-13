"""Athlete repository — SQLite persistence for athletes and athlete metrics."""

from __future__ import annotations

import sqlite3
import time
from datetime import UTC, datetime, timedelta

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


def _row_to_athlete(row) -> dict:
    """Convert an athlete SQLite row to a dict with safe defaults for missing columns."""
    if row is None:
        return None
    columns = [
        "id",
        "name",
        "email",
        "picture",
        "age",
        "weight_kg",
        "height_cm",
        "fat_percentage",
        "weekly_sessions",
        "monthly_hours",
        "annual_hours",
        "experience_level",
        "goals",
        "preferred_terrain",
        "weekly_volume_km",
        "best_segments",
        "medical_notes",
        "equipment",
        "ftp_watts",
        "body_water_percentage",
        "muscle_mass_percentage",
        "bmr_kcal",
        "fat_mass_kg",
        "subcutaneous_fat_kg",
        "subcutaneous_fat_percentage",
        "visceral_fat_level",
        "visceral_fat_percentage",
        "visceral_fat_kg",
        "muscle_mass_kg",
        "bone_mass_kg",
        "protein_percentage",
        "protein_kg",
        "body_age",
        "apparent_age",
        "bmi",
        "lean_body_mass_kg",
        "password_hash",
        "tenant_id",
        "created_at",
        "updated_at",
        "user_id",
    ]
    keys = row.keys()
    return {col: row[col] if col in keys else None for col in columns}


def get_athlete_by_name(name: str, tenant_id: int | None = None) -> dict | None:
    """Return the first athlete matching ``name``, optionally filtered by tenant."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM athletes WHERE name = ? AND tenant_id = ?", (name, tenant_id))
        else:
            cur.execute("SELECT * FROM athletes WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return _row_to_athlete(row)
        return None


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def get_athlete_by_email(email: str, tenant_id: int | None = None) -> dict | None:
    """Return the first athlete matching ``email``, optionally filtered by tenant."""

    try:
        with _get_db_connection() as conn:
            cur = conn.cursor()
            if tenant_id is not None:
                cur.execute("SELECT * FROM athletes WHERE email = ? AND tenant_id = ?", (email, tenant_id))
            else:
                cur.execute("SELECT * FROM athletes WHERE email = ?", (email,))
            row = cur.fetchone()
            if row:
                return _row_to_athlete(row)
            return None
    except Exception:
        return None


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def save_athlete(athlete: dict, athlete_id: int | None = None, tenant_id: int = 0, user_id: int | None = None) -> int:
    """Inserisce o aggiorna il profilo di un atleta.

    Se ``athlete_id`` e' fornito esegue un UPSERT (INSERT OR REPLACE)
    sovrascrivendo la riga esistente con lo stesso id. Altrimenti crea
    un nuovo atleta. Riprova fino a 5 volte su lock SQLite con backoff
    esponenziale. Restituisce l'id dell'atleta creato/aggiornato.
    """


    max_retries = 5
    retry_delay = 0.2
    last_error = None
    for attempt in range(max_retries):
        try:
            with _get_db_connection() as conn:
                cur = conn.cursor()
                base_cols = [
                    "name", "email", "picture", "age", "weight_kg", "height_cm", "fat_percentage",
                    "years_active", "weekly_sessions", "monthly_hours", "annual_hours",
                    "experience_level", "goals", "preferred_terrain", "weekly_volume_km",
                    "best_segments", "medical_notes", "equipment", "ftp_watts",
                    "body_water_percentage", "muscle_mass_percentage", "bmr_kcal",
                    "fat_mass_kg", "subcutaneous_fat_kg", "subcutaneous_fat_percentage",
                    "visceral_fat_level", "visceral_fat_percentage", "visceral_fat_kg",
                    "muscle_mass_kg", "bone_mass_kg", "protein_percentage", "protein_kg",
                    "body_age", "apparent_age", "password_hash", "tenant_id",
                    "created_at", "updated_at", "bmi", "lean_body_mass_kg",
                ]
                base_vals = [
                    athlete.get("name"), athlete.get("email"), athlete.get("picture"),
                    athlete.get("age"), athlete.get("weight_kg", 70), athlete.get("height_cm"),
                    athlete.get("fat_percentage"), athlete.get("years_active", 1),
                    athlete.get("weekly_sessions", 3), athlete.get("monthly_hours", 0),
                    athlete.get("annual_hours", 0), athlete.get("experience_level", "Beginner"),
                    athlete.get("goals"), athlete.get("preferred_terrain"),
                    athlete.get("weekly_volume_km", 0), athlete.get("best_segments"),
                    athlete.get("medical_notes"), athlete.get("equipment"), athlete.get("ftp_watts"),
                    athlete.get("body_water_percentage"), athlete.get("muscle_mass_percentage"),
                    athlete.get("bmr_kcal"), athlete.get("fat_mass_kg"),
                    athlete.get("subcutaneous_fat_kg"), athlete.get("subcutaneous_fat_percentage"),
                    athlete.get("visceral_fat_level"), athlete.get("visceral_fat_percentage"),
                    athlete.get("visceral_fat_kg"), athlete.get("muscle_mass_kg"),
                    athlete.get("bone_mass_kg"), athlete.get("protein_percentage"),
                    athlete.get("protein_kg"), athlete.get("body_age"), athlete.get("apparent_age"),
                    athlete.get("password_hash"), athlete.get("tenant_id", tenant_id),
                    datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat(),
                    athlete.get("bmi"), athlete.get("lean_body_mass_kg"),
                ]
                if athlete_id is None:
                    cols = list(base_cols)
                    vals = list(base_vals)
                    if user_id is not None:
                        cols.insert(0, "user_id")
                        vals.insert(0, user_id)
                    cur.execute(
                        f"INSERT INTO athletes ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})",
                        vals,
                    )
                else:
                    cols = ["id"] + base_cols
                    vals = [athlete_id] + base_vals
                    if user_id is not None:
                        cols.insert(1, "user_id")
                        vals.insert(1, user_id)
                    cur.execute(
                        f"INSERT OR REPLACE INTO athletes ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})",
                        vals,
                    )
                conn.commit()
                return cur.lastrowid
        except sqlite3.OperationalError as e:
            last_error = e
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to save athlete after retries")


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def get_athlete(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    """Recupera il profilo di un atleta per id, opzionalmente filtrato per tenant.

    Restituisce un dict con tutti i campi della tabella ``athletes`` oppure
    ``None`` se l'atleta non esiste o non appartiene al tenant.
    """

    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM athletes WHERE id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,))
        row = cur.fetchone()
        if row:
            return _row_to_athlete(row)
        return None


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def save_athlete_snapshot(athlete: dict, tenant_id: int = 0, changed_by: int | None = None, conn=None) -> int:
    """Insert a full snapshot of the athlete state into athlete_history.

    Returns the id of the created snapshot. Excludes password_hash for security.
    """

    cols = [
        "athlete_id", "tenant_id", "recorded_at", "changed_by", "name", "email",
        "picture", "age", "weight_kg", "height_cm", "fat_percentage",
        "years_active", "weekly_sessions", "monthly_hours", "annual_hours",
        "experience_level", "goals", "preferred_terrain", "weekly_volume_km",
        "best_segments", "medical_notes", "equipment", "ftp_watts",
        "body_water_percentage", "muscle_mass_percentage", "bmr_kcal",
        "fat_mass_kg", "subcutaneous_fat_kg", "subcutaneous_fat_percentage",
        "visceral_fat_level", "visceral_fat_percentage", "visceral_fat_kg",
        "muscle_mass_kg", "bone_mass_kg", "protein_percentage", "protein_kg",
        "body_age", "apparent_age", "bmi", "lean_body_mass_kg",
    ]
    vals = [
        athlete.get("id"),
        athlete.get("tenant_id", tenant_id),
        datetime.now(UTC).isoformat(),
        changed_by,
        athlete.get("name"),
        athlete.get("email"),
        athlete.get("picture"),
        athlete.get("age"),
        athlete.get("weight_kg"),
        athlete.get("height_cm"),
        athlete.get("fat_percentage"),
        athlete.get("years_active"),
        athlete.get("weekly_sessions"),
        athlete.get("monthly_hours"),
        athlete.get("annual_hours"),
        athlete.get("experience_level"),
        athlete.get("goals"),
        athlete.get("preferred_terrain"),
        athlete.get("weekly_volume_km"),
        athlete.get("best_segments"),
        athlete.get("medical_notes"),
        athlete.get("equipment"),
        athlete.get("ftp_watts"),
        athlete.get("body_water_percentage"),
        athlete.get("muscle_mass_percentage"),
        athlete.get("bmr_kcal"),
        athlete.get("fat_mass_kg"),
        athlete.get("subcutaneous_fat_kg"),
        athlete.get("subcutaneous_fat_percentage"),
        athlete.get("visceral_fat_level"),
        athlete.get("visceral_fat_percentage"),
        athlete.get("visceral_fat_kg"),
        athlete.get("muscle_mass_kg"),
        athlete.get("bone_mass_kg"),
        athlete.get("protein_percentage"),
        athlete.get("protein_kg"),
        athlete.get("body_age"),
        athlete.get("apparent_age"),
        athlete.get("bmi"),
        athlete.get("lean_body_mass_kg"),
    ]
    if conn is None:
        with _get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO athlete_history ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})",
                vals,
            )
            conn.commit()
            return cur.lastrowid
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO athlete_history ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})",
        vals,
    )
    return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def get_athlete_history(athlete_id: int, *, tenant_id: int | None = None, limit: int = 100) -> list[dict]:
    """Return the change history for an athlete, newest first."""

    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                """SELECT * FROM athlete_history WHERE athlete_id = ? AND tenant_id = ?
                   ORDER BY recorded_at DESC, id DESC LIMIT ?""",
                (athlete_id, tenant_id, limit),
            )
        else:
            cur.execute(
                """SELECT * FROM athlete_history WHERE athlete_id = ?
                   ORDER BY recorded_at DESC, id DESC LIMIT ?""",
                (athlete_id, limit),
            )
        rows = cur.fetchall()
        if not rows:
            return []
        columns = rows[0].keys()
        return [dict(zip(columns, row, strict=False)) for row in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def update_athlete(athlete_id: int, athlete_data: dict) -> bool:
    """Merge ``athlete_data`` into the existing athlete row. Returns True if updated."""

    existing = get_athlete(athlete_id)
    if not existing:
        return False
    merged = {**existing, **athlete_data}
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE athletes SET name=?, email=?, age=?, weight_kg=?,
            height_cm=?, fat_percentage=?, years_active=?, weekly_sessions=?,
            monthly_hours=?, annual_hours=?, experience_level=?, goals=?,
            preferred_terrain=?, weekly_volume_km=?, best_segments=?,
            medical_notes=?, equipment=?, ftp_watts=?, body_water_percentage=?,
            muscle_mass_percentage=?, bmr_kcal=?, fat_mass_kg=?, subcutaneous_fat_kg=?,
            subcutaneous_fat_percentage=?, visceral_fat_level=?, visceral_fat_percentage=?,
            visceral_fat_kg=?, muscle_mass_kg=?, bone_mass_kg=?, protein_percentage=?,
            protein_kg=?,
            body_age=?, apparent_age=?, bmi=?, lean_body_mass_kg=?,
            password_hash=?, tenant_id=?, updated_at=? WHERE id=? """,
            (
                merged.get("name"),
                merged.get("email"),
                merged.get("age", 30),
                merged.get("weight_kg", 70),
                merged.get("height_cm"),
                merged.get("fat_percentage"),
                merged.get("years_active", 1),
                merged.get("weekly_sessions", 3),
                merged.get("monthly_hours", 0),
                merged.get("annual_hours", 0),
                merged.get("experience_level", "Beginner"),
                merged.get("goals"),
                merged.get("preferred_terrain"),
                merged.get("weekly_volume_km", 0),
                merged.get("best_segments"),
                merged.get("medical_notes"),
                merged.get("equipment"),
                merged.get("ftp_watts"),
                merged.get("body_water_percentage"),
                merged.get("muscle_mass_percentage"),
                merged.get("bmr_kcal"),
                merged.get("fat_mass_kg"),
                merged.get("subcutaneous_fat_kg"),
                merged.get("subcutaneous_fat_percentage"),
                merged.get("visceral_fat_level"),
                merged.get("visceral_fat_percentage"),
                merged.get("visceral_fat_kg"),
                merged.get("muscle_mass_kg"),
                merged.get("bone_mass_kg"),
                merged.get("protein_percentage"),
                merged.get("protein_kg"),
                merged.get("body_age"),
                merged.get("apparent_age"),
                merged.get("bmi"),
                merged.get("lean_body_mass_kg"),
                merged.get("password_hash"),
                merged.get("tenant_id", athlete_id),
                now,
                athlete_id,
            ),
        )
        save_athlete_snapshot(existing, tenant_id=existing.get("tenant_id", athlete_id), changed_by=None, conn=conn)
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def get_athletes_by_user(user_id: int) -> list[dict]:
    """Restituisce tutti gli atleti di un utente ordinati per id."""

    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM athletes WHERE user_id = ? ORDER BY id", (user_id,))
        rows = cur.fetchall()
        return [_row_to_athlete(row) for row in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def get_athlete_count_by_user(user_id: int) -> int:

    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM athletes WHERE user_id = ?", (user_id,))
        return cur.fetchone()[0]


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def delete_athlete(athlete_id: int, user_id: int) -> bool:
    """Elimina un atleta se appartiene all'utente. Non elimina l'atleta principale se id==user_id."""

    if athlete_id == user_id:
        return False
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM athletes WHERE id = ? AND user_id = ?", (athlete_id, user_id))
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
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
    """Append a single metric sample to the athlete history (athlete_metric_log).

    ``recorded_at`` is stored as an ISO-8601 UTC timestamp so the same event
    can later be aggregated by day / month / second when drawing charts.
    """

    if value is None:
        return 0
    if not recorded_at:
        recorded_at = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO athlete_metric_log
               (athlete_id, tenant_id, metric_type, value, unit, note, source, recorded_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                athlete_id,
                tenant_id,
                metric_type,
                value,
                unit,
                note,
                source,
                recorded_at,
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def get_athlete_metric_log(
    athlete_id: int,
    metric_type: str,
    *,
    tenant_id: int | None = None,
    days: int = 365,
    limit: int = 2000,
) -> list[dict]:
    """Return the time series for one metric, oldest-first, for charting."""

    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, value, unit, note, source, recorded_at
               FROM athlete_metric_log
               WHERE athlete_id=? AND metric_type=?
                 AND (recorded_at IS NULL OR recorded_at >= ?)
               ORDER BY recorded_at ASC
               LIMIT ?""",
            (athlete_id, metric_type, since, limit),
        )
        rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "value": r[1],
            "unit": r[2],
            "note": r[3],
            "source": r[4],
            "recorded_at": r[5],
        }
        for r in rows
    ]


@pg_dispatch("bike_analyzer.backend.db.postgres_athlete")
def get_all_athletes() -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, experience_level FROM athletes")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "email": r[2], "experience_level": r[3]} for r in rows]
