"""PostgreSQL-backed persistence for metabolic data."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_metabolic_profiles_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metabolic_profiles (
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                sex TEXT NOT NULL DEFAULT 'male',
                bmr_formula TEXT NOT NULL DEFAULT 'mifflin',
                activity_level TEXT NOT NULL DEFAULT 'moderate',
                bmr_kcal REAL,
                tdee_kcal REAL,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT NOW(),
                updated_at TEXT NOT NULL DEFAULT NOW(),
                PRIMARY KEY(athlete_id)
            )
            """
        )
        conn.commit()


def _ensure_food_logs_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS food_logs (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                date TEXT NOT NULL,
                meal_type TEXT NOT NULL DEFAULT 'other',
                description TEXT NOT NULL DEFAULT '',
                kcal REAL DEFAULT 0,
                carbs_g REAL,
                protein_g REAL,
                fat_g REAL,
                fiber_g REAL,
                water_ml REAL,
                note TEXT,
                recorded_at TEXT NOT NULL DEFAULT NOW(),
                created_at TEXT NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.commit()


def _ensure_metabolic_daily_summaries_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metabolic_daily_summaries (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                date TEXT NOT NULL,
                bmr_kcal REAL,
                tdee_kcal REAL,
                intake_kcal REAL DEFAULT 0,
                expenditure_kcal REAL DEFAULT 0,
                balance_kcal REAL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT NOW(),
                updated_at TEXT NOT NULL DEFAULT NOW(),
                UNIQUE(athlete_id, date)
            )
            """
        )
        conn.commit()


def _ensure_metabolic_reference_values_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metabolic_reference_values (
                id SERIAL PRIMARY KEY,
                sex TEXT NOT NULL,
                age_lo INTEGER NOT NULL,
                age_hi INTEGER NOT NULL,
                weight_lo REAL NOT NULL,
                weight_hi REAL NOT NULL,
                activity_level TEXT NOT NULL,
                bmr_kcal REAL NOT NULL,
                tdee_kcal REAL NOT NULL,
                source TEXT NOT NULL DEFAULT 'builtin',
                tenant_id INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.commit()


def _ensure_metabolic_adaptive_weights_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metabolic_adaptive_weights (
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                weights JSONB DEFAULT '{}'::jsonb,
                updated_at TEXT NOT NULL DEFAULT NOW(),
                PRIMARY KEY(athlete_id)
            )
            """
        )
        conn.commit()


def save_metabolic_profile(profile: dict, athlete_id: int, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_profiles_table(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metabolic_profiles
                (athlete_id, tenant_id, sex, bmr_formula, activity_level,
                 bmr_kcal, tdee_kcal, notes, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id) DO UPDATE SET
                    sex = excluded.sex,
                    bmr_formula = excluded.bmr_formula,
                    activity_level = excluded.activity_level,
                    bmr_kcal = excluded.bmr_kcal,
                    tdee_kcal = excluded.tdee_kcal,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                RETURNING athlete_id
                """,
                (
                    athlete_id,
                    tenant_id,
                    profile.get("sex", "male"),
                    profile.get("bmr_formula", "mifflin"),
                    profile.get("activity_level", "moderate"),
                    profile.get("bmr_kcal"),
                    profile.get("tdee_kcal"),
                    profile.get("notes"),
                    now,
                    now,
                ),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_metabolic_profile(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_profiles_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM metabolic_profiles WHERE athlete_id = %s AND tenant_id = %s",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM metabolic_profiles WHERE athlete_id = %s",
                    (athlete_id,),
                )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "athlete_id": row["athlete_id"],
                "tenant_id": row["tenant_id"],
                "sex": row["sex"],
                "bmr_formula": row["bmr_formula"],
                "activity_level": row["activity_level"],
                "bmr_kcal": row["bmr_kcal"],
                "tdee_kcal": row["tdee_kcal"],
                "notes": row["notes"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
    finally:
        _safe_close(conn)


def save_food_log(log: dict, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_food_logs_table(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO food_logs
                (athlete_id, tenant_id, date, meal_type, description, kcal,
                 carbs_g, protein_g, fat_g, fiber_g, water_ml, note,
                 recorded_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    log.get("athlete_id"),
                    log.get("tenant_id", tenant_id),
                    log.get("date"),
                    log.get("meal_type", "other"),
                    log.get("description", ""),
                    log.get("kcal", 0),
                    log.get("carbs_g"),
                    log.get("protein_g"),
                    log.get("fat_g"),
                    log.get("fiber_g"),
                    log.get("water_ml"),
                    log.get("note"),
                    log.get("recorded_at") or now,
                    now,
                ),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_food_logs_by_athlete_date(
    athlete_id: int,
    date: str,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_food_logs_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM food_logs WHERE athlete_id = %s AND date = %s "
                    "AND tenant_id = %s ORDER BY recorded_at ASC",
                    (athlete_id, date, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM food_logs WHERE athlete_id = %s AND date = %s ORDER BY recorded_at ASC",
                    (athlete_id, date),
                )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def update_food_log(log_id: int, log_data: dict) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_food_logs_table(conn)
        now = datetime.now(UTC).isoformat()
        sets = []
        params = []
        for key in (
            "date", "meal_type", "description", "kcal",
            "carbs_g", "protein_g", "fat_g", "fiber_g", "water_ml", "note"
        ):
            if key in log_data:
                sets.append(f"{key} = %s")
                params.append(log_data[key])
        if "recorded_at" in log_data:
            sets.append("recorded_at = %s")
            params.append(log_data["recorded_at"])
        sets.append("created_at = %s")
        params.append(now)
        params.append(log_id)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE food_logs SET {', '.join(sets)} WHERE id = %s",
                params,
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def get_food_log(log_id: int) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_food_logs_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM food_logs WHERE id = %s", (log_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _safe_close(conn)


def delete_food_log(log_id: int) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_food_logs_table(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM food_logs WHERE id = %s", (log_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def save_metabolic_daily_summary(summary: dict, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_daily_summaries_table(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metabolic_daily_summaries
                (athlete_id, tenant_id, date, bmr_kcal, tdee_kcal,
                 intake_kcal, expenditure_kcal, balance_kcal, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(athlete_id, date) DO UPDATE SET
                    bmr_kcal = excluded.bmr_kcal,
                    tdee_kcal = excluded.tdee_kcal,
                    intake_kcal = excluded.intake_kcal,
                    expenditure_kcal = excluded.expenditure_kcal,
                    balance_kcal = excluded.balance_kcal,
                    updated_at = excluded.updated_at
                RETURNING id
                """,
                (
                    summary.get("athlete_id"),
                    summary.get("tenant_id", tenant_id),
                    summary.get("date"),
                    summary.get("bmr_kcal"),
                    summary.get("tdee_kcal"),
                    summary.get("intake_kcal", 0),
                    summary.get("expenditure_kcal", 0),
                    summary.get("balance_kcal", 0),
                    now,
                    now,
                ),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_metabolic_daily_summaries(
    athlete_id: int,
    start_date: str,
    end_date: str,
    tenant_id: int | None = None,
) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_daily_summaries_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM metabolic_daily_summaries WHERE athlete_id = %s AND tenant_id = %s AND date >= %s AND date <= %s ORDER BY date ASC",
                    (athlete_id, tenant_id, start_date, end_date),
                )
            else:
                cur.execute(
                    "SELECT * FROM metabolic_daily_summaries WHERE athlete_id = %s AND date >= %s AND date <= %s ORDER BY date ASC",
                    (athlete_id, start_date, end_date),
                )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def get_metabolic_daily_summary(athlete_id: int, date: str, tenant_id: int | None = None) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_daily_summaries_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM metabolic_daily_summaries WHERE athlete_id = %s AND date = %s AND tenant_id = %s",
                    (athlete_id, date, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM metabolic_daily_summaries WHERE athlete_id = %s AND date = %s",
                    (athlete_id, date),
                )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _safe_close(conn)


def upsert_metabolic_reference_value(value: dict, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_reference_values_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metabolic_reference_values
                (sex, age_lo, age_hi, weight_lo, weight_hi, activity_level,
                 bmr_kcal, tdee_kcal, source, tenant_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    value.get("sex", "male"),
                    value.get("age_lo", 18),
                    value.get("age_hi", 100),
                    value.get("weight_lo", 30),
                    value.get("weight_hi", 200),
                    value.get("activity_level", "moderate"),
                    value.get("bmr_kcal"),
                    value.get("tdee_kcal"),
                    value.get("source", "builtin"),
                    value.get("tenant_id", tenant_id),
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_metabolic_reference_value(
    sex: str,
    age: int,
    weight: float,
    activity_level: str,
    tenant_id: int | None = None,
) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_reference_values_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM metabolic_reference_values WHERE sex = %s AND age_lo <= %s AND age_hi >= %s AND weight_lo <= %s AND weight_hi >= %s AND activity_level = %s AND tenant_id = %s ORDER BY created_at DESC LIMIT 1",
                    (sex, age, age, weight, weight, activity_level, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM metabolic_reference_values WHERE sex = %s AND age_lo <= %s AND age_hi >= %s AND weight_lo <= %s AND weight_hi >= %s AND activity_level = %s ORDER BY created_at DESC LIMIT 1",
                    (sex, age, age, weight, weight, activity_level),
                )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _safe_close(conn)


def get_all_metabolic_reference_values(tenant_id: int | None = None) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_reference_values_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM metabolic_reference_values WHERE tenant_id = %s ORDER BY created_at DESC",
                    (tenant_id,),
                )
            else:
                cur.execute("SELECT * FROM metabolic_reference_values ORDER BY created_at DESC")
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)


def save_metabolic_adaptive_weights(weights: dict, athlete_id: int, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_adaptive_weights_table(conn)
        now = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metabolic_adaptive_weights (athlete_id, tenant_id, weights, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(athlete_id) DO UPDATE SET
                    weights = excluded.weights,
                    updated_at = excluded.updated_at
                RETURNING athlete_id
                """,
                (athlete_id, tenant_id, json.dumps(weights), now),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_metabolic_adaptive_weights(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_metabolic_adaptive_weights_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM metabolic_adaptive_weights WHERE athlete_id = %s AND tenant_id = %s",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM metabolic_adaptive_weights WHERE athlete_id = %s",
                    (athlete_id,),
                )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "athlete_id": row["athlete_id"],
                "tenant_id": row["tenant_id"],
                "weights": json.loads(row["weights"]) if row["weights"] else {},
                "updated_at": row["updated_at"],
            }
    finally:
        _safe_close(conn)
