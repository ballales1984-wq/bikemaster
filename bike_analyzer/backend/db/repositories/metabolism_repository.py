"""Metabolism repository — SQLite persistence for metabolic profiles, food logs, daily summaries, reference values and adaptive weights."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def save_metabolic_profile(profile: dict, athlete_id: int, tenant_id: int = 0) -> int:
    """Upsert metabolic profile for an athlete."""
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO metabolic_profiles
            (athlete_id, tenant_id, sex, bmr_formula, activity_level,
             bmr_kcal, tdee_kcal, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id) DO UPDATE SET
                sex=excluded.sex,
                bmr_formula=excluded.bmr_formula,
                activity_level=excluded.activity_level,
                bmr_kcal=excluded.bmr_kcal,
                tdee_kcal=excluded.tdee_kcal,
                notes=excluded.notes,
                updated_at=excluded.updated_at""",
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
        return athlete_id


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_metabolic_profile(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    """Recupera il profilo metabolico di un atleta."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM metabolic_profiles WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute("SELECT * FROM metabolic_profiles WHERE athlete_id = ?", (athlete_id,))
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


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def save_food_log(log: dict, tenant_id: int = 0) -> int:
    """Inserisce un nuovo log alimentare."""
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO food_logs
            (athlete_id, tenant_id, date, meal_type, description, kcal,
             carbs_g, protein_g, fat_g, fiber_g, water_ml, note,
             recorded_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_food_logs_by_athlete_date(
    athlete_id: int,
    date: str,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    """Restituisce i log alimentari di un atleta per una data specifica."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM food_logs WHERE athlete_id = ? AND date = ? AND tenant_id = ? ORDER BY recorded_at ASC",
                (athlete_id, date, tenant_id),
            )
        else:
            cur.execute(
                """SELECT * FROM food_logs WHERE athlete_id = ? AND date = ? ORDER BY recorded_at ASC""",
                (athlete_id, date),
            )
        rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "athlete_id": r["athlete_id"],
            "tenant_id": r["tenant_id"],
            "date": r["date"],
            "meal_type": r["meal_type"],
            "description": r["description"],
            "kcal": r["kcal"],
            "carbs_g": r["carbs_g"],
            "protein_g": r["protein_g"],
            "fat_g": r["fat_g"],
            "fiber_g": r["fiber_g"],
            "water_ml": r["water_ml"],
            "note": r["note"],
            "recorded_at": r["recorded_at"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_food_logs_by_athlete(athlete_id: int, tenant_id: int | None = None, limit: int = 2000) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM food_logs WHERE athlete_id = ? AND tenant_id = ? ORDER BY date ASC LIMIT ?",
                (athlete_id, tenant_id, limit),
            )
        else:
            cur.execute(
                "SELECT * FROM food_logs WHERE athlete_id = ? ORDER BY date ASC LIMIT ?",
                (athlete_id, limit),
            )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def update_food_log(log_id: int, log_data: dict) -> bool:
    """Aggiorna un log alimentare esistente."""
    existing = get_food_log(log_id)
    if not existing:
        return False
    merged = {**existing, **log_data}
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE food_logs SET
               date=?, meal_type=?, description=?, kcal=?, carbs_g=?, protein_g=?,
               fat_g=?, fiber_g=?, water_ml=?, note=?, recorded_at=?
               WHERE id=?""",
            (
                merged.get("date"),
                merged.get("meal_type"),
                merged.get("description"),
                merged.get("kcal"),
                merged.get("carbs_g"),
                merged.get("protein_g"),
                merged.get("fat_g"),
                merged.get("fiber_g"),
                merged.get("water_ml"),
                merged.get("note"),
                merged.get("recorded_at"),
                log_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_food_log(log_id: int) -> dict | None:
    """Recupera un singolo log alimentare per id."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM food_logs WHERE id = ?", (log_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "athlete_id": row["athlete_id"],
            "tenant_id": row["tenant_id"],
            "date": row["date"],
            "meal_type": row["meal_type"],
            "description": row["description"],
            "kcal": row["kcal"],
            "carbs_g": row["carbs_g"],
            "protein_g": row["protein_g"],
            "fat_g": row["fat_g"],
            "fiber_g": row["fiber_g"],
            "water_ml": row["water_ml"],
            "note": row["note"],
            "recorded_at": row["recorded_at"],
            "created_at": row["created_at"],
        }


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def delete_food_log(log_id: int) -> bool:
    """Elimina un log alimentare."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM food_logs WHERE id = ?", (log_id,))
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def save_metabolic_daily_summary(summary: dict, tenant_id: int = 0) -> int:
    """Upsert metabolic daily summary for an athlete on a specific date."""
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO metabolic_daily_summaries
            (athlete_id, tenant_id, date, bmr_kcal, neat_kcal, eat_kcal,
             climb_bonus_kcal, tdee_kcal, intake_kcal, balance_kcal,
             steps_estimated, elevation_gain_estimated_m, rides_count,
             gps_neat_kcal, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                bmr_kcal=excluded.bmr_kcal,
                neat_kcal=excluded.neat_kcal,
                eat_kcal=excluded.eat_kcal,
                climb_bonus_kcal=excluded.climb_bonus_kcal,
                tdee_kcal=excluded.tdee_kcal,
                intake_kcal=excluded.intake_kcal,
                balance_kcal=excluded.balance_kcal,
                steps_estimated=excluded.steps_estimated,
                elevation_gain_estimated_m=excluded.elevation_gain_estimated_m,
                rides_count=excluded.rides_count,
                gps_neat_kcal=excluded.gps_neat_kcal,
                notes=excluded.notes,
                updated_at=excluded.updated_at""",
            (
                summary.get("athlete_id"),
                summary.get("tenant_id", tenant_id),
                summary.get("date"),
                summary.get("bmr_kcal", 0),
                summary.get("neat_kcal", 0),
                summary.get("eat_kcal", 0),
                summary.get("climb_bonus_kcal", 0),
                summary.get("tdee_kcal", 0),
                summary.get("intake_kcal", 0),
                summary.get("balance_kcal", 0),
                summary.get("steps_estimated"),
                summary.get("elevation_gain_estimated_m"),
                summary.get("rides_count", 0),
                summary.get("gps_neat_kcal", 0),
                summary.get("notes"),
                now,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_metabolic_daily_summaries(
    athlete_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: int | None = None,
    limit: int = 365,
) -> list[dict]:
    """Recupera i riepiloghi metabolici giornalieri per un atleta."""
    query = "SELECT * FROM metabolic_daily_summaries WHERE athlete_id = ?"
    params: list = [athlete_id]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "athlete_id": r["athlete_id"],
            "tenant_id": r["tenant_id"],
            "date": r["date"],
            "bmr_kcal": r["bmr_kcal"],
            "neat_kcal": r["neat_kcal"],
            "eat_kcal": r["eat_kcal"],
            "climb_bonus_kcal": r["climb_bonus_kcal"],
            "tdee_kcal": r["tdee_kcal"],
            "intake_kcal": r["intake_kcal"],
            "balance_kcal": r["balance_kcal"],
            "steps_estimated": r["steps_estimated"],
            "elevation_gain_estimated_m": r["elevation_gain_estimated_m"],
            "rides_count": r["rides_count"],
            "gps_neat_kcal": r["gps_neat_kcal"],
            "notes": r["notes"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_metabolic_daily_summary(
    athlete_id: int,
    date: str,
    tenant_id: int | None = None,
) -> dict | None:
    """Recupera il riepilogo metabolico per una data specifica."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM metabolic_daily_summaries WHERE athlete_id = ? AND date = ? AND tenant_id = ?",
                (athlete_id, date, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM metabolic_daily_summaries WHERE athlete_id = ? AND date = ?",
                (athlete_id, date),
            )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "athlete_id": row["athlete_id"],
            "tenant_id": row["tenant_id"],
            "date": row["date"],
            "bmr_kcal": row["bmr_kcal"],
            "neat_kcal": row["neat_kcal"],
            "eat_kcal": row["eat_kcal"],
            "climb_bonus_kcal": row["climb_bonus_kcal"],
            "tdee_kcal": row["tdee_kcal"],
            "intake_kcal": row["intake_kcal"],
            "balance_kcal": row["balance_kcal"],
            "steps_estimated": row["steps_estimated"],
            "elevation_gain_estimated_m": row["elevation_gain_estimated_m"],
            "rides_count": row["rides_count"],
            "gps_neat_kcal": row["gps_neat_kcal"],
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def upsert_metabolic_reference_value(value: dict, tenant_id: int = 0) -> int:
    """Upsert a reference (mean) metabolic value for a demographic bracket."""
    now = datetime.now(UTC).isoformat()
    sex = value.get("sex", "male")
    alo = int(value.get("age_bracket_lo", 0))
    ahi = int(value.get("age_bracket_hi", 0))
    wlo = int(value.get("weight_bracket_lo", 0))
    whi = int(value.get("weight_bracket_hi", 0))
    activity_level = value.get("activity_level", "moderate")
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO metabolic_reference_values
            (tenant_id, sex, age_bracket_lo, age_bracket_hi,
             weight_bracket_lo, weight_bracket_hi, bmr_kcal, tdee_kcal,
             activity_level, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sex, age_bracket_lo, age_bracket_hi,
                        weight_bracket_lo, weight_bracket_hi, activity_level)
            DO UPDATE SET
                bmr_kcal=excluded.bmr_kcal,
                tdee_kcal=excluded.tdee_kcal,
                source=excluded.source,
                created_at=excluded.created_at""",
            (
                tenant_id,
                sex,
                alo,
                ahi,
                wlo,
                whi,
                value.get("bmr_kcal"),
                value.get("tdee_kcal"),
                activity_level,
                value.get("source", "import"),
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid) if cur.lastrowid else 0


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_metabolic_reference_value(
    sex: str,
    age: int,
    weight_kg: float,
    activity_level: str = "moderate",
    tenant_id: int = 0,
) -> dict | None:
    """Return the imported reference row for the bracket closest to age/weight."""
    from ...core.calculators.metabolism import age_bracket, weight_bracket

    a_lo, a_hi = age_bracket(age)
    w_lo, w_hi = weight_bracket(weight_kg)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT * FROM metabolic_reference_values
            WHERE sex = ? AND age_bracket_lo = ? AND age_bracket_hi = ?
              AND weight_bracket_lo = ? AND weight_bracket_hi = ?
              AND activity_level = ?
            LIMIT 1""",
            (sex, a_lo, a_hi, w_lo, w_hi, activity_level),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "tenant_id": row["tenant_id"],
            "sex": row["sex"],
            "age_bracket_lo": row["age_bracket_lo"],
            "age_bracket_hi": row["age_bracket_hi"],
            "weight_bracket_lo": row["weight_bracket_lo"],
            "weight_bracket_hi": row["weight_bracket_hi"],
            "bmr_kcal": row["bmr_kcal"],
            "tdee_kcal": row["tdee_kcal"],
            "activity_level": row["activity_level"],
            "source": row["source"],
            "created_at": row["created_at"],
        }


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_all_metabolic_reference_values(tenant_id: int | None = None) -> list[dict]:
    """Return all imported reference values, optionally filtered by tenant."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM metabolic_reference_values WHERE tenant_id = ? ORDER BY id", (tenant_id,))
        else:
            cur.execute("SELECT * FROM metabolic_reference_values ORDER BY id")
        return [dict(row) for row in cur.fetchall()]


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def save_metabolic_adaptive_weights(weights: dict, athlete_id: int, tenant_id: int = 0) -> int:
    """Upsert per-athlete adaptive model weights and sensor confidence."""
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO metabolic_adaptive_weights
            (athlete_id, tenant_id, activity_multiplier_w, neat_w,
             climb_bonus_w, sensor_bmr_conf, sensor_tdee_conf,
             learning_rate, confidence_lr, n_updates, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id) DO UPDATE SET
                activity_multiplier_w=excluded.activity_multiplier_w,
                neat_w=excluded.neat_w,
                climb_bonus_w=excluded.climb_bonus_w,
                sensor_bmr_conf=excluded.sensor_bmr_conf,
                sensor_tdee_conf=excluded.sensor_tdee_conf,
                learning_rate=excluded.learning_rate,
                confidence_lr=excluded.confidence_lr,
                n_updates=excluded.n_updates,
                updated_at=excluded.updated_at""",
            (
                athlete_id,
                tenant_id,
                float(weights.get("activity_multiplier_w", 1.0)),
                float(weights.get("neat_w", 1.0)),
                float(weights.get("climb_bonus_w", 1.0)),
                float(weights.get("sensor_bmr_conf", 1.0)),
                float(weights.get("sensor_tdee_conf", 1.0)),
                float(weights.get("learning_rate", 0.1)),
                float(weights.get("confidence_lr", 0.05)),
                int(weights.get("n_updates", 0) or 0),
                now,
            ),
        )
        conn.commit()
        return athlete_id


@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")
def get_metabolic_adaptive_weights(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    """Return the per-athlete adaptive weights, if any."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM metabolic_adaptive_weights WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute("SELECT * FROM metabolic_adaptive_weights WHERE athlete_id = ?", (athlete_id,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)
