"""Weather service for fetching temperature and humidity data."""
from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests
from ..config import WEATHER_API_KEY, WEATHER_CACHE_HOURS, WEATHER_UNITS

WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

def get_weather_for_coordinates(lat: float, lon: float, date: Optional[str] = None) -> dict:
    """Fetch weather for specific coordinates and optional date."""
    from ..db.database import get_weather_cache, save_weather_cache
    
    if not WEATHER_API_KEY:
        return {"error": "Weather API key not configured", "temperature": None, "humidity": None}
    
    # Check cache first (for today's weather or specific date if cached)
    if date:
        cached = get_weather_cache(lat, lon, date)
        if cached:
            return cached
    
    endpoint = f"{WEATHER_BASE_URL}/weather"
    try:
        resp = requests.get(endpoint, params={
            "lat": lat,
            "lon": lon,
            "appid": WEATHER_API_KEY,
            "units": WEATHER_UNITS,
            "lang": "it"
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        weather = {
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "description": data["weather"][0]["description"] if data.get("weather") else "",
            "wind_speed": data.get("wind", {}).get("speed"),
            "location": {
                "lat": lat,
                "lon": lon,
                "city": data.get("name", "Unknown")
            },
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Cache the result
        if date:
            save_weather_cache(lat, lon, date, weather)
        
        return weather
    except Exception as e:
        return {"error": str(e), "temperature": None, "humidity": None}

def get_forecast_for_date(lat: float, lon: float, date: str) -> dict:
    """Get weather forecast for a specific future date."""
    from ..db.database import get_weather_cache, save_weather_cache
    
    if not WEATHER_API_KEY:
        return {"error": "Weather API key not configured", "temperature": None, "humidity": None}
    
    # Check cache
    cached = get_weather_cache(lat, lon, date)
    if cached:
        return cached
    
    # Use One Call API for forecast
    endpoint = f"{WEATHER_BASE_URL}/forecast"
    try:
        resp = requests.get(endpoint, params={
            "lat": lat,
            "lon": lon,
            "appid": WEATHER_API_KEY,
            "units": WEATHER_UNITS,
            "lang": "it"
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Find forecast closest to midday of target date
        target_date = datetime.fromisoformat(date).date() if "T" in date else datetime.strptime(date, "%Y-%m-%d")
        target_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        target_ts = int(target_dt.timestamp())
        
        candidates = data.get("list", [])
        closest = min(candidates, key=lambda x: abs(x["dt"] - target_ts)) if candidates else None
        
        if closest:
            weather = {
                "temperature": closest["main"]["temp"],
                "feels_like": closest["main"]["feels_like"],
                "humidity": closest["main"]["humidity"],
                "pressure": closest["main"]["pressure"],
                "description": closest["weather"][0]["description"] if closest.get("weather") else "",
                "wind_speed": closest.get("wind", {}).get("speed"),
                "location": {
                    "lat": lat,
                    "lon": lon,
                    "city": (data.get("city", {}) or {}).get("name", "Unknown")
                },
                "forecast_date": date,
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }
            save_weather_cache(lat, lon, date, weather)
            return weather
        
        return {"error": "No forecast data", "temperature": None, "humidity": None}
    except Exception as e:
        return {"error": str(e), "temperature": None, "humidity": None}

def get_weather_score(temperature: float, humidity: float) -> tuple[int, str]:
    """Calculate bike ride suitability score based on weather."""
    score = 10
    advice = []
    
    # Temperature scoring (optimal 15-25°C)
    if temperature < 0:
        score -= 5
        advice.append("⚠️ Temperature molto bassa, abbigliamento caldo necessario")
    elif temperature < 5:
        score -= 3
        advice.append("🧥 Freddo intenso, abbigliamento termico")
    elif temperature < 10:
        score -= 1
        advice.append("🧣 Freddo, strato extra consigliato")
    elif temperature > 35:
        score -= 4
        advice.append("🔥 Temperature elevata, idratazione cruciale")
    elif temperature > 30:
        score -= 2
        advice.append("🥵 Caldo, orari diurni da evitare")
    
    # Humidity scoring
    if humidity > 85:
        score -= 2
        advice.append("💨 Umidità elevata, sensazione di caldo")
    elif humidity > 70:
        score -= 1
        advice.append("🌫️ Umidità moderata")
    
    if score >= 8:
        advice.append("Ottimo per una uscita in bici!")
    elif score >= 5:
        advice.append("Buona uscita, attenzione a condizioni")
    else:
        advice.append("Condizioni non ideali, considera riprogrammazione")
    
    return score, " ".join(advice)