"""Pydantic v2 application settings.

Replaces manual dotenv parsing with a type-safe, validated settings model.
All settings are loaded from environment variables with sensible defaults.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with Pydantic v2 validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # === Database ===
    db_path: str = "rides.db"
    database_url: str = ""

    # === API ===
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # === CORS ===
    cors_origins: str = "http://localhost:8000,http://localhost:8080,http://127.0.0.1:8000,http://127.0.0.1:8080"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # === SerpApi / Google Maps (deprecated) ===
    google_maps_api_key: str = ""
    google_maps_zoom: int = 13
    google_maps_size: str = "800x600"
    serpapi_api_key: str = ""
    serpapi_engine: str = "google_maps"
    serpapi_base_url: str = "https://serpapi.com/search"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"

    # === Google Fit ===
    google_fit_scope: str = (
        "https://www.googleapis.com/auth/fitness.activity.read "
        "https://www.googleapis.com/auth/fitness.location.read"
    )

    # === Knowledge Base ===
    kb_path: Path = Path(__file__).resolve().parent.parent.parent / "knowledge_base"

    # === AI Coach ===
    groq_api_key: str = ""
    groq_model: str = "llama3-70b-8192"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # === JWT / Auth ===
    secret_key: str = ""
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

    # === Weather ===
    weather_api_key: str = ""
    weather_cache_hours: int = 6
    weather_units: str = "metric"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return cached settings singleton (lazy-loaded)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
