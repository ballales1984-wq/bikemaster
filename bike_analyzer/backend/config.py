"""Backward-compatible configuration layer.

Imports validated settings from settings.py and exposes them using the
legacy UPPER_CASE names used throughout the codebase.

SECURITY: In produzione SECRET_KEY è obbligatoria. Se mancara, l'app non
si avvia. In sviluppo si può usare il fallback con warning.
"""

from __future__ import annotations

import logging
import os
import sys

from bike_analyzer.backend.settings import get_settings

_s = get_settings()

# Security hardening per SECRET_KEY
_ENV = os.getenv("ENVIRONMENT", "development")
_IS_PROD = _ENV.lower() in ("production", "prod", "staging")

_SECRET_KEY = _s.secret_key
_PLACEHOLDER_KEYS = ("your-secret-key-here", "changeme", "change-me", "secret", "<SECRET_KEY>", "REPLACE_ME", "")
_SECRET_KEY_IS_PLACEHOLDER = _SECRET_KEY.strip() in _PLACEHOLDER_KEYS

# Check environment from settings first, then env var
_ENV = os.getenv("ENVIRONMENT", _s.environment)
_IS_PROD = _ENV.lower() in ("production", "prod", "staging")

if not _SECRET_KEY_IS_PLACEHOLDER:
    _SECRET_KEY_PRIMARY = _SECRET_KEY
    _SECRET_KEY_PREVIOUS = ""
else:
    if _IS_PROD:
        logging.critical("SECRET_KEY non valida. Usa un valore casuale >= 32 caratteri (es. openssl rand -hex 32).")
        sys.exit(1)
    _SECRET_KEY_PRIMARY = "test-secret-key-for-development-please-override"
    _SECRET_KEY_PREVIOUS = os.getenv("SECRET_KEY_PREVIOUS", "")

DB_PATH = _s.db_path
DATABASE_URL = _s.database_url
API_HOST = _s.api_host
API_PORT = _s.api_port
CORS_ORIGINS = _s.cors_origins_list
GOOGLE_MAPS_API_KEY = _s.google_maps_api_key
GOOGLE_MAPS_ZOOM = _s.google_maps_zoom
GOOGLE_MAPS_SIZE = _s.google_maps_size
SERPAPI_API_KEY = _s.serpapi_api_key
SERPAPI_ENGINE = _s.serpapi_engine
SERPAPI_BASE_URL = _s.serpapi_base_url
NOMINATIM_BASE_URL = _s.nominatim_base_url
GOOGLE_HEALTH_SCOPE = _s.google_health_scope
GOOGLE_FIT_SCOPE = _s.google_fit_scope
KB_PATH = _s.kb_path
AI_COACH_MODE = _s.ai_coach_mode
GROQ_API_KEY = _s.groq_api_key
GROQ_MODEL = _s.groq_model
OPENAI_API_KEY = _s.openai_api_key
OPENAI_MODEL = _s.openai_model
OPENAI_LOG_LEVEL = _s.openai_log_level
OPENAI_EMBEDDING_COOLDOWN_SECONDS = _s.openai_embedding_cooldown_seconds
OPENAI_EMBEDDING_MAX_FAILURES = _s.openai_embedding_max_failures
OLLAMA_API_KEY = _s.ollama_api_key
OLLAMA_BASE_URL = _s.ollama_base_url
OLLAMA_MODEL = _s.ollama_model
SECRET_KEY = _SECRET_KEY_PRIMARY
SECRET_KEY_PREVIOUS = _SECRET_KEY_PREVIOUS
ALGORITHM = _s.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = _s.access_token_expire_minutes
JWT_ISSUER = _s.jwt_issuer
JWT_AUDIENCE = _s.jwt_audience
MAX_SPEED_KM_H = _s.max_speed_km_h
PAUSE_SPEED_THRESHOLD = _s.pause_speed_threshold
PAUSE_DURATION_THRESHOLD_S = _s.pause_duration_threshold_s
ACCELERATION_THRESHOLD = _s.acceleration_threshold
CALORIE_EFFICIENCY_FACTOR = _s.calorie_efficiency_factor
CALORIE_BENCHMARK_KCAL_KM = _s.calorie_benchmark_kcal_km
FATIGUE_WEIGHT_DURATION = _s.fatigue_weight_duration
FATIGUE_WEIGHT_HR = _s.fatigue_weight_hr
FATIGUE_WEIGHT_SPEED = _s.fatigue_weight_speed
FATIGUE_WEIGHT_ELEVATION = _s.fatigue_weight_elevation
FATIGUE_WEIGHT_WEIGHT = _s.fatigue_weight_weight
WEATHER_API_KEY = _s.weather_api_key
WEATHER_CACHE_HOURS = _s.weather_cache_hours
WEATHER_UNITS = _s.weather_units
INCIDENT_DATA_PATH = _s.incident_data_path
INCIDENT_API_URL = _s.incident_api_url
INCIDENT_API_KEY = _s.incident_api_key
INCIDENT_RADIUS_KM = _s.incident_radius_km
INCIDENT_DAYS = _s.incident_days

# === Redis / Background Tasks ===
REDIS_URL = _s.redis_url
REDIS_CACHE_TTL_SECONDS = _s.redis_cache_ttl_seconds
TASK_QUEUE_WORKERS = _s.task_queue_workers

ENVIRONMENT = _ENV

# === Strava Integration ===
STRAVA_CLIENT_ID = _s.strava_client_id
STRAVA_CLIENT_SECRET = _s.strava_client_secret
STRAVA_REDIRECT_URI = _s.strava_redirect_uri
STRAVA_SCOPE = _s.strava_scope
STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE_URL = "https://www.strava.com/api/v3"

# === Garmin Integration ===
GARMIN_CONSUMER_KEY = _s.garmin_consumer_key
GARMIN_CONSUMER_SECRET = _s.garmin_consumer_secret
GARMIN_REDIRECT_URI = _s.garmin_redirect_uri
GARMIN_SCOPE = _s.garmin_scope
GARMIN_AUTH_URL = "https://connect.garmin.com/oauthConfirm"
GARMIN_TOKEN_URL = "https://connect.garmin.com/oauth2/token"
GARMIN_API_BASE_URL = "https://apis.garmin.com/fitness/v1"

# === Wahoo Integration ===
WAHOO_CLIENT_ID = _s.wahoo_client_id
WAHOO_CLIENT_SECRET = _s.wahoo_client_secret
WAHOO_REDIRECT_URI = _s.wahoo_redirect_uri
WAHOO_SCOPE = _s.wahoo_scope
WAHOO_AUTH_URL = "https://api.wahooligan.com/oauth/authorize"
WAHOO_TOKEN_URL = "https://api.wahooligan.com/oauth/token"
WAHOO_API_BASE_URL = "https://api.wahooligan.com"

# === Google OAuth2 ===
GOOGLE_CLIENT_ID = _s.google_client_id
GOOGLE_CLIENT_SECRET = _s.google_client_secret

GOOGLE_FIT_CLIENT_ID = _s.google_fit_client_id or _s.google_client_id
GOOGLE_FIT_CLIENT_SECRET = _s.google_fit_client_secret or _s.google_client_secret
GOOGLE_HEALTH_CLIENT_ID = _s.google_health_client_id or _s.google_client_id
GOOGLE_HEALTH_CLIENT_SECRET = _s.google_health_client_secret or _s.google_client_secret
