"""Centralized application configuration.

All settings are loaded from environment variables with sensible defaults.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env", override=True)

# Database
DB_PATH: str = os.getenv("DB_PATH", "rides.db")

# API Server
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

# Google Fit
GOOGLE_FIT_SCOPE: str = (
    "https://www.googleapis.com/auth/fitness.activity.read "
    "https://www.googleapis.com/auth/fitness.location.read"
)

# Knowledge Base
KB_PATH: Path = Path(__file__).parent.parent.parent / "knowledge_base"

# AI Coach
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_MODEL: str = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")

# JWT / Auth
SECRET_KEY: str = os.getenv("SECRET_KEY", "bikemaster-default-secret-change-me")
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


