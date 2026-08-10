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

from ..analytics.calories import ensure_calories
from ..models.models import Ride
from ..settings import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

_s = get_settings()
DB_PATH = _s.db_path
_INITIAL_DB_PATH = DB_PATH


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

    max_retries = 3
    retry_delay = 0.1
    conn = None
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
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
        "CREATE INDEX IF NOT EXISTS ix_history_athlete_recorded "
        "ON athlete_history(athlete_id, recorded_at)"
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
                "CREATE INDEX IF NOT EXISTS ix_metric_log_athlete_metric "
                "ON athlete_metric_log(athlete_id, metric_type)"
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
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_pois_tenant_coords_name_type ON pois(tenant_id, lat, lon, name, type)")
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
            "CREATE INDEX IF NOT EXISTS idx_beck_assessments_athlete_date "
            "ON beck_assessments(athlete_id, created_at)"
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
            "CREATE INDEX IF NOT EXISTS idx_hr_samples_athlete_recorded "
            "ON hr_24h_samples(athlete_id, recorded_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hr_samples_athlete_date "
            "ON hr_24h_samples(athlete_id, date(recorded_at))"
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
            "CREATE INDEX IF NOT EXISTS idx_activity_athlete_date "
            "ON daily_activity_classification(athlete_id, date)"
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
            "CREATE INDEX IF NOT EXISTS idx_legal_acceptances_athlete "
            "ON legal_acceptances(athlete_id, acceptance_type)"
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
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sync_entity_state_type ON sync_entity_state(entity_type, sync_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sync_conflicts_resolution ON sync_conflicts(resolution)"
    )


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
    from .postgres_rides import has_postgres
    from .postgres_rides import save_ride as _pg_save_ride

    if has_postgres():
        return _pg_save_ride(ride)
    import time

    max_retries = 5
    retry_delay = 0.2
    last_error = None
    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                external_source = str(ride.get("external_source") or "").strip() or None
                external_id = str(ride.get("external_id") or "").strip() or None
                existing_ride_id = _find_existing_external_ride(conn, external_source, external_id)
                if existing_ride_id is not None:
                    return existing_ride_id
                if not ride.get("calories"):
                    try:
                        allowed = set(Ride.__dataclass_fields__.keys())
                        clean = {
                            k: v
                            for k, v in ride.items()
                            if k in allowed and k not in ("gps_points", "id")
                        }
                        ride["calories"] = ensure_calories(Ride(**clean))
                    except Exception:
                        logger.debug("Calorie estimate failed; storing 0", exc_info=True)
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


def get_ride(ride_id: int, tenant_id: int | None = None) -> dict | None:
    """Recupera una singola attivita' per id, opzionalmente filtrata per tenant.

    Restituisce un dict con tutti i campi della tabella ``rides`` oppure
    ``None`` se l'attivita' non esiste o non appartiene al tenant.
    """
    from .postgres_rides import get_ride as _pg_get_ride
    from .postgres_rides import has_postgres

    if has_postgres():
        return _pg_get_ride(ride_id, tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE id = ? AND tenant_id = ?", (ride_id, tenant_id))
        else:
            cur.execute("SELECT * FROM rides WHERE id = ?", (ride_id,))
        row = cur.fetchone()
        if row:
            return _row_to_ride(row)
        return None


def get_rides_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    """Restituisce tutte le attivita' di un atleta, opzionalmente filtrate per tenant.

    I risultati sono ordinati per id crescente (dal piu' vecchio al piu'
    recente). Usa ``_row_to_ride`` per deserializzare i punti GPS da JSON.
    """
    from .postgres_rides import get_rides_by_athlete as _pg_get_rides
    from .postgres_rides import has_postgres

    if has_postgres():
        return _pg_get_rides(athlete_id, tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ?", (athlete_id,))
        rows = cur.fetchall()
        return [_row_to_ride(r) for r in rows]


def get_athlete_by_name(name: str, tenant_id: int | None = None) -> dict | None:
    """Return the first athlete matching ``name``, optionally filtered by tenant."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM athletes WHERE name = ? AND tenant_id = ?", (name, tenant_id))
        else:
            cur.execute("SELECT * FROM athletes WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return _row_to_athlete(row)
        return None


def get_athlete_by_email(email: str, tenant_id: int | None = None) -> dict | None:
    """Return the first athlete matching ``email``, optionally filtered by tenant."""
    from .postgres_athlete import get_athlete_by_email as _pg_get_athlete_by_email
    from .postgres_athlete import has_postgres

    if has_postgres():
        return _pg_get_athlete_by_email(email, tenant_id)
    try:
        with get_db_connection() as conn:
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


def get_all_rides(athlete_id: int | None = None, tenant_id: int | None = None) -> list[dict]:
    """Return rides filtered by athlete and/or tenant, or all rides if none provided."""
    from .postgres_rides import get_all_rides as _pg_get_all
    from .postgres_rides import has_postgres

    if has_postgres():
        return _pg_get_all(athlete_id, tenant_id)
    with get_db_connection() as conn:
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


def delete_ride(ride_id: int, tenant_id: int | None = None) -> bool:
    """Delete a ride by id, optionally scoped to a tenant. Returns True if deleted."""
    from .postgres_rides import delete_ride as _pg_delete
    from .postgres_rides import has_postgres

    if has_postgres():
        return _pg_delete(ride_id, tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("DELETE FROM rides WHERE id = ? AND tenant_id = ?", (ride_id, tenant_id))
        else:
            cur.execute("DELETE FROM rides WHERE id = ?", (ride_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted


def update_ride(ride_id: int, ride: dict, tenant_id: int | None = None) -> bool:
    """Partially update an existing ride (PATCH semantics).

    Only the columns present in ``ride`` are written, so a NOT-NULL column (e.g.
    ``date``) is never clobbered with NULL when the caller passes a subset of
    fields. Returns True if a row was modified.
    """
    from .postgres_rides import has_postgres
    from .postgres_rides import update_ride as _pg_update

    if has_postgres():
        return _pg_update(ride_id, ride, tenant_id)
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
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            params += [ride_id, tenant_id]
            cur.execute(f"UPDATE rides SET {', '.join(assignments)} WHERE id = ? AND tenant_id = ?", params)
        else:
            params.append(ride_id)
            cur.execute(f"UPDATE rides SET {', '.join(assignments)} WHERE id = ?", params)
        conn.commit()
        return cur.rowcount > 0


def save_athlete(athlete: dict, athlete_id: int | None = None, tenant_id: int = 0, user_id: int | None = None) -> int:
    """Inserisce o aggiorna il profilo di un atleta.

    Se ``athlete_id`` e' fornito esegue un UPSERT (INSERT OR REPLACE)
    sovrascrivendo la riga esistente con lo stesso id. Altrimenti crea
    un nuovo atleta. Riprova fino a 5 volte su lock SQLite con backoff
    esponenziale. Restituisce l'id dell'atleta creato/aggiornato.
    """
    from .postgres_athlete import has_postgres
    from .postgres_athlete import save_athlete as _pg_save_athlete

    if has_postgres():
        return _pg_save_athlete(athlete, athlete_id, tenant_id, user_id)
    import time

    max_retries = 5
    retry_delay = 0.2
    last_error = None
    is_new = False
    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                if athlete_id is not None:
                    cur.execute("SELECT id FROM athletes WHERE id = ?", (athlete_id,))
                    is_new = cur.fetchone() is None
                else:
                    is_new = True
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
        "years_active",
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


def get_athlete(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    """Recupera il profilo di un atleta per id, opzionalmente filtrato per tenant.

    Restituisce un dict con tutti i campi della tabella ``athletes`` oppure
    ``None`` se l'atleta non esiste o non appartiene al tenant.
    """
    from .postgres_athlete import get_athlete as _pg_get_athlete
    from .postgres_athlete import has_postgres

    if has_postgres():
        return _pg_get_athlete(athlete_id, tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM athletes WHERE id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,))
        row = cur.fetchone()
        if row:
            return _row_to_athlete(row)
        return None


def save_metric(metric: dict, tenant_id: int = 0) -> int:
    """Insert a metrics row (fatigue, recovery, calories, efficiency) for a ride."""
    from .postgres_rides import has_postgres
    from .postgres_rides import save_metric as _pg_save_metric

    if has_postgres():
        return _pg_save_metric(metric, tenant_id)
    with get_db_connection() as conn:
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
                datetime.now(UTC).isoformat(),
                metric.get("tenant_id", tenant_id),
            ),
        )
        conn.commit()
        return cur.lastrowid


def save_athlete_snapshot(athlete: dict, tenant_id: int = 0, changed_by: int | None = None, conn=None) -> int:
    """Insert a full snapshot of the athlete state into athlete_history.

    Returns the id of the created snapshot. Excludes password_hash for security.
    """
    from .postgres_athlete import has_postgres
    from .postgres_athlete import save_athlete_snapshot as _pg_save_snapshot

    if has_postgres():
        return _pg_save_snapshot(athlete, tenant_id, changed_by)
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
        with get_db_connection() as conn:
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


def get_athlete_history(athlete_id: int, *, tenant_id: int | None = None, limit: int = 100) -> list[dict]:
    """Return the change history for an athlete, newest first."""
    from .postgres_athlete import get_athlete_history as _pg_get_history
    from .postgres_athlete import has_postgres

    if has_postgres():
        return _pg_get_history(athlete_id, tenant_id=tenant_id, limit=limit)
    with get_db_connection() as conn:
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


def update_athlete(athlete_id: int, athlete_data: dict) -> bool:
    """Merge ``athlete_data`` into the existing athlete row. Returns True if updated."""
    from .postgres_athlete import has_postgres
    from .postgres_athlete import update_athlete as _pg_update_athlete

    if has_postgres():
        return _pg_update_athlete(athlete_id, athlete_data)
    existing = get_athlete(athlete_id)
    if not existing:
        return False
    merged = {**existing, **athlete_data}
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
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
            password_hash=?, tenant_id=?, updated_at=? WHERE id=?""",
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


def get_athletes_by_user(user_id: int) -> list[dict]:
    """Restituisce tutti gli atleti di un utente ordinati per id."""
    from .postgres_athlete import get_athletes_by_user as _pg_get_athletes_by_user
    from .postgres_athlete import has_postgres

    if has_postgres():
        return _pg_get_athletes_by_user(user_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM athletes WHERE user_id = ? ORDER BY id", (user_id,))
        rows = cur.fetchall()
        return [_row_to_athlete(row) for row in rows]


def get_athlete_count_by_user(user_id: int) -> int:
    from .postgres_athlete import get_athlete_count_by_user as _pg_get_athlete_count_by_user
    from .postgres_athlete import has_postgres

    if has_postgres():
        return _pg_get_athlete_count_by_user(user_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM athletes WHERE user_id = ?", (user_id,))
        return cur.fetchone()[0]


def delete_athlete(athlete_id: int, user_id: int) -> bool:
    """Elimina un atleta se appartiene all'utente. Non elimina l'atleta principale se id==user_id."""
    from .postgres_athlete import delete_athlete as _pg_delete_athlete
    from .postgres_athlete import has_postgres

    if athlete_id == user_id:
        return False
    if has_postgres():
        return _pg_delete_athlete(athlete_id, user_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM athletes WHERE id = ? AND user_id = ?", (athlete_id, user_id))
        return cur.rowcount > 0


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


def get_user_oauth_credentials(user_id: int, provider: str) -> dict | None:
    _ensure_user_oauth_credentials_table()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM user_oauth_credentials WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        row = cur.fetchone()
        if row:
            creds = dict(row)
            if creds.get("client_secret"):
                try:
                    from ..db.token_crypto import decrypt_token
                    creds["client_secret"] = decrypt_token(creds["client_secret"])
                except Exception:
                    pass
            return creds
        return None


def get_all_user_oauth_credentials(user_id: int) -> list[dict]:
    _ensure_user_oauth_credentials_table()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_oauth_credentials WHERE user_id = ?", (user_id,))
        return [dict(r) for r in cur.fetchall()]


def save_user_oauth_credentials(user_id: int, provider: str, data: dict) -> None:
    _ensure_user_oauth_credentials_table()
    now = datetime.now(UTC).isoformat()
    client_secret = data.get("client_secret", "")
    if client_secret:
        try:
            from ..db.token_crypto import encrypt_token
            client_secret = encrypt_token(client_secret)
        except Exception:
            pass
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_oauth_credentials
               (user_id, provider, client_id, client_secret, redirect_uri,
                scope, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, provider) DO UPDATE SET
                   client_id = excluded.client_id,
                   client_secret = excluded.client_secret,
                   redirect_uri = excluded.redirect_uri,
                   scope = excluded.scope,
                   updated_at = excluded.updated_at""",
            (
                user_id,
                provider,
                data.get("client_id"),
                client_secret,
                data.get("redirect_uri"),
                data.get("scope"),
                now,
                now,
            ),
        )


def delete_user_oauth_credentials(user_id: int, provider: str) -> bool:
    _ensure_user_oauth_credentials_table()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_oauth_credentials WHERE user_id = ? AND provider = ?", (user_id, provider))
        return cur.rowcount > 0


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
    from .postgres_athlete import has_postgres
    from .postgres_athlete import log_athlete_metric as _pg_log_metric

    if has_postgres():
        return _pg_log_metric(
            athlete_id, metric_type, value, tenant_id=tenant_id, unit=unit,
            note=note, source=source, recorded_at=recorded_at,
        )
    if value is None:
        return 0
    if not recorded_at:
        recorded_at = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
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


def get_athlete_metric_log(
    athlete_id: int,
    metric_type: str,
    *,
    tenant_id: int | None = None,
    days: int = 365,
    limit: int = 2000,
) -> list[dict]:
    """Return the time series for one metric, oldest-first, for charting."""
    from .postgres_athlete import get_athlete_metric_log as _pg_get_log
    from .postgres_athlete import has_postgres

    if has_postgres():
        return _pg_get_log(
            athlete_id, metric_type, tenant_id=tenant_id, days=days, limit=limit
        )
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    with get_db_connection() as conn:
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


def log_hr_sample(
    athlete_id: int,
    heart_rate: int,
    *,
    source: str = "ble",
    device_id: str | None = None,
    recorded_at: str | None = None,
    tenant_id: int = 0,
) -> int:
    """Append a single heart-rate sample to the 24h tracking table.

    ``recorded_at`` is stored as an ISO-8601 UTC timestamp so samples can be
    aggregated by hour / day when rendering the 24h chart.
    """
    if heart_rate <= 0 or heart_rate > 300:
        return 0
    if not recorded_at:
        recorded_at = datetime.now(UTC).isoformat()
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hr_24h_samples
               (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def log_hr_samples(
    athlete_id: int,
    samples: list[dict[str, Any]],
    *,
    source: str = "ble",
    tenant_id: int = 0,
) -> int:
    """Bulk-insert heart-rate samples for 24h tracking.

    Each sample dict accepts: ``heart_rate`` (int), ``recorded_at`` (ISO),
    ``device_id`` (optional str).
    """
    if not samples:
        return 0
    now = datetime.now(UTC).isoformat()
    rows: list[tuple[Any, ...]] = []
    for s in samples:
        hr = s.get("heart_rate")
        if hr is None or hr < 0 or hr > 300:
            continue
        rows.append(
            (
                athlete_id,
                tenant_id,
                int(hr),
                s.get("source", source),
                s.get("device_id"),
                s.get("recorded_at") or now,
                now,
            )
        )
    if not rows:
        return 0
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            """INSERT INTO hr_24h_samples
               (athlete_id, tenant_id, heart_rate, source, device_id, recorded_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return int(cur.rowcount)


def get_hr_24h_samples(
    athlete_id: int,
    hours: int = 24,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    """Return raw heart-rate samples for the last *hours* hours (oldest-first)."""
    since = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                """SELECT id, heart_rate, source, device_id, recorded_at
                   FROM hr_24h_samples
                   WHERE athlete_id = ? AND tenant_id = ?
                     AND recorded_at >= ?
                   ORDER BY recorded_at ASC""",
                (athlete_id, tenant_id, since),
            )
        else:
            cur.execute(
                """SELECT id, heart_rate, source, device_id, recorded_at
                   FROM hr_24h_samples
                   WHERE athlete_id = ?
                     AND recorded_at >= ?
                   ORDER BY recorded_at ASC""",
                (athlete_id, since),
            )
        rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "heart_rate": r[1],
            "source": r[2],
            "device_id": r[3],
            "recorded_at": r[4],
        }
        for r in rows
    ]


def get_hr_daily_summary(
    athlete_id: int,
    days: int = 30,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    """Return per-day resting / average / max / min HR for the last *days* days."""
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_db_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT date(recorded_at) as day,
                   MIN(heart_rate) as resting_hr,
                   ROUND(AVG(heart_rate), 1) as avg_hr,
                   MAX(heart_rate) as max_hr,
                   COUNT(*) as sample_count
            FROM hr_24h_samples
            WHERE athlete_id = ?
              AND date(recorded_at) >= ?
        """
        params: list[Any] = [athlete_id, since]
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        sql += " GROUP BY date(recorded_at) ORDER BY day ASC"
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [
        {
            "day": r[0],
            "resting_hr": r[1],
            "avg_hr": r[2],
            "max_hr": r[3],
            "min_hr": r[1],
            "sample_count": r[4],
        }
        for r in rows
    ]


def get_hr_settings(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    """Return HR 24h monitoring settings for an athlete."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM hr_monitoring_settings WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM hr_monitoring_settings WHERE athlete_id = ?",
                (athlete_id,),
            )
        row = cur.fetchone()
    if not row:
        return None
    return dict(row)


def upsert_hr_settings(athlete_id: int, settings: dict, *, tenant_id: int = 0) -> dict:
    """Create or update HR 24h monitoring settings."""
    now = datetime.now(UTC).isoformat()
    allowed = {
        "enabled",
        "interval_seconds",
        "source",
        "device_id",
        "max_hr",
        "resting_hr",
        "tenant_id",
    }
    clean = {k: v for k, v in settings.items() if k in allowed}
    clean.setdefault("athlete_id", athlete_id)
    clean.setdefault("tenant_id", tenant_id)
    clean.setdefault("created_at", now)
    clean.setdefault("updated_at", now)
    cols = list(clean.keys())
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c not in ("athlete_id", "tenant_id"))
    if not updates:
        updates = "updated_at = excluded.updated_at"
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""INSERT INTO hr_monitoring_settings ({col_names})
                VALUES ({placeholders})
                ON CONFLICT(athlete_id) DO UPDATE SET {updates}""",
            [clean[c] for c in cols],
        )
        conn.commit()
    return get_hr_settings(athlete_id, tenant_id) or dict(clean)


def delete_hr_settings(athlete_id: int, tenant_id: int | None = None) -> bool:
    """Delete HR 24h monitoring settings for an athlete."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "DELETE FROM hr_monitoring_settings WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "DELETE FROM hr_monitoring_settings WHERE athlete_id = ?",
                (athlete_id,),
            )
        conn.commit()
        return cur.rowcount > 0


def delete_hr_samples(athlete_id: int, *, tenant_id: int | None = None, older_than: str | None = None) -> int:
    """Delete HR samples, optionally filtered by age (ISO string). Returns deleted count."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None and older_than:
            cur.execute(
                "DELETE FROM hr_24h_samples WHERE athlete_id = ? AND tenant_id = ? AND recorded_at < ?",
                (athlete_id, tenant_id, older_than),
            )
        elif tenant_id is not None:
            cur.execute(
                "DELETE FROM hr_24h_samples WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        elif older_than:
            cur.execute(
                "DELETE FROM hr_24h_samples WHERE athlete_id = ? AND recorded_at < ?",
                (athlete_id, older_than),
            )
        else:
            cur.execute("DELETE FROM hr_24h_samples WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return int(cur.rowcount)


def log_sensor_data(
    athlete_id: int,
    samples: list[dict[str, Any]],
    *,
    tenant_id: int = 0,
) -> int:
    """Bulk-insert raw BLE sensor readings (heart-rate, GPS, accelerometer)."""
    if not samples:
        return 0
    rows: list[tuple[Any, ...]] = []
    for s in samples:
        ts = s.get("ts") or s.get("recorded_at") or datetime.now(UTC).isoformat()
        rows.append(
            (
                athlete_id,
                tenant_id,
                ts,
                s.get("heart_rate"),
                s.get("lat"),
                s.get("lng"),
                s.get("altitude"),
                s.get("accel_x"),
                s.get("accel_y"),
                s.get("accel_z"),
                s.get("speed_kmh"),
            )
        )
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            """INSERT INTO sensor_data
               (athlete_id, tenant_id, ts, heart_rate, lat, lng, altitude,
                accel_x, accel_y, accel_z, speed_kmh)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return int(cur.rowcount)


def classify_day(
    athlete_id: int,
    for_date: str,
    *,
    tenant_id: int = 0,
) -> dict:
    """Compute the activity classification for a single calendar day.

    Combines HR 24h samples, GPS movement (rides) and metabolic summaries to
    derive an autonomous label: ``sleep``, ``recovery``, ``active`` or
    ``rest``.  Results are persisted into ``daily_activity_classification``.
    """
    date_start = for_date

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT MIN(heart_rate) as resting_hr,
                      ROUND(AVG(heart_rate), 1) as avg_hr,
                      MAX(heart_rate) as max_hr,
                      COUNT(*) as sample_count
               FROM hr_24h_samples
               WHERE athlete_id = ? AND date(recorded_at) = ?""",
            (athlete_id, date_start),
        )
        hr_row = cur.fetchone()
        resting_hr = hr_row[0] if hr_row and hr_row[0] is not None else None
        avg_hr = hr_row[1] if hr_row and hr_row[1] is not None else None
        sample_count = hr_row[3] if hr_row and hr_row[3] is not None else 0

        cur.execute(
            """SELECT ROUND(SUM(distance_km), 2) as total_km,
                      SUM(duration_minutes) as total_min,
                      ROUND(SUM(calories), 0) as total_cal,
                      COUNT(*) as rides_count
               FROM rides
               WHERE athlete_id = ? AND date(date) = ?""",
            (athlete_id, date_start),
        )
        ride_row = cur.fetchone()
        distance_km = ride_row[0] if ride_row and ride_row[0] is not None else 0.0
        rides_count = ride_row[3] if ride_row and ride_row[3] is not None else 0
        calories = ride_row[2] if ride_row and ride_row[2] is not None else 0

        cur.execute(
            """SELECT steps_estimated, tdee_kcal, neat_kcal, intake_kcal
               FROM metabolic_daily_summaries
               WHERE athlete_id = ? AND date = ? AND tenant_id = ?""",
            (athlete_id, date_start, tenant_id),
        )
        meta_row = cur.fetchone()

    # Heuristic thresholds
    high_activity_steps = 2000
    high_activity_km = 1.0
    sleep_threshold_ratio = 0.55
    max_setting = _get_max_hr_setting(athlete_id)
    resting_setting = _get_resting_hr_setting(athlete_id)

    steps_estimated = int(meta_row[0]) if meta_row and meta_row[0] else 0

    # Determine label
    is_sleep_day = (
        resting_hr is not None
        and resting_setting is not None
        and sample_count > 0
        and avg_hr is not None
        and max_setting is not None
        and resting_hr >= int(resting_setting * 0.85)
        and avg_hr < max_setting * sleep_threshold_ratio
    )
    is_active = steps_estimated >= high_activity_steps or distance_km >= high_activity_km
    is_recovery = (
        not is_active
        and resting_setting is not None
        and resting_hr is not None
        and resting_hr <= resting_setting + 5
    )

    if is_sleep_day and not is_active:
        label = "sleep"
    elif is_active:
        label = "active"
    elif is_recovery:
        label = "recovery"
    else:
        label = "rest"

    confidence = 0.85 if is_active else (0.75 if is_recovery else 0.60)
    hours = round(calories / 50.0, 1) if calories else 0.0  # rough estimate

    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO daily_activity_classification
               (athlete_id, tenant_id, date, label, hr_resting, hr_avg,
                hours, steps_estimated, distance_km, source, confidence, computed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(athlete_id, date) DO UPDATE SET
               label = excluded.label,
               hr_resting = excluded.hr_resting,
               hr_avg = excluded.hr_avg,
               hours = excluded.hours,
               steps_estimated = excluded.steps_estimated,
               distance_km = excluded.distance_km,
               confidence = excluded.confidence,
               computed_at = excluded.computed_at""",
            (
                athlete_id,
                tenant_id,
                date_start,
                label,
                resting_hr,
                avg_hr,
                hours,
                steps_estimated,
                distance_km,
                "derived",
                confidence,
                now,
            ),
        )
        conn.commit()

    return {
        "date": date_start,
        "label": label,
        "hr_resting": resting_hr,
        "hr_avg": avg_hr,
        "hours": hours,
        "steps_estimated": steps_estimated,
        "distance_km": distance_km,
        "rides_count": rides_count,
        "confidence": round(confidence, 2),
    }


def get_activity_summary(
    athlete_id: int,
    days: int = 30,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    """Return daily activity classifications for the last *days* days."""
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_db_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT date, label, hr_resting, hr_avg, hours,
                   steps_estimated, distance_km, confidence
            FROM daily_activity_classification
            WHERE athlete_id = ? AND date >= ?
        """
        params: list[Any] = [athlete_id, since]
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        sql += " ORDER BY date ASC"
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [
        {
            "date": r[0],
            "label": r[1],
            "hr_resting": r[2],
            "hr_avg": r[3],
            "hours": r[4],
            "steps_estimated": r[5],
            "distance_km": r[6],
            "confidence": r[7],
        }
        for r in rows
    ]


def get_activity_classification(
    athlete_id: int,
    for_date: str,
    *,
    tenant_id: int = 0,
) -> dict | None:
    """Return the persisted activity classification for a single day."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT date, label, hr_resting, hr_avg, hours,
                      steps_estimated, distance_km, confidence
               FROM daily_activity_classification
               WHERE athlete_id = ? AND date = ? AND tenant_id = ?""",
            (athlete_id, for_date, tenant_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "date": row[0],
        "label": row[1],
        "hr_resting": row[2],
        "hr_avg": row[3],
        "hours": row[4],
        "steps_estimated": row[5],
        "distance_km": row[6],
        "confidence": row[7],
    }


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


def save_metabolic_profile(profile: dict, athlete_id: int, tenant_id: int = 0) -> int:
    """Upsert metabolic profile for an athlete."""
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
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


def get_metabolic_profile(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    """Recupera il profilo metabolico di un atleta."""
    with get_db_connection() as conn:
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


def save_food_log(log: dict, tenant_id: int = 0) -> int:
    """Inserisce un nuovo log alimentare."""
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
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


def get_food_logs_by_athlete_date(
    athlete_id: int,
    date: str,
    *,
    tenant_id: int | None = None,
) -> list[dict]:
    """Restituisce i log alimentari di un atleta per una data specifica."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM food_logs WHERE athlete_id = ? AND date = ? "
                "AND tenant_id = ? ORDER BY recorded_at ASC",
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


def update_food_log(log_id: int, log_data: dict) -> bool:
    """Aggiorna un log alimentare esistente."""
    existing = get_food_log(log_id)
    if not existing:
        return False
    merged = {**existing, **log_data}
    with get_db_connection() as conn:
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


def get_food_log(log_id: int) -> dict | None:
    """Recupera un singolo log alimentare per id."""
    with get_db_connection() as conn:
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


def delete_food_log(log_id: int) -> bool:
    """Elimina un log alimentare."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM food_logs WHERE id = ?", (log_id,))
        conn.commit()
        return cur.rowcount > 0


def save_metabolic_daily_summary(summary: dict, tenant_id: int = 0) -> int:
    """Upsert metabolic daily summary for an athlete on a specific date."""
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
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
    with get_db_connection() as conn:
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


def get_metabolic_daily_summary(
    athlete_id: int,
    date: str,
    tenant_id: int | None = None,
) -> dict | None:
    """Recupera il riepilogo metabolico per una data specifica."""
    with get_db_connection() as conn:
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


def upsert_metabolic_reference_value(value: dict, tenant_id: int = 0) -> int:
    """Upsert a reference (mean) metabolic value for a demographic bracket."""
    now = datetime.now(UTC).isoformat()
    sex = value.get("sex", "male")
    alo = int(value.get("age_bracket_lo", 0))
    ahi = int(value.get("age_bracket_hi", 0))
    wlo = int(value.get("weight_bracket_lo", 0))
    whi = int(value.get("weight_bracket_hi", 0))
    activity_level = value.get("activity_level", "moderate")
    with get_db_connection() as conn:
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


def get_metabolic_reference_value(
    sex: str, age: int, weight_kg: float,
    activity_level: str = "moderate", tenant_id: int = 0,
) -> dict | None:
    """Return the imported reference row for the bracket closest to age/weight."""
    from ...core.calculators.metabolism import age_bracket, weight_bracket

    a_lo, a_hi = age_bracket(age)
    w_lo, w_hi = weight_bracket(weight_kg)
    with get_db_connection() as conn:
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


def get_all_metabolic_reference_values(tenant_id: int | None = None) -> list[dict]:
    """Return all imported reference values, optionally filtered by tenant."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM metabolic_reference_values WHERE tenant_id = ? ORDER BY id", (tenant_id,))
        else:
            cur.execute("SELECT * FROM metabolic_reference_values ORDER BY id")
        return [dict(row) for row in cur.fetchall()]


def save_metabolic_adaptive_weights(weights: dict, athlete_id: int, tenant_id: int = 0) -> int:
    """Upsert per-athlete adaptive model weights and sensor confidence."""
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
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


def get_metabolic_adaptive_weights(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    """Return the per-athlete adaptive weights, if any."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM metabolic_adaptive_weights "
                "WHERE athlete_id = ? AND tenant_id = ?",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute("SELECT * FROM metabolic_adaptive_weights WHERE athlete_id = ?", (athlete_id,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)


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


def save_chat_message(athlete_id: int | None, role: str, content: str, tenant_id: int = 0) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO chat_history (athlete_id, role, content, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?)""",
            (athlete_id, role, content, datetime.now(UTC).isoformat(), tenant_id),
        )
        conn.commit()
        return cur.lastrowid


def get_chat_history(athlete_id: int, limit: int = 10, tenant_id: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT role, content, created_at FROM chat_history "
                "WHERE athlete_id = ? AND tenant_id = ? ORDER BY id DESC LIMIT ?",
                (athlete_id, tenant_id, limit),
            )
        else:
            cur.execute(
                "SELECT role, content, created_at FROM chat_history WHERE athlete_id = ? ORDER BY id DESC LIMIT ?",
                (athlete_id, limit),
            )
        rows = cur.fetchall()
        return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]


def clear_chat_history(athlete_id: int, tenant_id: int | None = None) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("DELETE FROM chat_history WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("DELETE FROM chat_history WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return cur.rowcount > 0


def prune_chat_history(athlete_id: int, tenant_id: int | None = None, retention_days: int = 90) -> int:
    from datetime import datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "DELETE FROM chat_history WHERE athlete_id = ? AND tenant_id = ? AND created_at < ?",
                (athlete_id, tenant_id, cutoff.isoformat()),
            )
        else:
            cur.execute(
                "DELETE FROM chat_history WHERE athlete_id = ? AND created_at < ?",
                (athlete_id, cutoff.isoformat()),
            )
        conn.commit()
        return cur.rowcount


def get_all_athletes() -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, experience_level FROM athletes")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "email": r[2], "experience_level": r[3]} for r in rows]


def save_calendar_event(event: dict, tenant_id: int = 0) -> int:
    weather = {}
    if event.get("lat") is not None and event.get("lon") is not None:
        from ..weather.weather_service import get_forecast_for_date

        try:
            weather = get_forecast_for_date(float(event["lat"]), float(event["lon"]), event.get("date", ""))
            if "error" in weather:
                weather = {}
        except Exception:
            weather = {}

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO calendar_events
            (athlete_id, title, event_type, date, duration_minutes,
             description, completed, weather_temp, weather_humidity,
             weather_description, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.get("athlete_id"),
                event.get("title"),
                event.get("event_type", "training"),
                event.get("date"),
                event.get("duration_minutes", 0),
                event.get("description"),
                1 if event.get("completed") else 0,
                weather.get("temperature"),
                weather.get("humidity"),
                weather.get("description"),
                datetime.now(UTC).isoformat(),
                event.get("tenant_id", tenant_id),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_calendar_event(event_id: int) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,))
        row = cur.fetchone()
        if row:
            return _row_to_calendar_event(row)
        return None


def get_events_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM calendar_events WHERE athlete_id = ? AND tenant_id = ? ORDER BY date DESC",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM calendar_events WHERE athlete_id = ? ORDER BY date DESC",
                (athlete_id,),
            )
        rows = cur.fetchall()
        return [_row_to_calendar_event(r) for r in rows]


def get_events_by_date_range(
    athlete_id: int, start_date: str, end_date: str, tenant_id: int | None = None
) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM calendar_events WHERE athlete_id = ? AND tenant_id = ? "
                "AND date >= ? AND date <= ? ORDER BY date ASC",
                (athlete_id, tenant_id, start_date, end_date),
            )
        else:
            cur.execute(
                "SELECT * FROM calendar_events WHERE athlete_id = ? AND date >= ? AND date <= ? ORDER BY date ASC",
                (athlete_id, start_date, end_date),
            )
        rows = cur.fetchall()
        return [_row_to_calendar_event(r) for r in rows]


def get_events_by_month(athlete_id: int, year: int, month: int, tenant_id: int | None = None) -> list[dict]:
    next_month = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    month_start = f"{year}-{month:02d}-01"
    return get_events_by_date_range(athlete_id, month_start, next_month, tenant_id)


def update_calendar_event(event_id: int, event_data: dict, tenant_id: int | None = None) -> bool:
    existing = get_calendar_event(event_id)
    if not existing:
        return False
    merged = {**existing, **event_data}
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                """UPDATE calendar_events
                SET title=?, event_type=?, date=?, duration_minutes=?,
                description=?, completed=?, weather_temp=?, weather_humidity=?,
                weather_description=? WHERE id=? AND tenant_id=?""",
                (
                    merged.get("title"),
                    merged.get("event_type", "training"),
                    merged.get("date"),
                    merged.get("duration_minutes", 0),
                    merged.get("description"),
                    1 if merged.get("completed") else 0,
                    merged.get("weather_temp"),
                    merged.get("weather_humidity"),
                    merged.get("weather_description"),
                    event_id,
                    tenant_id,
                ),
            )
        else:
            cur.execute(
                """UPDATE calendar_events
                SET title=?, event_type=?, date=?, duration_minutes=?,
                description=?, completed=?, weather_temp=?, weather_humidity=?,
                weather_description=? WHERE id=?""",
                (
                    merged.get("title"),
                    merged.get("event_type", "training"),
                    merged.get("date"),
                    merged.get("duration_minutes", 0),
                    merged.get("description"),
                    1 if merged.get("completed") else 0,
                    merged.get("weather_temp"),
                    merged.get("weather_humidity"),
                    merged.get("weather_description"),
                    event_id,
                ),
            )
        conn.commit()
        return cur.rowcount > 0


def delete_calendar_event(event_id: int, tenant_id: int | None = None) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("DELETE FROM calendar_events WHERE id = ? AND tenant_id = ?", (event_id, tenant_id))
        else:
            cur.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted


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


def get_weather_cache(lat: float, lon: float, date: str) -> dict | None:
    """Get cached weather data for coordinates and date."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT temperature, humidity, description, cached_at FROM weather_cache WHERE lat=? AND lon=? AND date=?",
            (lat, lon, date),
        )
        row = cur.fetchone()
        if row:
            return {
                "temperature": row[0],
                "humidity": row[1],
                "description": row[2],
                "cached_at": row[3],
            }
        return None


def save_weather_cache(lat: float, lon: float, date: str, weather: dict) -> int:
    """Save weather data to cache."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO weather_cache
            (lat, lon, date, temperature, humidity, description, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                lat,
                lon,
                date,
                weather.get("temperature"),
                weather.get("humidity"),
                weather.get("description"),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def upsert_training_stress_day(
    athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float, tenant_id: int = 0
) -> None:
    from .postgres_rides import has_postgres
    from .postgres_rides import upsert_training_stress_day as _pg_upsert

    if has_postgres():
        return _pg_upsert(athlete_id, date, tss, atl, ctl, tsb, tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cur.execute(
            """INSERT INTO training_stress_days
            (athlete_id, date, tss, atl, ctl, tsb, created_at, updated_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
            tss=excluded.tss, atl=excluded.atl, ctl=excluded.ctl,
            tsb=excluded.tsb, updated_at=excluded.updated_at, tenant_id=excluded.tenant_id""",
            (athlete_id, date, tss, atl, ctl, tsb, now, now, tenant_id),
        )
        conn.commit()


def save_user(user: dict) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO users (username, email, password_hash, is_admin,
             is_client, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user.get("username"),
                user.get("email"),
                user.get("password_hash"),
                1 if user.get("is_admin") else 0,
                1 if user.get("is_client") else 0,
                1 if user.get("is_active", True) else 0,
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_user_by_username(username: str) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "password_hash": row[3],
                "is_admin": bool(row[4]),
                "is_client": bool(row[5]),
                "is_active": bool(row[6]),
                "created_at": row[7],
                "updated_at": row[8],
            }
        return None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "password_hash": row[3],
                "is_admin": bool(row[4]),
                "is_client": bool(row[5]),
                "is_active": bool(row[6]),
                "created_at": row[7],
                "updated_at": row[8],
            }
        return None


def get_all_users() -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, is_admin, is_client, is_active, created_at, updated_at FROM users ORDER BY id DESC")
        rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "is_admin": bool(row[3]),
                "is_client": bool(row[4]),
                "is_active": bool(row[5]),
                "created_at": row[6],
                "updated_at": row[7],
            }
            for row in rows
        ]


def update_user(user_id: int, updates: dict) -> dict | None:
    allowed = {"email", "password_hash", "is_admin", "is_client", "is_active"}
    fields = []
    values = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        if key in ("is_admin", "is_client", "is_active"):
            value = 1 if value else 0
        fields.append(f"{key} = ?")
        values.append(value)
    if not fields:
        return get_user_by_id(user_id)
    values.append(datetime.now(UTC).isoformat())
    values.append(user_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET {', '.join(fields)}, updated_at = ? WHERE id = ?", values)
        conn.commit()
    return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0


def get_training_stress_days(athlete_id: int, limit: int = 90, tenant_id: int | None = None) -> list[dict]:
    from .postgres_rides import get_training_stress_days as _pg_get_stress
    from .postgres_rides import has_postgres

    if has_postgres():
        return _pg_get_stress(athlete_id, limit, tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? AND tenant_id = ? "
                "ORDER BY date DESC LIMIT ?",
                (athlete_id, tenant_id, limit),
            )
        else:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? "
                "ORDER BY date DESC LIMIT ?",
                (athlete_id, limit),
            )
        rows = cur.fetchall()
        return [{"date": r[0], "tss": r[1], "atl": r[2], "ctl": r[3], "tsb": r[4]} for r in rows]


def get_latest_training_stress(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    from .postgres_rides import get_latest_training_stress as _pg_get_latest
    from .postgres_rides import has_postgres

    if has_postgres():
        return _pg_get_latest(athlete_id, tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? AND tenant_id = ? "
                "ORDER BY date DESC LIMIT 1",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? "
                "ORDER BY date DESC LIMIT 1",
                (athlete_id,),
            )
        row = cur.fetchone()
        if row:
            return {
                "date": row[0],
                "tss": row[1],
                "atl": row[2],
                "ctl": row[3],
                "tsb": row[4],
            }
        return None


def recalculate_training_stress_for_athlete(athlete_id: int, ftp: float = 250.0, tenant_id: int = 0) -> None:
    """Ricalcola ATL/CTL/TSB storici per tutti i giorni con attivita' dell'atleta.

    Per ogni giorno calcola il TSS cumulato, poi applica due EWMA:
    - ATL ( Acute Training Load ) con tau di 7 giorni.
    - CTL ( Chronic Training Load ) con tau di 42 giorni.
    Il TSB ( Form ) e' la differenza CTL - ATL.

    I risultati vengono salvati/aggiornati nella tabella
    ``training_stress_days`` tramite ``upsert_training_stress_day``.
    """
    from ..analytics.training_stress import (
        estimate_tss,
        exponentially_weighted_moving_average,
    )

    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id, tenant_id)]
    if not rides:
        return
    daily: dict[str, float] = {}
    for ride in rides:
        tss = estimate_tss(ride, ftp=ftp)
        day = ride.date[:10] if ride.date else "unknown"
        daily[day] = daily.get(day, 0.0) + tss
    sorted_days = sorted(daily.items())
    tss_series = [v for _, v in sorted_days]
    atl_series = [
        exponentially_weighted_moving_average(tss_series[: i + 1], tau_days=7.0) for i in range(len(tss_series))
    ]
    ctl_series = [
        exponentially_weighted_moving_average(tss_series[: i + 1], tau_days=42.0) for i in range(len(tss_series))
    ]
    for i, (date_str, _) in enumerate(sorted_days):
        tsb = round(ctl_series[i] - atl_series[i], 1)
        upsert_training_stress_day(
            athlete_id,
            date_str,
            round(tss_series[i], 1),
            atl_series[i],
            ctl_series[i],
            tsb,
            tenant_id,
        )


def save_road_incident(incident: dict) -> int:
    with get_db_connection() as conn:
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


def save_route_safety_score(score_data: dict, tenant_id: int = 0) -> int:
    with get_db_connection() as conn:
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


def get_route_safety_score(ride_id: int, tenant_id: int | None = None) -> dict | None:
    with get_db_connection() as conn:
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


def save_poi(poi: dict) -> int:
    """Create a Point of Interest. Returns the new row id."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM pois WHERE tenant_id = ? AND lat = ? AND lon = ? AND name = ? AND type = ?",
            (
                poi.get("tenant_id", 0),
                poi.get("lat"),
                poi.get("lon"),
                poi.get("name"),
                poi.get("type"),
            ),
        )
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            """INSERT INTO pois
            (name, description, lat, lon, type, photos, video_url,
             difficulty_note, tags, itinerary_id, created_by, tenant_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                poi.get("name"),
                poi.get("description"),
                poi.get("lat"),
                poi.get("lon"),
                poi.get("type"),
                json.dumps(poi.get("photos", [])),
                poi.get("video_url"),
                poi.get("difficulty_note"),
                json.dumps(poi.get("tags", [])),
                poi.get("itinerary_id"),
                poi.get("created_by"),
                poi.get("tenant_id", 0),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_poi(poi_id: int, tenant_id: int | None = None) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM pois WHERE id = ? AND tenant_id = ?", (poi_id, tenant_id))
        else:
            cur.execute("SELECT * FROM pois WHERE id = ?", (poi_id,))
        row = cur.fetchone()
        return _row_to_poi(row) if row else None


def get_nearby_pois(lat: float, lon: float, radius_km: float = 5.0, tenant_id: int | None = None) -> list[dict]:
    """Return POIs within ``radius_km`` of (lat, lon) using the haversine distance.

    A coarse lat/lon bounding box narrows the candidate set before the exact
    distance filter, which keeps the query efficient without PostGIS.

    When ``tenant_id`` is provided, only POIs belonging to that tenant are
    returned, preventing cross-tenant GPS data disclosure.
    """
    from ...core.models import haversine_distance_m

    radius_m = max(0.0, radius_km) * 1000.0
    delta_lat = radius_km / 111.0
    delta_lon = radius_km / (111.320 * max(0.000001, abs(math.cos(math.radians(lat)))))

    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM pois WHERE tenant_id = ? AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?",
                (tenant_id, lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
            )
        else:
            cur.execute(
                "SELECT * FROM pois WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?",
                (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
            )
        rows = cur.fetchall()

    nearby = []
    for row in rows:
        poi = _row_to_poi(row)
        distance_m = haversine_distance_m(lat, lon, poi["lat"], poi["lon"])
        if distance_m <= radius_m:
            poi["distance_m"] = round(distance_m)
            nearby.append(poi)
    nearby.sort(key=lambda p: p["distance_m"])
    return nearby


def list_pois(itinerary_id: int | None = None, tenant_id: int | None = None) -> list[dict]:
    """Return all POIs, optionally filtered by ``itinerary_id`` and/or ``tenant_id``.

    When ``tenant_id`` is provided, only POIs belonging to that tenant are
    returned, preventing cross-tenant data disclosure.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        if itinerary_id is not None and tenant_id is not None:
            cur.execute(
                "SELECT * FROM pois WHERE itinerary_id = ? AND tenant_id = ? ORDER BY id DESC",
                (itinerary_id, tenant_id),
            )
        elif itinerary_id is not None:
            cur.execute(
                "SELECT * FROM pois WHERE itinerary_id = ? ORDER BY id DESC",
                (itinerary_id,),
            )
        elif tenant_id is not None:
            cur.execute(
                "SELECT * FROM pois WHERE tenant_id = ? ORDER BY id DESC",
                (tenant_id,),
            )
        else:
            cur.execute("SELECT * FROM pois ORDER BY id DESC")
        rows = cur.fetchall()
    return [_row_to_poi(r) for r in rows]


def delete_poi(poi_id: int) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM pois WHERE id = ?", (poi_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted


def save_itinerary(itinerary: dict) -> int:
    """Create an itinerary. Returns the new row id."""
    from .postgres_itineraries import has_postgres
    from .postgres_itineraries import save_itinerary as _pg_save_itinerary

    if has_postgres():
        return _pg_save_itinerary(itinerary)
    with get_db_connection() as conn:
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


def get_itinerary(itinerary_id: int) -> dict | None:
    """Retrieve a single itinerary by id."""
    from .postgres_itineraries import get_itinerary as _pg_get_itinerary
    from .postgres_itineraries import has_postgres

    if has_postgres():
        return _pg_get_itinerary(itinerary_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM itineraries WHERE id = ?", (itinerary_id,))
        row = cur.fetchone()
        return _row_to_itinerary(row) if row else None


def list_itineraries(athlete_id: int | None = None) -> list[dict]:
    """Return all itineraries, optionally filtered by athlete."""
    from .postgres_itineraries import has_postgres
    from .postgres_itineraries import list_itineraries as _pg_list

    if has_postgres():
        return _pg_list(athlete_id)
    with get_db_connection() as conn:
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


def save_stage(stage: dict) -> int:
    """Create a stage for an itinerary. Returns the new row id."""
    from .postgres_itineraries import has_postgres
    from .postgres_itineraries import save_stage as _pg_save_stage

    if has_postgres():
        return _pg_save_stage(stage)
    with get_db_connection() as conn:
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


def list_stages(itinerary_id: int) -> list[dict]:
    """Return all stages for an itinerary, ordered by stage_day."""
    from .postgres_itineraries import has_postgres
    from .postgres_itineraries import list_stages as _pg_list_stages

    if has_postgres():
        return _pg_list_stages(itinerary_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM stages WHERE itinerary_id = ? ORDER BY stage_day ASC, id ASC",
            (itinerary_id,),
        )
        rows = cur.fetchall()
    return [_row_to_stage(r) for r in rows]


def get_stage(stage_id: int) -> dict | None:
    """Retrieve a single stage by id."""
    from .postgres_itineraries import get_stage as _pg_get_stage
    from .postgres_itineraries import has_postgres

    if has_postgres():
        return _pg_get_stage(stage_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stages WHERE id = ?", (stage_id,))
        row = cur.fetchone()
        return _row_to_stage(row) if row else None


def update_itinerary(itinerary_id: int, data: dict, tenant_id: int | None = None) -> bool:
    """Update an itinerary. Returns True if the row was modified."""
    from .postgres_itineraries import has_postgres
    from .postgres_itineraries import update_itinerary as _pg_update_itinerary

    if has_postgres():
        return _pg_update_itinerary(itinerary_id, data, tenant_id)
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
        updates.append("tenant_id=?")  # no-op guard, already filtered
        vals.append(tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE itineraries SET {', '.join(updates)} WHERE id = ?",
            vals,
        )
        conn.commit()
        return cur.rowcount > 0


def delete_itinerary(itinerary_id: int, tenant_id: int | None = None) -> bool:
    """Delete an itinerary. Returns True if the row was deleted."""
    from .postgres_itineraries import delete_itinerary as _pg_delete_itinerary
    from .postgres_itineraries import has_postgres

    if has_postgres():
        return _pg_delete_itinerary(itinerary_id, tenant_id)
    with get_db_connection() as conn:
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


def update_stage(stage_id: int, data: dict, tenant_id: int | None = None) -> bool:
    """Update a stage. Returns True if the row was modified."""
    from .postgres_itineraries import has_postgres
    from .postgres_itineraries import update_stage as _pg_update_stage

    if has_postgres():
        return _pg_update_stage(stage_id, data, tenant_id)
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
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE stages SET {', '.join(updates)} WHERE id = ?",
            vals,
        )
        conn.commit()
        return cur.rowcount > 0


def delete_stage(stage_id: int, tenant_id: int | None = None) -> bool:
    """Delete a stage. Returns True if the row was deleted."""
    from .postgres_itineraries import delete_stage as _pg_delete_stage
    from .postgres_itineraries import has_postgres

    if has_postgres():
        return _pg_delete_stage(stage_id, tenant_id)
    with get_db_connection() as conn:
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


def reorder_stages(itinerary_id: int, stage_order: list[int], tenant_id: int | None = None) -> bool:
    """Reorder stages by updating stage_day values. Returns True on success."""
    from .postgres_itineraries import has_postgres
    from .postgres_itineraries import reorder_stages as _pg_reorder

    if has_postgres():
        return _pg_reorder(itinerary_id, stage_order, tenant_id)
    with get_db_connection() as conn:
        cur = conn.cursor()
        for day, stage_id in enumerate(stage_order, start=1):
            cur.execute(
                "UPDATE stages SET stage_day=?, updated_at=? WHERE id=? AND itinerary_id=?",
                (day, datetime.now(UTC).isoformat(), stage_id, itinerary_id),
            )
        conn.commit()
        return True


def _row_to_itinerary(row: tuple) -> dict:
    cols = [d[0] for d in row.cursor_description] if hasattr(row, "cursor_description") else [
        "id", "athlete_id", "tenant_id", "name", "description",
        "start_date", "end_date", "total_km", "total_elevation_m", "created_at",
    ]
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
    cols = [d[0] for d in row.cursor_description] if hasattr(row, "cursor_description") else [
        "id", "itinerary_id", "stage_day", "title", "distance_km",
        "elevation_gain_m", "estimated_km", "estimated_elevation_m",
        "ride_id", "poi_id", "notes", "tenant_id", "created_at", "updated_at",
    ]
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


def seed_nutrition_food_items() -> None:
    now = datetime.now(UTC).isoformat()
    items = [
        ("Pasta al pesto", "pasta", 350, 55, 12, 10, 3),
        ("Pasta al pomodoro", "pasta", 280, 52, 10, 5, 3),
        ("Pasta carbonara", "pasta", 450, 55, 18, 22, 2),
        ("Risotto alla milanese", "pasta", 420, 50, 12, 20, 1),
        ("Pizza margherita", "pizza", 250, 30, 10, 8, 2),
        ("Pizza napoletana", "pizza", 280, 32, 11, 9, 2),
        ("Insalata mista", "insalate", 80, 8, 2, 4, 2),
        ("Caprese", "insalate", 180, 6, 12, 12, 1),
        ("Bistecca alla fiorentina", "carne", 320, 0, 28, 22, 0),
        ("Arrosto di vitello", "carne", 250, 0, 26, 15, 0),
        ("Pollo alla griglia", "carne", 165, 0, 31, 3.5, 0),
        ("Pesce spada alla griglia", "pesce", 200, 0, 24, 8, 0),
        ("Salmone al forno", "pesce", 220, 0, 22, 14, 0),
        ("Tonno al naturale", "pesce", 130, 0, 28, 1, 0),
        ("Uova sode", "uova", 155, 1.1, 13, 11, 0),
        ("Frittata di verdure", "uova", 180, 4, 12, 12, 1),
        ("Pane integrale", "pane", 220, 43, 9, 3, 4),
        ("Pane bianco", "pane", 260, 50, 8, 3, 2),
        ("Riso bianco bollito", "cereali", 130, 28, 2.5, 0.3, 0.4),
        ("Parmigiano reggiano", "latticini", 400, 4, 36, 29, 0),
        ("Mozzarella di bufala", "latticini", 280, 2, 18, 22, 0),
        ("Yogurt greco naturale", "latticini", 100, 4, 10, 0.5, 0),
        ("Pasta e fagioli", "zuppe", 180, 25, 10, 3, 5),
        ("Minestrone", "zuppe", 60, 10, 3, 1, 2.5),
        ("Tiramisu", "dolci", 350, 40, 8, 18, 1),
        ("Gelato alla crema", "dolci", 200, 24, 4, 10, 0.5),
        ("Pasta al ragù", "pasta", 380, 48, 16, 16, 3),
        ("Lasagna alla bolognese", "pasta", 320, 30, 14, 16, 2),
        ("Insalata di riso", "insalate", 180, 28, 5, 5, 2),
        ("Branzino al forno", "pesce", 160, 0, 24, 5, 0),
        ("Carote bollite", "verdure", 35, 7, 0.7, 0.2, 2.5),
        ("Broccoli al vapore", "verdure", 35, 6, 2.5, 0.3, 2.5),
        ("Patate al forno", "verdure", 110, 20, 2.5, 0.1, 1.5),
        ("Spinaci saltati", "verdure", 45, 5, 3.5, 0.5, 2.5),
        ("Panna cotta", "dolci", 230, 20, 4, 14, 0),
        ("Crostata di marmellata", "dolci", 280, 38, 4, 12, 1),
        ("Arancino", "street_food", 250, 35, 6, 10, 1.5),
        ("Supplì", "street_food", 200, 28, 6, 8, 1),
        ("Cappuccino", "bevande", 120, 10, 7, 6, 0),
        ("Acqua naturale", "bevande", 0, 0, 0, 0, 0),
        ("Succo d'arancia", "bevande", 45, 10, 0.7, 0.2, 0.2),
        ("Vino rosso (bicchiere)", "bevande", 120, 3.5, 0.2, 0, 0),
        ("Birra (bottiglia)", "bevande", 150, 12, 1.5, 0, 0),
        ("Macellaio - braciola di maiale", "carne", 210, 0, 22, 13, 0),
        ("Macellaio - salsiccia", "carne", 300, 1, 16, 26, 0),
        ("Macellaio - roast beef", "carne", 180, 0, 26, 7, 0),
        ("Macellaio - pollo intero", "carne", 165, 0, 21, 8, 0),
        ("Tonno in scatola al naturale", "pesce", 120, 0, 26, 1, 0),
        ("Sarde fresche", "pesce", 180, 0, 22, 8, 0),
        ("Merluzzo bollito", "pesce", 90, 0, 18, 0.7, 0),
        ("Gamberetti bolliti", "pesce", 100, 0.5, 24, 0.5, 0),
        ("Ceci bolliti", "legumi", 120, 18, 7, 2, 5),
        ("Lenticchie bollite", "legumi", 110, 18, 8, 0.4, 4),
        ("Fagioli borlotti", "legumi", 115, 20, 7.5, 0.5, 5),
        ("Fave fresche", "legumi", 70, 12, 4.5, 0.5, 4),
        ("Pasta e ceci", "zuppe", 160, 26, 7, 2, 4),
        ("Pasta e patate", "zuppe", 140, 25, 4, 1, 2),
        ("Passato di verdure", "zuppe", 50, 9, 2, 0.5, 2.5),
        ("Insalata di tonno", "insalate", 160, 4, 22, 5, 1),
        ("Insalata di pollo", "insalate", 150, 3, 20, 5, 1),
        ("Polenta", "cereali", 150, 33, 3, 1, 2),
        ("Couscous", "cereali", 160, 34, 4, 0.5, 2),
        ("Quinoa bollita", "cereali", 120, 21, 4.5, 1.8, 2.5),
        ("Granola con yogurt", "colazione", 200, 30, 6, 8, 2),
        ("Cornetti (2)", "colazione", 280, 35, 5, 14, 1),
        ("Brioche", "colazione", 250, 32, 5, 11, 1),
        ("Fette biscottate con marmellata", "colazione", 180, 35, 3, 3, 1),
    ]
    with get_db_connection() as conn:
        cur = conn.cursor()
        for name, category, kcal, carbs, protein, fat, fiber in items:
            cur.execute(
                """INSERT OR IGNORE INTO nutrition_food_items
                (name, category, kcal_per_100g, carbs_g_per_100g,
                 protein_g_per_100g, fat_g_per_100g, fiber_g_per_100g,
                 source, is_builtin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, category, kcal, carbs, protein, fat, fiber, "builtin", 1, now, now),
            )
        conn.commit()


def search_nutrition_food_items(query: str, category: str | None = None, limit: int = 50) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        params: list = []
        q = "SELECT * FROM nutrition_food_items WHERE 1=1"
        if query:
            q += " AND name LIKE ?"
            params.append(f"%{query}%")
        if category:
            q += " AND category = ?"
            params.append(category)
        q += " ORDER BY is_builtin DESC, name ASC LIMIT ?"
        params.append(limit)
        cur.execute(q, params)
        rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "tenant_id": r["tenant_id"],
            "name": r["name"],
            "category": r["category"],
            "kcal_per_100g": r["kcal_per_100g"],
            "carbs_g_per_100g": r["carbs_g_per_100g"],
            "protein_g_per_100g": r["protein_g_per_100g"],
            "fat_g_per_100g": r["fat_g_per_100g"],
            "fiber_g_per_100g": r["fiber_g_per_100g"],
            "source": r["source"],
            "is_builtin": r["is_builtin"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


def get_nutrition_food_item(item_id: int) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM nutrition_food_items WHERE id = ?", (item_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "tenant_id": row["tenant_id"],
            "name": row["name"],
            "category": row["category"],
            "kcal_per_100g": row["kcal_per_100g"],
            "carbs_g_per_100g": row["carbs_g_per_100g"],
            "protein_g_per_100g": row["protein_g_per_100g"],
            "fat_g_per_100g": row["fat_g_per_100g"],
            "fiber_g_per_100g": row["fiber_g_per_100g"],
            "source": row["source"],
            "is_builtin": row["is_builtin"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def list_nutrition_categories() -> list[str]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM nutrition_food_items ORDER BY category ASC")
        rows = cur.fetchall()
    return [r["category"] for r in rows]


def save_nutrition_food_item(item: dict, tenant_id: int = 0) -> int:
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO nutrition_food_items
            (tenant_id, name, category, kcal_per_100g, carbs_g_per_100g,
             protein_g_per_100g, fat_g_per_100g, fiber_g_per_100g,
             source, is_builtin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                item.get("name", ""),
                item.get("category", "other"),
                item.get("kcal_per_100g", 0),
                item.get("carbs_g_per_100g", 0),
                item.get("protein_g_per_100g", 0),
                item.get("fat_g_per_100g", 0),
                item.get("fiber_g_per_100g", 0),
                item.get("source", "user"),
                0,
                now,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid


def update_nutrition_food_item(item_id: int, item_data: dict) -> bool:
    existing = get_nutrition_food_item(item_id)
    if not existing:
        return False
    merged = {**existing, **item_data}
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE nutrition_food_items SET
               name=?, category=?, kcal_per_100g=?, carbs_g_per_100g=?,
               protein_g_per_100g=?, fat_g_per_100g=?, fiber_g_per_100g=?, updated_at=?
               WHERE id=?""",
            (
                merged.get("name"),
                merged.get("category"),
                merged.get("kcal_per_100g"),
                merged.get("carbs_g_per_100g"),
                merged.get("protein_g_per_100g"),
                merged.get("fat_g_per_100g"),
                merged.get("fiber_g_per_100g"),
                datetime.now(UTC).isoformat(),
                item_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_nutrition_food_item(item_id: int) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM nutrition_food_items WHERE id = ? AND is_builtin = 0", (item_id,))
        conn.commit()
        return cur.rowcount > 0


def _beck_severity(total_score: int) -> str:
    if total_score <= 13:
        return "minimal"
    if total_score <= 19:
        return "mild"
    if total_score <= 28:
        return "moderate"
    return "severe"


def save_beck_assessment(assessment: dict, tenant_id: int = 0) -> int:
    now = datetime.now(UTC).isoformat()
    answers = assessment.get("answers", [])
    total_score = int(sum(int(score) for _, score in answers)) if answers else 0
    severity = _beck_severity(total_score)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO beck_assessments
            (athlete_id, tenant_id, total_score, severity, answers, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                assessment.get("athlete_id"),
                assessment.get("tenant_id", tenant_id),
                total_score,
                severity,
                json.dumps(answers),
                assessment.get("notes"),
                now,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_beck_assessment(assessment_id: int) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM beck_assessments WHERE id = ?", (assessment_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "athlete_id": row["athlete_id"],
            "tenant_id": row["tenant_id"],
            "total_score": row["total_score"],
            "severity": row["severity"],
            "answers": json.loads(row["answers"]) if row["answers"] else [],
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def get_beck_assessments_by_athlete(athlete_id: int, tenant_id: int = 0, limit: int = 100) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT * FROM beck_assessments
            WHERE athlete_id = ? AND tenant_id = ?
            ORDER BY created_at DESC
            LIMIT ?""",
            (athlete_id, tenant_id, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "athlete_id": r["athlete_id"],
                "tenant_id": r["tenant_id"],
                "total_score": r["total_score"],
                "severity": r["severity"],
                "answers": json.loads(r["answers"]) if r["answers"] else [],
                "notes": r["notes"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]


def get_metrics_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    from .postgres_rides import get_metrics_by_athlete as _pg_get_metrics
    from .postgres_rides import has_postgres

    if has_postgres():
        return _pg_get_metrics(athlete_id, tenant_id)
    with get_db_connection() as conn:
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


def get_fitness_states_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM fitness_states WHERE athlete_id = ? AND tenant_id = ? ORDER BY date ASC",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM fitness_states WHERE athlete_id = ? ORDER BY date ASC",
                (athlete_id,),
            )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_food_logs_by_athlete(athlete_id: int, tenant_id: int | None = None, limit: int = 2000) -> list[dict]:
    with get_db_connection() as conn:
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


def get_latest_beck_assessment(athlete_id: int, tenant_id: int = 0) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT * FROM beck_assessments
            WHERE athlete_id = ? AND tenant_id = ?
            ORDER BY created_at DESC
            LIMIT 1""",
            (athlete_id, tenant_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "athlete_id": row["athlete_id"],
            "tenant_id": row["tenant_id"],
            "total_score": row["total_score"],
            "severity": row["severity"],
            "answers": json.loads(row["answers"]) if row["answers"] else [],
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def register_ble_device(
    athlete_id: int,
    device_id: str,
    name: str,
    *,
    tenant_id: int = 0,
    device_type: str = "weight_scale",
    service_uuid: str | None = None,
    characteristic_uuid: str | None = None,
    mac_address: str | None = None,
    settings: str | None = None,
) -> int:
    """Register or update a BLE device for an athlete."""
    now = datetime.now(UTC).isoformat()
    settings_json = settings or "{}"
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ble_devices
               (athlete_id, tenant_id, device_id, name, device_type,
                service_uuid, characteristic_uuid, mac_address,
                paired, settings, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
               ON CONFLICT(athlete_id, device_id) DO UPDATE SET
                   name=excluded.name,
                   device_type=excluded.device_type,
                   service_uuid=excluded.service_uuid,
                   characteristic_uuid=excluded.characteristic_uuid,
                   mac_address=excluded.mac_address,
                   paired=1,
                   settings=excluded.settings,
                   updated_at=excluded.updated_at""",
            (
                athlete_id,
                tenant_id,
                device_id,
                name,
                device_type,
                service_uuid,
                characteristic_uuid,
                mac_address,
                settings_json,
                now,
                now,
            ),
        )
        conn.commit()
        cur.execute("SELECT id FROM ble_devices WHERE athlete_id = ? AND device_id = ?", (athlete_id, device_id))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_ble_devices(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    """List all BLE devices registered for an athlete."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM ble_devices WHERE athlete_id = ? AND tenant_id = ? "
                "ORDER BY created_at DESC",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute("SELECT * FROM ble_devices WHERE athlete_id = ? ORDER BY created_at DESC", (athlete_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_ble_device(device_id: int, athlete_id: int) -> dict | None:
    """Get a single BLE device by its DB id, ensuring athlete ownership."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ble_devices WHERE id = ? AND athlete_id = ?", (device_id, athlete_id))
        row = cur.fetchone()
    return dict(row) if row else None


def update_ble_device(device_id: int, athlete_id: int, **updates) -> dict | None:
    """Update fields of a BLE device."""
    allowed = {
        "name", "device_type", "service_uuid", "characteristic_uuid",
        "mac_address", "paired", "settings", "last_connected_at",
        "last_synced_at",
    }
    set_clause = ", ".join(f"{k} = ?" for k in updates if k in allowed)
    if not set_clause:
        return get_ble_device(device_id, athlete_id)
    values = [updates[k] for k in updates if k in allowed]
    values.extend([device_id, athlete_id])
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE ble_devices SET {set_clause} WHERE id = ? AND athlete_id = ?", values)
        conn.commit()
    return get_ble_device(device_id, athlete_id)


def unregister_ble_device(device_id: int, athlete_id: int) -> bool:
    """Remove a BLE device registration."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM ble_devices WHERE id = ? AND athlete_id = ?", (device_id, athlete_id))
        conn.commit()
        return cur.rowcount > 0


def mark_ble_device_connected(device_id: int, athlete_id: int) -> None:
    """Update last_connected_at timestamp."""
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE ble_devices SET last_connected_at = ? "
            "WHERE id = ? AND athlete_id = ?",
            (now, device_id, athlete_id),
        )
        conn.commit()


def mark_ble_device_synced(device_id: int, athlete_id: int) -> None:
    """Update last_synced_at timestamp."""
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE ble_devices SET last_synced_at = ? "
            "WHERE id = ? AND athlete_id = ?",
            (now, device_id, athlete_id),
        )
        conn.commit()


def save_consent(
    athlete_id: int,
    consent_type: str,
    granted: bool = True,
    source: str = "web",
    tenant_id: int = 0,
) -> None:
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_consent (athlete_id, tenant_id, consent_type, granted, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(athlete_id, consent_type) DO UPDATE SET
                   granted=excluded.granted,
                   source=excluded.source,
                   updated_at=excluded.updated_at""",
            (athlete_id, tenant_id, consent_type, 1 if granted else 0, source, now, now),
        )
        conn.commit()


def get_consent(athlete_id: int, consent_type: str) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM user_consent WHERE athlete_id = ? AND consent_type = ?",
            (athlete_id, consent_type),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def get_consents_by_athlete(athlete_id: int) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_consent WHERE athlete_id = ?", (athlete_id,))
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def save_legal_acceptance(
    athlete_id: int,
    acceptance_type: str,
    version: str,
    source: str = "web",
    tenant_id: int = 0,
) -> None:
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO legal_acceptances (athlete_id, tenant_id, acceptance_type, version, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (athlete_id, tenant_id, acceptance_type, version, source, now),
        )
        conn.commit()


def get_legal_acceptances_by_athlete(athlete_id: int) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM legal_acceptances WHERE athlete_id = ?", (athlete_id,))
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def has_accepted_version(athlete_id: int, acceptance_type: str, min_version: str) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(  # noqa: E501
            "SELECT version FROM legal_acceptances "
            "WHERE athlete_id = ? AND acceptance_type = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (athlete_id, acceptance_type),
        )
        row = cur.fetchone()
    if not row:
        return False
    accepted = str(row[0])
    return accepted >= min_version


def save_ai_audit_log(
    athlete_id: int,
    provider: str,
    model: str,
    prompt_hash: str,
    response_length: int = 0,
    tool_calls: int = 0,
    latency_ms: int = 0,
    tenant_id: int = 0,
) -> None:
    now = datetime.now(UTC).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ai_audit_log
               (athlete_id, tenant_id, provider, model, prompt_hash,
                response_length, tool_calls, latency_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (athlete_id, tenant_id, provider, model, prompt_hash, response_length, tool_calls, latency_ms, now),
        )
        conn.commit()


def get_ai_audit_logs_by_athlete(athlete_id: int, limit: int = 100) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM ai_audit_log WHERE athlete_id = ? ORDER BY created_at DESC LIMIT ?",
            (athlete_id, limit),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def _row_to_sync_entity_state(row: tuple) -> dict:
    cols = [d[0] for d in row.cursor_description] if hasattr(row, "cursor_description") else [
        "id", "entity_type", "entity_id", "source", "reliability_score",
        "last_modified", "sync_status", "sync_error", "cloud_id", "created_at", "updated_at",
    ]
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
    "recalculate_training_stress_for_athlete",
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
]
