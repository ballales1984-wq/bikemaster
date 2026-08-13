"""Weather API routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ...settings import get_settings

router = APIRouter(prefix="/weather", tags=["weather"], redirect_slashes=False)


@router.get("/")
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    date: str | None = Query(None, description="Date (YYYY-MM-DD) or today"),
):
    """Get weather for coordinates, optionally for a specific date."""
    from ...weather.weather_service import (
        get_forecast_for_date,
        get_weather_for_coordinates,
        get_weather_score,
    )

    try:
        _s = get_settings()
        if not _s.weather_api_key:
            return JSONResponse(
                status_code=503,
                content={"error": "Weather service not configured", "score": 5, "advice": ""},
            )

        weather = get_forecast_for_date(lat, lon, date) if date else get_weather_for_coordinates(lat, lon)

        if "error" in weather:
            return JSONResponse(status_code=502, content={"error": weather["error"], "score": 5, "advice": ""})

        temp = weather.get("temperature")
        humidity = weather.get("humidity")

        score, advice = (
            get_weather_score(temp, humidity)
            if temp is not None and humidity is not None
            else (5, "Weather data not available")
        )

        weather["score"] = score
        weather["advice"] = advice

        return weather
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "score": 5, "advice": ""})


@router.get("", include_in_schema=False)
async def get_weather_no_trailing_slash(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    date: str | None = Query(None, description="Date (YYYY-MM-DD) or today"),
):
    """Alias for get_weather without trailing slash to avoid redirect CORS issues."""
    return await get_weather(lat, lon, date)


@router.get("/forecast")
async def get_weather_forecast(
    lat: float = Query(..., description="Latitudine"),
    lon: float = Query(..., description="Longitudine"),
    days: int = Query(7, ge=1, le=7),
):
    """Get multi-day weather forecast."""
    from ...weather.weather_service import get_forecast_for_date, get_weather_score

    try:
        _s = get_settings()
        if not _s.weather_api_key:
            return JSONResponse(status_code=503, content={"error": "Weather service not configured", "forecasts": []})

        forecasts = []
        today = datetime.now(UTC)

        for i in range(days):
            date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            weather = get_forecast_for_date(lat, lon, date)
            if "error" not in weather:
                temp = weather.get("temperature")
                humidity = weather.get("humidity")
                score, advice = get_weather_score(temp, humidity) if temp and humidity else (5, "")
                weather["score"] = score
                weather["advice"] = advice
                weather["date"] = date
            forecasts.append(weather)

        return {"forecasts": forecasts}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "forecasts": []})


@router.get("/geocode")
async def geocode_city(
    city: str = Query(..., description="City name"),
):
    """Convert city name to coordinates."""
    from ...weather.weather_service import get_city_coordinates

    try:
        result = get_city_coordinates(city)
        if "error" in result:
            return JSONResponse(status_code=404, content={"error": result["error"], "city": city})
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "city": city})
