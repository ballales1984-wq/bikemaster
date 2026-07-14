"""Pydantic v2 application settings.

Replaces manual dotenv parsing with a type-safe, validated settings model.
All settings are loaded from environment variables with sensible defaults.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with Pydantic v2 validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # === Environment ===
    environment: str = "development"

    # === Sentry Monitoring ===
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.2
    sentry_profiles_sample_rate: float = 0.1

    # === OpenTelemetry / Jaeger Tracing ===
    otel_service_name: str = "bikemaster"
    otel_exporter_zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_traces_sampler: str = "parentbased_traceidratio"
    otel_traces_sampler_arg: float = 1.0
    otel_environment: str = "development"

    # === Database ===
    db_path: str = "rides.db"
    database_url: str = ""

    # === API ===
    api_host: str = "0.0.0.0"  # nosec B104  # Required for Docker container listening
    api_port: int = 8000

    # === CORS ===
    cors_origins: str = "http://localhost:8000,http://localhost:8080,http://127.0.0.1:8000,http://127.0.0.1:8080,https://bikemaster-xi.vercel.app"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # === OAuth redirect URI allow-list ===
    # Custom (non-http/https) URI schemes allowed as OAuth redirect targets,
    # e.g. mobile app deep links like "com.bikemaster.app://callback".
    oauth_redirect_schemes: str = "com.bikemaster.app"

    @property
    def oauth_redirect_schemes_list(self) -> set[str]:
        return {s.strip().lower() for s in self.oauth_redirect_schemes.split(",") if s.strip()}

    # === OAuth redirect host allow-list (http/https) ===
    # Comma-separated hosts additionally allowed as OAuth redirect_uri targets.
    # The request Origin header is NEVER trusted, to prevent open-redirect attacks.
    oauth_allowed_redirect_hosts: str = ""

    @property
    def oauth_allowed_hosts_list(self) -> list[str]:
        return [h.strip().lower() for h in self.oauth_allowed_redirect_hosts.split(",") if h.strip()]

    # === SerpApi / Google Maps ===
    # SerpApi is used as an on-demand, budget-limited POI enrichment source that
    # gradually populates the map database (see maps/poi_enrichment.py). OSM
    # (osm_maps.py) remains the default keyless provider for live lookups.
    google_maps_api_key: str = ""
    google_maps_zoom: int = 13
    google_maps_size: str = "800x600"
    serpapi_api_key: str = ""
    serpapi_engine: str = "google_maps"
    serpapi_base_url: str = "https://serpapi.com/search"
    # Max SerpApi searches per calendar month (free-tier safeguard). Enrichment
    # stops once this budget is exhausted and can fall back to OSM.
    serpapi_monthly_budget: int = 250
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"

    # === Google Health ===
    google_health_scope: str = (
        "https://www.googleapis.com/auth/googlehealth.activity.read "
        "https://www.googleapis.com/auth/googlehealth.location.read"
    )

    # === Google Fit ===
    google_fit_scope: str = (
        "https://www.googleapis.com/auth/fitness.activity.read https://www.googleapis.com/auth/fitness.location.read"
    )

    # === Knowledge Base ===
    kb_path: Path = Path(__file__).resolve().parent.parent.parent / "knowledge_base"

    # === AI Coach ===
    ai_coach_mode: str = "external"
    ai_coach_chat_retention_days: int = 90
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # === JWT / Auth ===
    secret_key: str = ""
    secret_key_previous: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    jwt_issuer: str = "bikemaster"
    jwt_audience: str = "bikemaster"

    # === Analytics thresholds ===
    max_speed_km_h: float = 120.0
    pause_speed_threshold: float = 1.5
    pause_duration_threshold_s: float = 180.0
    acceleration_threshold: float = 2.0
    calorie_efficiency_factor: float = 0.25
    calorie_benchmark_kcal_km: float = 30.0
    fatigue_weight_duration: float = 0.30
    fatigue_weight_hr: float = 0.30
    fatigue_weight_speed: float = 0.20
    fatigue_weight_elevation: float = 0.10
    fatigue_weight_weight: float = 0.10

    # === Traffic / Road Safety ===
    incident_data_path: str = ""
    incident_api_url: str = ""
    incident_api_key: str = ""
    incident_radius_km: float = 5.0
    incident_days: int = 90

    # === Weather ===
    weather_api_key: str = ""
    weather_cache_hours: int = 6
    weather_units: str = "metric"

    # === Redis ===
    redis_url: str = ""
    redis_cache_ttl_seconds: int = 300

    # === Background Tasks ===
    task_queue_workers: int = 2

    # === Strava Integration ===
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/api/v1/import/strava/callback"
    strava_scope: str = "activity:read_all"

    # === Garmin Integration ===
    garmin_consumer_key: str = ""
    garmin_consumer_secret: str = ""
    garmin_redirect_uri: str = "http://localhost:8000/api/v1/import/garmin/callback"
    garmin_scope: str = "read"

    # === Wahoo Integration ===
    wahoo_client_id: str = ""
    wahoo_client_secret: str = ""
    wahoo_redirect_uri: str = "http://localhost:8000/api/v1/integrations/wahoo/callback"
    wahoo_scope: str = "workouts_read user_read"

    # === Map Styles ===
    default_map_style: str = "standard"

    # === Google OAuth2 ===
    google_client_id: str = ""
    google_client_secret: str = ""

    # === Google Fit / Google Health OAuth2 (fallback to generic Google client) ===
    google_fit_client_id: str = ""
    google_fit_client_secret: str = ""
    google_health_client_id: str = ""
    google_health_client_secret: str = ""

    @model_validator(mode="after")
    def _validate_production_database(self) -> Settings:
        _ENV = self.environment.lower()
        _IS_PROD = _ENV in ("production", "prod", "staging")
        if _IS_PROD and not self.database_url:
            logging.warning(
                "DATABASE_URL not set in production environment. "
                "Expected PostgreSQL connection string. Falling back to SQLite (db_path=%s).",
                self.db_path,
            )
        elif not self.database_url and not self.db_path:
            self.db_path = "rides.db"
        return self

    @model_validator(mode="after")
    def _validate_secret_key(self) -> Settings:
        _ENV = self.environment.lower()
        _IS_PROD = _ENV in ("production", "prod", "staging")
        _PLACEHOLDER_KEYS = (
            "your-secret-key-here",
            "changeme",
            "change-me",
            "secret",
            "<SECRET_KEY>",
            "REPLACE_ME",
            "",
        )
        if self.secret_key.strip() not in _PLACEHOLDER_KEYS:
            self.secret_key_previous = ""
        else:
            if _IS_PROD:
                logging.critical(
                    "SECRET_KEY non valida. Usa un valore casuale >= 32 caratteri (es. openssl rand -hex 32)."
                )
                sys.exit(1)
            self.secret_key = "test-secret-key-for-development-please-override"
            self.secret_key_previous = os.getenv("SECRET_KEY_PREVIOUS", "")
        return self


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings singleton (lazy-loaded)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
