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
_IS_PROD = _ENV.lower() in ("production", "prod", "staging", "staging")

if not _s.secret_key:
    if _IS_PROD:
        logging.error("SECRET_KEY è obbligatoria in produzione. Impostala nel .env.")
        sys.exit(1)
    else:
        import secrets as _secrets
        _fallback = _secrets.token_urlsafe(32)
        logging.warning(
            "SECRET_KEY non configurata. Generated temporary key (dev only): %s...", _fallback[:8]
        )
        _s.secret_key = _fallback

# SECRET_KEY rotation support
_SECRET_KEY_PRIMARY = _s.secret_key
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
GOOGLE_FIT_SCOPE = _s.google_fit_scope
KB_PATH = _s.kb_path
GROQ_API_KEY = _s.groq_api_key
GROQ_MODEL = _s.groq_model
OPENAI_API_KEY = _s.openai_api_key
OPENAI_MODEL = _s.openai_model
SECRET_KEY = _s.secret_key
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

ENVIRONMENT = _ENV
