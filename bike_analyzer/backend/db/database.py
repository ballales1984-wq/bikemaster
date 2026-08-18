"""Database layer — SQLite (local-first primary store) with optional PostgreSQL cloud sync.

Questo modulo costituisce il layer di persistenza primario dell'applicazione.
E' organizzato come un insieme di funzioni sincrone che operano su SQLite
tramite ``sqlite3`` standard, con le seguenti caratteristiche:

- Modalita' WAL (Write-Ahead Logging) per concorrenza lettura/scrittura.
- Retry automatico su lock contention (max 5 tentativi, backoff esponenziale).
- Migrazioni leggere inline (``ALTER TABLE`` condizionali) per evoluzione
  dello schema senza tool esterni.
- Indici performance per query frequenti su ``athlete_id``, ``date`` e
  ``distance_km``.
- Supporto multi-tenant tramite colonna ``tenant_id`` su ogni tabella.
- Deduplicazione per sorgenti esterne (Strava, Garmin) tramite indice
  unique su ``(external_source, external_id)``.
- Funzioni di backup e rotazione automatica dei file di database.

Per il cloud (Hub) si usa invece ``async_db.py`` con PostgreSQL/SQLAlchemy.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from typing import Any

from ..models.models import Ride  # noqa: F401
from ..settings import get_settings
from ..utils.logger import get_logger
from .dispatch import pg_dispatch
from .repositories.athlete_repository import (
    _row_to_athlete,  # noqa: F401
    delete_athlete,  # noqa: F401
    get_all_athletes,
    get_athlete,
    get_athlete_by_email,
    get_athlete_by_name,
    get_athlete_count_by_user,  # noqa: F401
    get_athlete_history,  # noqa: F401
    get_athlete_metric_log,  # noqa: F401
    get_athletes_by_user,  # noqa: F401
    log_athlete_metric,  # noqa: F401
    save_athlete,
    save_athlete_snapshot,  # noqa: F401
    update_athlete,
)
from .repositories.ride_repository import (
    _find_existing_external_ride,  # noqa: F401
    _row_to_ride,  # noqa: F401
    delete_ride,
    get_all_rides,
    get_metrics_by_athlete,
    get_ride,
    get_rides_by_athlete,
    save_metric,
    save_ride,
    update_ride,
)
from .repositories.training_stress_repository import (
    get_latest_training_stress,
    get_training_stress_days,
    upsert_training_stress_day,
)

from .repositories.beck_repository import (
    _beck_severity,
    get_beck_assessment,
    get_beck_assessments_by_athlete,
    get_latest_beck_assessment,
    save_beck_assessment,
)
from .repositories.ble_repository import (
    get_ble_device,
    get_ble_devices,
    mark_ble_device_connected,
    mark_ble_device_synced,
    register_ble_device,
    unregister_ble_device,
    update_ble_device,
)
from .repositories.calendar_repository import (
    _row_to_calendar_event,
    delete_calendar_event,
    get_calendar_event,
    get_events_by_athlete,
    get_events_by_date_range,
    get_events_by_month,
    save_calendar_event,
    update_calendar_event,
)
from .repositories.chat_repository import (
    clear_chat_history,
    get_chat_history,
    prune_chat_history,
    save_chat_message,
)
from .repositories.fitness_repository import (
    get_fitness_states_by_athlete,
)
from .repositories.google_oauth_repository import (
    delete_google_token,
    get_google_token,
    save_google_token,
)
from .repositories.health_connect_repository import (
    connect_health_connect,
    disconnect_health_connect,
    get_health_connect_token,
    update_health_connect_sync,
)
from .repositories.hr_repository import (
    _get_max_hr_setting,
    _get_resting_hr_setting,
    delete_hr_samples,
    delete_hr_settings,
    get_hr_24h_samples,
    get_hr_daily_summary,
    get_hr_settings,
    log_hr_sample,
    log_hr_samples,
    upsert_hr_settings,
)
from .repositories.legal_repository import (
    get_ai_audit_logs_by_athlete,
    get_consent,
    get_consents_by_athlete,
    get_legal_acceptances_by_athlete,
    has_accepted_version,
    save_ai_audit_log,
    save_consent,
    save_legal_acceptance,
)
from .repositories.maps_repository import (
    get_maps_usage,
    record_maps_call,
)
from .repositories.metabolism_repository import (
    delete_food_log,
    get_all_metabolic_reference_values,
    get_food_log,
    get_food_logs_by_athlete,
    get_food_logs_by_athlete_date,
    get_metabolic_adaptive_weights,
    get_metabolic_daily_summary,
    get_metabolic_daily_summaries,
    get_metabolic_profile,
    get_metabolic_reference_value,
    save_food_log,
    save_metabolic_adaptive_weights,
    save_metabolic_daily_summary,
    save_metabolic_profile,
    upsert_metabolic_reference_value,
    update_food_log,
)
from .repositories.nutrition_repository import (
    delete_nutrition_food_item,
    get_nutrition_food_item,
    list_nutrition_categories,
    save_nutrition_food_item,
    search_nutrition_food_items,
    seed_nutrition_food_items,
    update_nutrition_food_item,
)
from .repositories.oauth_tokens_repository import (
    get_garmin_token,
    get_strava_token,
    get_wahoo_token,
    revoke_garmin_token,
    revoke_strava_token,
    revoke_wahoo_token,
    save_garmin_token,
    save_strava_token,
    save_wahoo_token,
    update_strava_last_sync,
)
from .repositories.poi_repository import (
    _row_to_poi,
    delete_poi,
    get_nearby_pois,
    get_poi,
    list_pois,
    save_poi,
)
from .repositories.safety_repository import (
    get_route_safety_score,
    save_road_incident,
    save_route_safety_score,
)
from .repositories.security_repository import (
    is_token_revoked,
    revoke_token,
    sweep_revoked_tokens,
)
from .repositories.sensor_repository import (
    _get_max_hr_setting,
    _get_resting_hr_setting,
    classify_day,
    get_activity_classification,
    get_activity_summary,
    log_sensor_data,
)
from .repositories.sync_repository import (
    _row_to_sync_entity_state,
    get_pending_sync_entities,
    get_sync_conflicts,
    get_sync_entity_state,
    get_sync_setting,
    resolve_sync_conflict,
    save_sync_conflict,
    save_sync_entity_state,
    save_sync_setting,
)
from .repositories.itineraries_repository import (
    delete_itinerary,
    delete_stage,
    get_itinerary,
    get_stage,
    list_itineraries,
    list_stages,
    reorder_stages,
    save_itinerary,
    save_stage,
    update_itinerary,
    update_stage,
)
from .repositories.user_repository import (
    delete_user,
    get_all_users,
    get_user_by_id,
    get_user_by_username,
    save_user,
    update_user,
)
from .repositories.user_oauth_repository import (
    delete_user_oauth_credentials,
    get_all_user_oauth_credentials,
    get_user_oauth_credentials,
    save_user_oauth_credentials,
)
from .repositories.weather_repository import (
    get_weather_cache,
    save_weather_cache,
)

logger = get_logger(__name__)

_s = get_settings()
DB_PATH = _s.db_path
_INITIAL_DB_PATH = DB_PATH

_persistence_warned: set[str] = set()
_db_initializing = False
_db_initialized = False
_init_db_path = None


def _create_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_db_initialized() -> None:
    global _db_initializing, _db_initialized, _init_db_path
    if _db_initialized and _init_db_path == DB_PATH:
        return
    if _db_initializing:
        return
    _db_initializing = True
    try:
        init_db()
        _db_initialized = True
        _init_db_path = DB_PATH
    finally:
        _db_initializing = False


def _is_persistent_path(path: str) -> bool:
    import pathlib

    p = pathlib.Path(path)
    parent = p.parent
    if not parent.exists():
        return False
    try:
        test_file = parent / ".bikemaster_persistence_check"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return True
    except Exception:
        return False


def _warn_sqlite_persistence(caller_name: str) -> None:
    if not _s.database_url and _is_persistent_path(DB_PATH):
        return
    key = f"{caller_name}:{DB_PATH}"
    if key in _persistence_warned:
        return
    _persistence_warned.add(key)
    is_prod = _s.environment.lower() in ("production", "prod", "staging")
    level = logger.error if is_prod else logger.warning
    level(
        "SQLite write on %s path (caller=%s, db=%s). "
        "Data will be lost on container resume unless a persistent disk is mounted.",
        "NON-PERSISTENT" if not _is_persistent_path(DB_PATH) else "FALLBACK",
        caller_name,
        DB_PATH,
    )


@contextmanager
def get_db_connection():
    """Context manager per connessioni SQLite con WAL e retry su lock.

    Configura la connessione con:
    - ``journal_mode=WAL`` per letture concorrenti durante la scrittura.
    - ``busy_timeout=5000`` per attendere il rilascio del lock.
    - ``foreign_keys=ON`` per integrita' referenziale.
    - ``row_factory=sqlite3.Row`` per accesso per colonna.

    In caso di ``OperationalError`` con messaggio ``locked`` ritenta fino a
    3 volte con backoff lineare (0.1s, 0.2s, 0.3s). Il commit e' automatico
    se il blocco ``with`` completa senza eccezioni.
    """
    import time

    caller_name = _get_caller_name()
    _ensure_db_initialized()
    if not _s.database_url:
        _warn_sqlite_persistence(caller_name)

    max_retries = 3
    retry_delay = 0.1
    conn = None
    for attempt in range(max_retries):
        try:
            conn = _create_connection()
            break
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise

    if conn is None:
        raise RuntimeError(f"Failed to connect to database at {DB_PATH} after {max_retries} retries")

    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _get_caller_name() -> str:
    import inspect

    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back
        while caller_frame:
            filename = caller_frame.f_code.co_filename
            if "database.py" not in filename:
                return caller_frame.f_code.co_name
            caller_frame = caller_frame.f_back
        return "unknown"
    finally:
        del frame


def recalculate_training_stress_for_athlete(athlete_id: int, ftp: float = 250.0, tenant_id: int = 0) -> None:
    from ..analytics.training_load import recalculate_training_stress_for_athlete as _recalculate

    return _recalculate(athlete_id, ftp=ftp, tenant_id=tenant_id)


def init_db():
    """Crea tutte le tabelle e applica le migrazioni leggere per SQLite.

    Esegue ``CREATE TABLE IF NOT EXISTS`` per ogni entita' del dominio,
    poi applica migrazioni incrementali con ``ALTER TABLE`` condizionali
    (controlla ``PRAGMA table_info`` prima di aggiungere colonne).
    Include anche la creazione degli indici performance e delle tabelle
    per il sync bidirezionale.
    """
    with get_db_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            is_admin INTEGER DEFAULT 0,
            is_client INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )""")
        with suppress(Exception):
            conn.execute("ALTER TABLE users ADD COLUMN is_client INTEGER DEFAULT 0")
        conn.execute("""CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            activity_type TEXT DEFAULT 'ride',
            is_official INTEGER DEFAULT 1,
            source TEXT DEFAULT 'manual',
            created_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS athlete_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            recorded_at TEXT NOT NULL,
            changed_by INTEGER,
            name TEXT,
            email TEXT,
            picture TEXT,
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
            apparent_age INTEGER,
            bmi REAL,
            lean_body_mass_kg REAL
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_history_athlete_recorded ON athlete_history(athlete_id, recorded_at)"
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS athlete_metric_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            tenant_id INTEGER DEFAULT 0,
            metric_type TEXT NOT NULL,
            value REAL,
            unit TEXT,
            note TEXT,
            source TEXT DEFAULT 'manual',
            recorded_at TEXT,
            created_at TEXT,
            UNIQUE(athlete_id, metric_type, recorded_at)
        )""")
        with suppress(Exception):
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_metric_log_athlete_metric ON athlete_metric_log(athlete_id, metric_type)"
            )
        with suppress(Exception):
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_metric_log_athlete_metric_recorded "
                "ON athlete_metric_log(athlete_id, metric_type, recorded_at)"
            )
        conn.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            tenant_id INTEGER DEFAULT 0,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            tenant_id INTEGER DEFAULT 0,
            title TEXT NOT NULL,
            event_type TEXT DEFAULT 'training',
            date TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 0,
            description TEXT,
            completed INTEGER DEFAULT 0,
            weather_temp REAL,
            weather_humidity REAL,
            weather_description TEXT,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS weather_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            date TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            description TEXT,
            cached_at TEXT,
            UNIQUE(lat, lon, date)
        )""")
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(athletes)")
        athlete_cols = [row[1] for row in cur.fetchall()]
        if "goals" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN goals TEXT")
        if "ftp_watts" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN ftp_watts REAL")
        if "password_hash" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN password_hash TEXT")
        if "email" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN email TEXT")
        if "picture" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN picture TEXT")
        if "body_water_percentage" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN body_water_percentage REAL")
        if "muscle_mass_percentage" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN muscle_mass_percentage REAL")
        if "bmr_kcal" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN bmr_kcal REAL")
        if "fat_mass_kg" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN fat_mass_kg REAL")
        if "subcutaneous_fat_kg" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN subcutaneous_fat_kg REAL")
        if "subcutaneous_fat_percentage" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN subcutaneous_fat_percentage REAL")
        if "visceral_fat_level" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN visceral_fat_level REAL")
        if "visceral_fat_percentage" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN visceral_fat_percentage REAL")
        if "visceral_fat_kg" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN visceral_fat_kg REAL")
        if "muscle_mass_kg" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN muscle_mass_kg REAL")
        if "bone_mass_kg" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN bone_mass_kg REAL")
        if "protein_percentage" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN protein_percentage REAL")
        if "protein_kg" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN protein_kg REAL")
        if "body_age" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN body_age INTEGER")
        if "apparent_age" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN apparent_age INTEGER")
        if "bmi" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN bmi REAL")
        if "lean_body_mass_kg" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN lean_body_mass_kg REAL")
        if "updated_at" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN updated_at TEXT")
        cur.execute("PRAGMA table_info(athlete_history)")
        history_cols = [row[1] for row in cur.fetchall()]
        if not history_cols:
            pass
        cur.execute("PRAGMA table_info(athlete_history)")
        history_cols = [row[1] for row in cur.fetchall()]
        if "bmi" not in history_cols:
            conn.execute("ALTER TABLE athlete_history ADD COLUMN bmi REAL")
        if "lean_body_mass_kg" not in history_cols:
            conn.execute("ALTER TABLE athlete_history ADD COLUMN lean_body_mass_kg REAL")
        conn.execute("""CREATE TABLE IF NOT EXISTS training_stress_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            tss REAL,
            atl REAL,
            ctl REAL,
            tsb REAL,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(athlete_id, date),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            ride_id INTEGER,
            fatigue_score REAL,
            recovery_hours REAL,
            calories_per_km REAL,
            efficiency_score REAL,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id),
            FOREIGN KEY (ride_id) REFERENCES rides(id)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_ride ON metrics(ride_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS training_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            title TEXT NOT NULL,
            description TEXT,
            goal_type TEXT DEFAULT 'granfondo',
            target_date TEXT,
            target_distance_km REAL,
            target_elevation_m REAL,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS planned_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            goal_id INTEGER,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            workout_type TEXT DEFAULT 'endurance',
            duration_minutes INTEGER DEFAULT 60,
            target_intensity REAL DEFAULT 0.5,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id),
            FOREIGN KEY (goal_id) REFERENCES training_goals(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS road_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            incident_date TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',
            description TEXT,
            road_type TEXT,
            source TEXT NOT NULL DEFAULT 'local',
            created_at TEXT,
            UNIQUE(source_id, source)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS route_safety_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id INTEGER,
            athlete_id INTEGER,
            risk_score REAL,
            label TEXT,
            advice TEXT,
            road_type_counts TEXT,
            has_bike_infrastructure INTEGER,
            incident_count INTEGER,
            route_length_km REAL,
            computed_at TEXT,
            tenant_id INTEGER DEFAULT 0,
            FOREIGN KEY (ride_id) REFERENCES rides(id),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
         )""")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_route_safety_scores_ride ON route_safety_scores(ride_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS pois (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            type TEXT NOT NULL,
            photos TEXT,
            video_url TEXT,
            difficulty_note TEXT,
            tags TEXT,
            itinerary_id INTEGER,
            created_by INTEGER,
            tenant_id INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE SET NULL
        )""")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_pois_tenant_coords_name_type ON pois(tenant_id, lat, lon, name, type)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pois_coords ON pois(lat, lon)")
        conn.execute("""CREATE TABLE IF NOT EXISTS itineraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            tenant_id INTEGER DEFAULT 0,
            name TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            end_date TEXT,
            total_km REAL DEFAULT 0,
            total_elevation_m REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_itineraries_athlete ON itineraries(athlete_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            itinerary_id INTEGER NOT NULL,
            stage_day INTEGER DEFAULT 1,
            title TEXT,
            distance_km REAL DEFAULT 0,
            elevation_gain_m REAL DEFAULT 0,
            estimated_km REAL,
            estimated_elevation_m REAL,
            ride_id INTEGER,
            poi_id INTEGER,
            notes TEXT,
            tenant_id INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE CASCADE,
            FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE SET NULL,
            FOREIGN KEY (poi_id) REFERENCES pois(id) ON DELETE SET NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stages_itinerary ON stages(itinerary_id)")
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(stages)")
        stage_cols = [row[1] for row in cur.fetchall()]
        if "poi_id" not in stage_cols:
            conn.execute("ALTER TABLE stages ADD COLUMN poi_id INTEGER")
        if "notes" not in stage_cols:
            conn.execute("ALTER TABLE stages ADD COLUMN notes TEXT")
        if "tenant_id" not in stage_cols:
            conn.execute("ALTER TABLE stages ADD COLUMN tenant_id INTEGER DEFAULT 0")
        if "created_at" not in stage_cols:
            conn.execute("ALTER TABLE stages ADD COLUMN created_at TEXT")
        if "updated_at" not in stage_cols:
            conn.execute("ALTER TABLE stages ADD COLUMN updated_at TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stages_poi ON stages(poi_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS fitness_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            tenant_id INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            computed_at TEXT,
            fitness REAL DEFAULT 0,
            fatigue REAL DEFAULT 0,
            form REAL DEFAULT 0,
            atl REAL DEFAULT 0,
            ctl REAL DEFAULT 0,
            tsb REAL DEFAULT 0,
            recovery_hours_needed REAL DEFAULT 0,
            weekly_tss REAL DEFAULT 0,
            monthly_tss REAL DEFAULT 0,
            trend_7d TEXT DEFAULT 'stable',
            trend_30d TEXT DEFAULT 'stable',
            risk_indicators TEXT,
            recommendation TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fitness_states_athlete ON fitness_states(athlete_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS metabolic_profiles (
            athlete_id INTEGER PRIMARY KEY,
            tenant_id INTEGER DEFAULT 0,
            sex TEXT DEFAULT 'male',
            bmr_formula TEXT DEFAULT 'mifflin',
            activity_level TEXT DEFAULT 'moderate',
            bmr_kcal REAL,
            tdee_kcal REAL,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            meal_type TEXT DEFAULT 'other',
            description TEXT NOT NULL,
            kcal REAL DEFAULT 0,
            carbs_g REAL,
            protein_g REAL,
            fat_g REAL,
            fiber_g REAL,
            water_ml REAL,
            note TEXT,
            recorded_at TEXT,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS metabolic_daily_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            bmr_kcal REAL DEFAULT 0,
            neat_kcal REAL DEFAULT 0,
            eat_kcal REAL DEFAULT 0,
            climb_bonus_kcal REAL DEFAULT 0,
            tdee_kcal REAL DEFAULT 0,
            intake_kcal REAL DEFAULT 0,
            balance_kcal REAL DEFAULT 0,
            steps_estimated INTEGER,
            elevation_gain_estimated_m REAL,
            rides_count INTEGER DEFAULT 0,
            gps_neat_kcal REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(athlete_id, date),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_food_logs_athlete_date ON food_logs(athlete_id, date)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_metabolic_summaries_athlete_date "
            "ON metabolic_daily_summaries(athlete_id, date)"
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS metabolic_reference_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER DEFAULT 0,
            sex TEXT NOT NULL,
            age_bracket_lo INTEGER NOT NULL,
            age_bracket_hi INTEGER NOT NULL,
            weight_bracket_lo INTEGER NOT NULL,
            weight_bracket_hi INTEGER NOT NULL,
            bmr_kcal REAL,
            tdee_kcal REAL,
            activity_level TEXT DEFAULT 'moderate',
            source TEXT DEFAULT 'import',
            created_at TEXT,
            UNIQUE(sex, age_bracket_lo, age_bracket_hi, weight_bracket_lo, weight_bracket_hi, activity_level)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metabolic_ref_sex ON metabolic_reference_values(sex)")
        conn.execute("""CREATE TABLE IF NOT EXISTS metabolic_adaptive_weights (
            athlete_id INTEGER PRIMARY KEY,
            tenant_id INTEGER DEFAULT 0,
            activity_multiplier_w REAL DEFAULT 1.0,
            neat_w REAL DEFAULT 1.0,
            climb_bonus_w REAL DEFAULT 1.0,
            sensor_bmr_conf REAL DEFAULT 1.0,
            sensor_tdee_conf REAL DEFAULT 1.0,
            learning_rate REAL DEFAULT 0.1,
            confidence_lr REAL DEFAULT 0.05,
            n_updates INTEGER DEFAULT 0,
            updated_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            ride_id INTEGER,
            date TEXT NOT NULL,
            average_power REAL,
            normalized_power REAL,
            intensity_factor REAL,
            tss REAL,
            ftp_watts REAL,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE,
            FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_athlete ON performance_metrics(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_ride ON performance_metrics(ride_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS ftp_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            ftp_watts REAL NOT NULL,
            source TEXT DEFAULT 'test',
            note TEXT,
            created_at TEXT,
            UNIQUE(athlete_id, date),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ftp_history_athlete_date ON ftp_history(athlete_id, date)")
        conn.execute("""CREATE TABLE IF NOT EXISTS nutrition_food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER DEFAULT 0,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'other',
            kcal_per_100g REAL NOT NULL,
            carbs_g_per_100g REAL DEFAULT 0,
            protein_g_per_100g REAL DEFAULT 0,
            fat_g_per_100g REAL DEFAULT 0,
            fiber_g_per_100g REAL DEFAULT 0,
            source TEXT DEFAULT 'builtin',
            is_builtin INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nutrition_food_name ON nutrition_food_items(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nutrition_food_category ON nutrition_food_items(category)")
        seed_nutrition_food_items()
        conn.execute("""CREATE TABLE IF NOT EXISTS beck_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            total_score INTEGER NOT NULL DEFAULT 0,
            severity TEXT NOT NULL DEFAULT 'minimal',
            answers TEXT NOT NULL DEFAULT '[]',
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_beck_assessments_athlete ON beck_assessments(athlete_id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_beck_assessments_athlete_date ON beck_assessments(athlete_id, created_at)"
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS ble_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            device_id TEXT NOT NULL,
            name TEXT,
            device_type TEXT DEFAULT 'weight_scale',
            service_uuid TEXT,
            characteristic_uuid TEXT,
            mac_address TEXT,
            paired INTEGER DEFAULT 0,
            last_connected_at TEXT,
            last_synced_at TEXT,
            settings TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(athlete_id, device_id),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ble_devices_athlete ON ble_devices(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ble_devices_type ON ble_devices(device_type)")
        conn.execute("""CREATE TABLE IF NOT EXISTS hr_24h_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            heart_rate INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'ble',
            device_id TEXT,
            recorded_at TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hr_samples_athlete_recorded ON hr_24h_samples(athlete_id, recorded_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hr_samples_athlete_date ON hr_24h_samples(athlete_id, date(recorded_at))"
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS hr_monitoring_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            interval_seconds INTEGER NOT NULL DEFAULT 30,
            source TEXT NOT NULL DEFAULT 'ble',
            device_id TEXT,
            max_hr INTEGER,
            resting_hr INTEGER,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(athlete_id),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hr_settings_athlete ON hr_monitoring_settings(athlete_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            ts TEXT NOT NULL,
            heart_rate INTEGER,
            lat REAL,
            lng REAL,
            altitude REAL,
            accel_x REAL,
            accel_y REAL,
            accel_z REAL,
            speed_kmh REAL,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sensor_athlete_ts ON sensor_data(athlete_id, ts)")
        conn.execute("""CREATE TABLE IF NOT EXISTS daily_activity_classification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            label TEXT NOT NULL,
            hr_resting INTEGER,
            hr_avg REAL,
            hours REAL,
            steps_estimated INTEGER,
            distance_km REAL,
            source TEXT DEFAULT 'derived',
            confidence REAL,
            computed_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE,
            UNIQUE(athlete_id, date)
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_athlete_date ON daily_activity_classification(athlete_id, date)"
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS strava_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER,
            scope TEXT,
            athlete_name TEXT,
            created_at TEXT,
            updated_at TEXT,
            last_sync_ts INTEGER,
            tenant_id INTEGER DEFAULT 0,
            UNIQUE(athlete_id),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_strava_tokens_athlete ON strava_tokens(athlete_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS garmin_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER,
            scope TEXT,
            athlete_name TEXT,
            created_at TEXT,
            updated_at TEXT,
            tenant_id INTEGER DEFAULT 0,
            UNIQUE(athlete_id),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_garmin_tokens_athlete ON garmin_tokens(athlete_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS wahoo_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER,
            scope TEXT,
            athlete_name TEXT,
            created_at TEXT,
            updated_at TEXT,
            tenant_id INTEGER DEFAULT 0,
            UNIQUE(athlete_id),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wahoo_tokens_athlete ON wahoo_tokens(athlete_id)")
        conn.commit()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(rides)")
        ride_cols = [row[1] for row in cur.fetchall()]
        if "external_source" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN external_source TEXT")
        if "external_id" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN external_id TEXT")
        if "title" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN title TEXT")
        if "tenant_id" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN tenant_id INTEGER DEFAULT 0")
        if "weight_kg" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN weight_kg REAL DEFAULT 70")
        if "calories" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN calories REAL DEFAULT 0")
        if "heart_rate_avg" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN heart_rate_avg REAL")
        if "elevation_gain_m" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN elevation_gain_m REAL")
        if "gps_points" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN gps_points TEXT")
        if "activity_type" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN activity_type TEXT DEFAULT 'ride'")
        if "is_official" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN is_official INTEGER DEFAULT 1")
        if "source" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN source TEXT DEFAULT 'manual'")
        if "created_at" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN created_at TEXT")
        cur.execute("PRAGMA table_info(athletes)")
        athlete_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(chat_history)")
        chat_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in chat_cols:
            conn.execute("ALTER TABLE chat_history ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(calendar_events)")
        cal_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in cal_cols:
            conn.execute("ALTER TABLE calendar_events ADD COLUMN tenant_id INTEGER DEFAULT 0")
        if "weather_temp" not in cal_cols:
            conn.execute("ALTER TABLE calendar_events ADD COLUMN weather_temp REAL")
        if "weather_humidity" not in cal_cols:
            conn.execute("ALTER TABLE calendar_events ADD COLUMN weather_humidity REAL")
        if "weather_description" not in cal_cols:
            conn.execute("ALTER TABLE calendar_events ADD COLUMN weather_description TEXT")
        cur.execute("PRAGMA table_info(training_stress_days)")
        stress_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in stress_cols:
            conn.execute("ALTER TABLE training_stress_days ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(metrics)")
        metric_cols = [row[1] for row in cur.fetchall()]
        if "athlete_id" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN athlete_id INTEGER")
        if "fatigue_score" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN fatigue_score REAL")
        if "recovery_hours" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN recovery_hours REAL")
        if "calories_per_km" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN calories_per_km REAL")
        if "efficiency_score" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN efficiency_score REAL")
        if "created_at" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN created_at TEXT")
        if "tenant_id" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(training_goals)")
        goal_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in goal_cols:
            conn.execute("ALTER TABLE training_goals ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(planned_workouts)")
        workout_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in workout_cols:
            conn.execute("ALTER TABLE planned_workouts ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(athletes)")
        athlete_cols = [row[1] for row in cur.fetchall()]
        if "user_id" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN user_id INTEGER")
        cur.execute("PRAGMA table_info(rides)")
        ride_cols = [row[1] for row in cur.fetchall()]
        if "updated_at" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN updated_at TEXT")
        _ensure_external_identity_index(conn)
        _ensure_sync_tables(conn)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_consent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                consent_type TEXT NOT NULL,
                granted INTEGER NOT NULL DEFAULT 1,
                source TEXT DEFAULT 'web',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_consent_athlete ON user_consent(athlete_id, consent_type)")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS legal_acceptances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                acceptance_type TEXT NOT NULL,
                version TEXT NOT NULL,
                source TEXT DEFAULT 'web',
                created_at TEXT,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(  # noqa: E501
            "CREATE INDEX IF NOT EXISTS idx_legal_acceptances_athlete ON legal_acceptances(athlete_id, acceptance_type)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ai_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                response_length INTEGER DEFAULT 0,
                tool_calls INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_audit_athlete_created ON ai_audit_log(athlete_id, created_at)")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT DEFAULT '',
                chunk_id TEXT DEFAULT '',
                text TEXT DEFAULT '',
                word_count INTEGER DEFAULT 0,
                char_count INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                section TEXT,
                embedding TEXT,
                tenant_id INTEGER DEFAULT 0,
                created_at TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                resource_id INTEGER,
                details TEXT DEFAULT '{}',
                ip_address TEXT,
                created_at TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                refresh_token TEXT NOT NULL UNIQUE,
                jti TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT,
                revoked_at TEXT,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                start_index INTEGER NOT NULL,
                end_index INTEGER NOT NULL,
                distance_m REAL,
                avg_speed_kmh REAL,
                elevation_gain_m REAL,
                FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS pauses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                start_index INTEGER NOT NULL,
                end_index INTEGER NOT NULL,
                duration_seconds REAL,
                FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS external_identities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                athlete_id INTEGER,
                provider TEXT NOT NULL,
                external_id TEXT NOT NULL,
                external_email TEXT,
                display_name TEXT,
                picture_url TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(provider, external_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS external_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                athlete_id INTEGER,
                provider TEXT NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                expires_at TEXT,
                scope TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(athlete_id, provider),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS totp_secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                secret TEXT NOT NULL,
                enabled INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_athlete ON sessions(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_ride ON segments(ride_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pauses_ride ON pauses(ride_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_external_identity_provider ON external_identities(provider)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_external_identity_athlete ON external_identities(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_external_token_athlete ON external_tokens(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_external_token_provider ON external_tokens(provider)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_totp_user ON totp_secrets(user_id)")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                revoked_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS serpapi_usage (
                month TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT
            )"""
        )
        conn.commit()


def _ensure_sync_tables(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sync_entity_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            source TEXT DEFAULT 'device',
            reliability_score REAL DEFAULT 1.0,
            last_modified TEXT NOT NULL,
            sync_status TEXT DEFAULT 'local',
            sync_error TEXT,
            cloud_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(entity_type, entity_id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sync_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sync_conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            local_data TEXT NOT NULL,
            remote_data TEXT NOT NULL,
            local_reliability REAL NOT NULL,
            remote_reliability REAL NOT NULL,
            local_modified TEXT NOT NULL,
            remote_modified TEXT NOT NULL,
            resolution TEXT DEFAULT 'unresolved',
            resolved_data TEXT,
            resolution_reason TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_entity_state_type ON sync_entity_state(entity_type, sync_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_conflicts_resolution ON sync_conflicts(resolution)")


def _ensure_external_identity_index(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """SELECT COUNT(*) FROM (
            SELECT external_source, external_id, COUNT(*) AS duplicate_count
            FROM rides
            WHERE external_source IS NOT NULL AND external_id IS NOT NULL
            GROUP BY external_source, external_id
            HAVING COUNT(*) > 1
        )"""
    )
    if cur.fetchone()[0] == 0:
        conn.execute("DROP INDEX IF EXISTS ix_rides_external_source")
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_rides_external_identity
            ON rides (external_source, external_id)"""
        )


def _ensure_oauth_lock_table():
    with get_db_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS oauth_locks (
                lock_key TEXT PRIMARY KEY,
                acquired_at TEXT NOT NULL
            )"""
        )
        conn.commit()


def acquire_oauth_sqlite_lock(lock_key: str, ttl_seconds: int = 10) -> bool:
    _ensure_oauth_lock_table()
    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT OR IGNORE INTO oauth_locks (lock_key, acquired_at) VALUES (?, ?)",
                (lock_key, datetime.now(UTC).isoformat()),
            )
            conn.commit()
            return cur.rowcount > 0
        except sqlite3.OperationalError:
            return False


def release_oauth_sqlite_lock(lock_key: str):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM oauth_locks WHERE lock_key = ?", (lock_key,))
        conn.commit()


def _ensure_user_oauth_credentials_table() -> None:
    with get_db_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_oauth_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                client_id TEXT,
                client_secret TEXT,
                redirect_uri TEXT,
                scope TEXT,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        with suppress(Exception):
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_oauth_user_provider "
                "ON user_oauth_credentials(user_id, provider)"
            )


def _get_max_hr_setting(athlete_id: int) -> int | None:
    settings = get_hr_settings(athlete_id)
    if not settings:
        return None
    val = settings.get("max_hr")
    return int(val) if val is not None else None


def _get_resting_hr_setting(athlete_id: int) -> int | None:
    settings = get_hr_settings(athlete_id)
    if not settings:
        return None
    val = settings.get("resting_hr")
    return int(val) if val is not None else None


def _row_to_calendar_event(row) -> dict:
    keys = row.keys() if hasattr(row, "keys") else []

    def _col(name, default=None):
        return row[name] if name in keys else default

    return {
        "id": _col("id"),
        "athlete_id": _col("athlete_id", 0),
        "tenant_id": _col("tenant_id", 0),
        "title": _col("title"),
        "event_type": _col("event_type", "training"),
        "date": _col("date"),
        "duration_minutes": _col("duration_minutes", 0),
        "description": _col("description"),
        "completed": bool(_col("completed", False)),
        "weather_temp": _col("weather_temp"),
        "weather_humidity": _col("weather_humidity"),
        "weather_description": _col("weather_description"),
        "created_at": _col("created_at"),
    }


def create_indices():
    """Create performance indexes for rides and metrics tables."""
    with get_db_connection() as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_date ON rides(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_distance ON rides(distance_km)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_duration ON rides(duration_minutes)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_speed ON rides(avg_speed_kmh)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_athlete ON rides(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_athlete_date ON rides(athlete_id, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_ride ON metrics(ride_id)")
        _ensure_external_identity_index(conn)
        conn.commit()
    if DB_PATH != _INITIAL_DB_PATH:
        if not _s.database_url:
            _warn_sqlite_persistence("create_indices")
        conn = sqlite3.connect(_INITIAL_DB_PATH)
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS rides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    created_at TEXT
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    athlete_id INTEGER,
                    ride_id INTEGER,
                    fatigue_score REAL,
                    recovery_hours REAL,
                    calories_per_km REAL,
                    efficiency_score REAL,
                    created_at TEXT,
                    tenant_id INTEGER DEFAULT 0
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_date ON rides(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_distance ON rides(distance_km)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_duration ON rides(duration_minutes)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_speed ON rides(avg_speed_kmh)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_athlete ON rides(athlete_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_ride ON metrics(ride_id)")
            _ensure_external_identity_index(conn)
            conn.commit()
        finally:
            conn.close()


def backup_database(backup_path: str | None = None) -> str:
    """Copy the SQLite database to ``backup_path`` (or a timestamped default)."""
    import shutil
    from pathlib import Path

    if not _s.database_url:
        _warn_sqlite_persistence("backup_database")
    if not Path(DB_PATH).exists():
        raise FileNotFoundError(f"Database {DB_PATH} does not exist yet")
    if backup_path is None:
        backup_path = f"rides_backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def get_backup_dir() -> str:
    """Return the directory used for scheduled database backups."""
    return os.path.join(os.path.dirname(DB_PATH), "backups")


def rotate_backups(max_backups: int = 10) -> list[str]:
    """Remove oldest backups in the backup dir, keeping at most ``max_backups``."""
    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith("rides_backup_") and f.endswith(".db")],
        reverse=True,
    )
    removed = []
    for old_backup in backups[max_backups:]:
        old_path = os.path.join(backup_dir, old_backup)
        os.remove(old_path)
        removed.append(old_backup)
    return removed


def scheduled_backup(max_backups: int = 10) -> dict[str, dict]:
    """Run a scheduled backup with rotation.

    Creates a timestamped backup in the backups/ directory and rotates old backups.
    Returns a dict with backup_path, backups_kept, and backups_removed.
    """
    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"rides_backup_{timestamp}.db")
    backup_database(backup_path)
    removed = rotate_backups(max_backups)
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("rides_backup_")])
    logger.info("Scheduled backup completed: %s (kept %d, removed %d)", backup_path, len(backups), len(removed))
    return {
        "backup_path": backup_path,
        "backups_kept": len(backups),
        "backups_removed": len(removed),
        "removed_backups": removed,
    }


def get_athlete_by_query(**query):
    """Backward-compatible alias expected by some tests.

    Example: get_athlete_by_query(name="...")
    """

    from .api_compat import get_athlete_by_query as _shim  # noqa: I001

    import bike_analyzer.backend.db.database as db_mod

    return _shim(db_mod, **query)


def _row_to_poi(row) -> dict:
    keys = row.keys() if hasattr(row, "keys") else []

    def _col(name, default=None):
        return row[name] if name in keys else default

    photos = _col("photos")
    tags = _col("tags")
    return {
        "id": _col("id"),
        "name": _col("name"),
        "description": _col("description"),
        "lat": _col("lat"),
        "lon": _col("lon"),
        "type": _col("type"),
        "photos": json.loads(photos) if photos else [],
        "video_url": _col("video_url"),
        "difficulty_note": _col("difficulty_note"),
        "tags": json.loads(tags) if tags else [],
        "itinerary_id": _col("itinerary_id"),
        "created_by": _col("created_by"),
        "tenant_id": _col("tenant_id", 0),
        "created_at": _col("created_at"),
    }


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


def _beck_severity(total_score: int) -> str:
    if total_score <= 13:
        return "minimal"
    if total_score <= 19:
        return "mild"
    if total_score <= 28:
        return "moderate"
    return "severe"


def _row_to_sync_entity_state(row: tuple) -> dict:
    cols = (
        [d[0] for d in row.cursor_description]
        if hasattr(row, "cursor_description")
        else [
            "id",
            "entity_type",
            "entity_id",
            "source",
            "reliability_score",
            "last_modified",
            "sync_status",
            "sync_error",
            "cloud_id",
            "created_at",
            "updated_at",
        ]
    )
    data = dict(zip(cols, row, strict=False))
    return {
        "id": data.get("id"),
        "entity_type": data.get("entity_type"),
        "entity_id": data.get("entity_id"),
        "source": data.get("source", "device"),
        "reliability_score": data.get("reliability_score", 1.0),
        "last_modified": data.get("last_modified"),
        "sync_status": data.get("sync_status", "local"),
        "sync_error": data.get("sync_error"),
        "cloud_id": data.get("cloud_id"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }


__all__ = [
    "save_ride",
    "get_ride",
    "get_all_rides",
    "get_rides_by_athlete",
    "get_all_athletes",
    "delete_ride",
    "update_ride",
    "init_db",
    "save_athlete",
    "get_athlete",
    "get_athlete_by_name",
    "get_athlete_by_email",
    "get_athlete_by_query",
    "save_metric",
    "update_athlete",
    "create_indices",
    "backup_database",
    "get_db_connection",
    "save_chat_message",
    "get_chat_history",
    "clear_chat_history",
    "save_calendar_event",
    "get_calendar_event",
    "get_events_by_athlete",
    "get_events_by_date_range",
    "get_events_by_month",
    "update_calendar_event",
    "delete_calendar_event",
    "get_weather_cache",
    "save_weather_cache",
    "upsert_training_stress_day",
    "get_training_stress_days",
    "get_latest_training_stress",
    "save_road_incident",
    "save_route_safety_score",
    "get_route_safety_score",
    "save_poi",
    "get_poi",
    "get_nearby_pois",
    "list_pois",
    "delete_poi",
    "save_user",
    "get_user_by_username",
    "get_user_by_id",
    "seed_nutrition_food_items",
    "search_nutrition_food_items",
    "get_nutrition_food_item",
    "list_nutrition_categories",
    "save_nutrition_food_item",
    "update_nutrition_food_item",
    "delete_nutrition_food_item",
    "save_beck_assessment",
    "get_beck_assessment",
    "get_beck_assessments_by_athlete",
    "get_latest_beck_assessment",
    "get_metrics_by_athlete",
    "get_fitness_states_by_athlete",
    "get_food_logs_by_athlete",
    "register_ble_device",
    "get_ble_devices",
    "get_ble_device",
    "update_ble_device",
    "unregister_ble_device",
    "mark_ble_device_connected",
    "mark_ble_device_synced",
    "save_consent",
    "get_consent",
    "get_consents_by_athlete",
    "save_legal_acceptance",
    "get_legal_acceptances_by_athlete",
    "has_accepted_version",
    "save_ai_audit_log",
    "get_ai_audit_logs_by_athlete",
    "log_hr_sample",
    "log_hr_samples",
    "get_hr_24h_samples",
    "get_hr_daily_summary",
    "get_hr_settings",
    "upsert_hr_settings",
    "delete_hr_settings",
    "delete_hr_samples",
    "log_sensor_data",
    "classify_day",
    "get_activity_summary",
    "get_activity_classification",
    "save_strava_token",
    "get_strava_token",
    "revoke_strava_token",
    "update_strava_last_sync",
    "save_garmin_token",
    "get_garmin_token",
    "revoke_garmin_token",
    "save_wahoo_token",
    "get_wahoo_token",
    "revoke_wahoo_token",
    "save_google_token",
    "get_google_token",
    "delete_google_token",
    "connect_health_connect",
    "disconnect_health_connect",
    "get_health_connect_token",
    "update_health_connect_sync",
    "revoke_token",
    "is_token_revoked",
    "sweep_revoked_tokens",
    "save_sync_entity_state",
    "get_sync_entity_state",
    "save_sync_setting",
    "get_sync_setting",
    "save_sync_conflict",
    "get_pending_sync_entities",
    "get_sync_conflicts",
    "resolve_sync_conflict",
    "get_maps_usage",
    "record_maps_call",
]

