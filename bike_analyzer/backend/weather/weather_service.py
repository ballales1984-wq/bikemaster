"""Weather service using OpenWeatherMap API."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests
from ..config import WEATHER_API_KEY

WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

def _get_weather_api_key() -> str:
    """Get API key from config or environment."""
    return WEATHER_API_KEY or ""

def get_weather_for_coordinates(lat: float, lon: float, date: Optional[str] = None) -> dict:
    """Fetch weather for specific coordinates using OpenWeatherMap."""
    from ..db.database import get_weather_cache, save_weather_cache
    
    api_key = _get_weather_api_key()
    if not api_key:
        return {"error": "Weather API key not configured", "temperature": None, "humidity": None}
    
    date_to_use = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Check cache
    cached = get_weather_cache(lat, lon, date_to_use)
    if cached:
        return cached
    
    endpoint = f"{WEATHER_BASE_URL}/weather"
    try:
        resp = requests.get(endpoint, params={
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
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
        
        save_weather_cache(lat, lon, date_to_use, weather)
        return weather
    except Exception as e:
        return {"error": str(e), "temperature": None, "humidity": None}

def get_forecast_for_date(lat: float, lon: float, date: str) -> dict:
    """Get weather forecast for a specific future date using 5-day forecast."""
    from ..db.database import get_weather_cache, save_weather_cache
    
    api_key = _get_weather_api_key()
    if not api_key:
        return {"error": "Weather API key not configured", "temperature": None, "humidity": None}
    
    cached = get_weather_cache(lat, lon, date)
    if cached:
        return cached
    
    endpoint = f"{WEATHER_BASE_URL}/forecast"
    try:
        resp = requests.get(endpoint, params={
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
            "lang": "it"
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        target_dt = datetime.combine(target_date, datetime.min.time())
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
    
    if temperature < 0:
        score -= 5
        advice.append("⚠️ Very low temperature, warm clothing needed")
    elif temperature < 5:
        score -= 3
        advice.append("🧥 Cold weather, thermal clothing")
    elif temperature < 10:
        score -= 1
        advice.append("🧣 Cold, extra layer recommended")
    elif temperature > 35:
        score -= 4
        advice.append("🔥 High temperature, hydration crucial")
    elif temperature > 30:
        score -= 2
        advice.append("🥵 Hot, avoid daytime hours")
    
    if humidity > 85:
        score -= 2
        advice.append("💨 High humidity, feels hotter")
    elif humidity > 70:
        score -= 1
        advice.append("🌫️ Moderate humidity")
    
    if score >= 8:
        advice.append("Great for a bike ride!")
    elif score >= 5:
        advice.append("Good ride, watch conditions")
    else:
        advice.append("Not ideal conditions, consider rescheduling")
    
    return score, " ".join(advice)