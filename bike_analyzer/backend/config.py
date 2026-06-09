"""Centralized application configuration.

All settings are loaded from environment variables with sensible defaults.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=True)

# Database
DB_PATH: str = os.getenv("DB_PATH", "rides.db")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# CORS
CORS_ORIGINS: List[str] = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8000,http://localhost:8080,http://127.0.0.1:8000,http://127.0.0.1:8080",
).split(",")

# Google Maps
GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_MAPS_ZOOM: int = int(os.getenv("GOOGLE_MAPS_ZOOM", "13"))
GOOGLE_MAPS_SIZE: str = os.getenv("GOOGLE_MAPS_SIZE", "800x600")

# SerpApi (Google Maps alternative)
SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
SERPAPI_ENGINE: str = os.getenv("SERPAPI_ENGINE", "google_maps")
SERPAPI_BASE_URL: str = os.getenv("SERPAPI_BASE_URL", "https://serpapi.com/search")

# Google Fit
GOOGLE_FIT_SCOPE: str = (
    "https://www.googleapis.com/auth/fitness.activity.read "
    "https://www.googleapis.com/auth/fitness.location.read"
)

# Knowledge Base
KB_PATH: Path = Path(__file__).parent.parent.parent / "knowledge_base"

# AI Coach
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# JWT / Auth
_SECRET: str = os.getenv("SECRET_KEY", "")
SECRET_KEY: str = _SECRET if _SECRET else secrets.token_urlsafe(32)
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_ISSUER: str = os.getenv("JWT_ISSUER", "bikemaster")
JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "bikemaster")

# Analytics thresholds
MAX_SPEED_KM_H: float = float(os.getenv("MAX_SPEED_KM_H", "120.0"))
PAUSE_SPEED_THRESHOLD: float = float(os.getenv("PAUSE_SPEED_THRESHOLD", "1.5"))
PAUSE_DURATION_THRESHOLD_S: float = float(os.getenv("PAUSE_DURATION_THRESHOLD_S", "180.0"))
ACCELERATION_THRESHOLD: float = float(os.getenv("ACCELERATION_THRESHOLD", "2.0"))
CALORIE_EFFICIENCY_FACTOR: float = float(os.getenv("CALORIE_EFFICIENCY_FACTOR", "0.25"))
CALORIE_BENCHMARK_KCAL_KM: float = float(os.getenv("CALORIE_BENCHMARK_KCAL_KM", "30.0"))
FATIGUE_WEIGHT_DURATION: float = float(os.getenv("FATIGUE_WEIGHT_DURATION", "0.30"))
FATIGUE_WEIGHT_HR: float = float(os.getenv("FATIGUE_WEIGHT_HR", "0.30"))
FATIGUE_WEIGHT_SPEED: float = float(os.getenv("FATIGUE_WEIGHT_SPEED", "0.20"))
FATIGUE_WEIGHT_ELEVATION: float = float(os.getenv("FATIGUE_WEIGHT_ELEVATION", "0.10"))
FATIGUE_WEIGHT_WEIGHT: float = float(os.getenv("FATIGUE_WEIGHT_WEIGHT", "0.10"))

# Weather API (OpenWeatherMap)
WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")

# Weather settings
WEATHER_CACHE_HOURS: int = int(os.getenv("WEATHER_CACHE_HOURS", "6"))
WEATHER_UNITS: str = os.getenv("WEATHER_UNITS", "metric")


