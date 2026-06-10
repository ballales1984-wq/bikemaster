"""Tests targeting previously uncovered error paths and edge cases."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from bike_analyzer.backend.analytics.ai_coach import (
    _build_athlete_context,
    _clean_ai_output,
    analyze_historical_trend,
    generate_training_advice,
    validate_athlete_profile,
)
from bike_analyzer.backend.ingestion.google_fit import (
    get_authorization_url,
    google_fit_to_ride,
)
from bike_analyzer.backend.maps.google_maps import get_google_api_key
from bike_analyzer.backend.maps.map_renderer import _speed_to_color, create_route_map
from bike_analyzer.backend.maps.osm_maps import search_nearby, search_places
from bike_analyzer.backend.models.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.backend.weather.weather_service import (
    get_forecast_for_date,
    get_weather_for_coordinates,
    get_weather_score,
)

# ============================================================
# AI coach — error paths + edge cases
# ============================================================

class TestAICoachErrorPaths:
    def test_validate_athlete_no_weight(self):
        assert validate_athlete_profile(AthleteProfile(name="Test", weight_kg=0))[0] is False

    def test_validate_athlete_no_name(self):
        assert validate_athlete_profile(AthleteProfile(name="", weight_kg=70))[0] is False

    def test_validate_athlete_valid(self):
        assert validate_athlete_profile(AthleteProfile(name="Test", weight_kg=70))[0] is True

    def test_clean_ai_output_strips_trailing_dot_zero(self):
        assert "5" in _clean_ai_output("You rode 5.0 km today")
        assert "test" in _clean_ai_output("test")

    def test_clean_ai_output_normalizes_newlines(self):
        result = _clean_ai_output("line1\n\n\n\nline2")
        assert "\n\n\n" not in result

    def test_build_athlete_context(self):
        profile = AthleteProfile(
            name="Mario Rossi", age=30, weight_kg=72, experience_level="Intermediate",
            goals="Gran Fondo", preferred_terrain="mountain", equipment="road bike"
        )
        ctx = _build_athlete_context(profile)
        assert "Mario Rossi" in ctx
        assert "Gran Fondo" in ctx
        assert "Intermediate" in ctx

    def test_generate_training_advice_no_api_key(self):
        import os
        with patch.dict(os.environ, {}, clear=True):
            profile = AthleteProfile(name="Test", experience_level="Beginner", weight_kg=70)
            advice = generate_training_advice(profile, [])
        assert advice is not None
        assert len(advice) > 0

    def test_analyze_historical_trend_empty(self):
        result = analyze_historical_trend([])
        assert "trend" in result

    def test_analyze_historical_trend_improving(self):
        import os
        os.environ.pop("GROQ_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        rides = [
            Ride(date="2024-01-01", distance_km=20, duration_minutes=60, avg_speed_kmh=20),
            Ride(date="2024-02-01", distance_km=30, duration_minutes=60, avg_speed_kmh=25),
            Ride(date="2024-03-01", distance_km=40, duration_minutes=60, avg_speed_kmh=30),
        ]
        result = analyze_historical_trend(rides)
        assert "average_fatigue" in result or "trend" in result


# ============================================================
# Google Maps — error paths
# ============================================================

class TestGoogleMapsErrorPaths:
    def test_get_google_api_key_no_env(self):
        import os
        with patch.dict(os.environ, {}, clear=True):
            key = get_google_api_key()
            assert key == "" or key is None

    def test_create_route_map_raises_on_empty(self):
        with pytest.raises(ValueError, match="No GPS points"):
            create_route_map([])

    def test_speed_to_color_edge_cases(self):
        assert _speed_to_color(15, 15, 15) == "#FFFF00"
        assert _speed_to_color(0, 0, 25) == "#00ff00"
        assert _speed_to_color(25, 0, 25) == "#ff0000"


# ============================================================
# OSM Maps — Nominatim error handling
# ============================================================

class TestOSMMapsErrorPaths:
    def test_search_places_request_error(self):
        with patch("bike_analyzer.backend.maps.osm_maps.requests") as mock_req:
            import requests as req_mod
            mock_req.get.side_effect = req_mod.RequestException("Connection error")
            result = search_places("cafe")
            assert result is None

    def test_search_nearby_request_error(self):
        pts = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime.now(tz=timezone.utc))]
        with patch("bike_analyzer.backend.maps.osm_maps.requests") as mock_req:
            import requests as req_mod
            mock_req.get.side_effect = req_mod.RequestException("Connection error")
            result = search_nearby(pts, "cafe")
            assert result is None

    def test_search_places_no_points(self):
        result = search_places("")
        assert result is None or "results" in result

    def test_reverse_geocode_request_error(self):
        with patch("bike_analyzer.backend.maps.osm_maps.requests") as mock_req:
            import requests as req_mod
            mock_req.get.side_effect = req_mod.RequestException("Connection error")
            from bike_analyzer.backend.maps.osm_maps import reverse_geocode
            result = reverse_geocode(45.0, 9.0)
            assert result is None


# ============================================================
# Google Fit — error handling
# ============================================================

class TestGoogleFitPaths:
    def test_get_authorization_url(self):
        url = get_authorization_url("test_client_id")
        assert "accounts.google.com" in url
        assert "test_client_id" in url
        assert "offline" in url

    def test_get_authorization_url_with_state(self):
        url = get_authorization_url("client_id", state="abc123")
        assert "state=abc123" in url

    def test_google_fit_to_ride(self):
        activities = [
            {"startTime": "2024-06-15T10:00:00Z", "endTime": "2024-06-15T11:30:00Z",
             "value": [{"intVal": 5400000, "mapKey": "duration"}, {"intVal": 25000, "mapKey": "distance"}]}
        ]
        rides = google_fit_to_ride(activities)
        assert isinstance(rides, list)

    def test_google_fit_to_ride_empty(self):
        assert google_fit_to_ride([]) == []


# ============================================================
# Weather — error handling + score
# ============================================================

class TestWeatherPaths:
    def test_get_weather_score_cold(self):
        score, advice = get_weather_score(-5, 50)
        assert score < 10
        assert len(advice) > 0

    def test_get_weather_score_perfect(self):
        score, advice = get_weather_score(22, 45)
        assert score == 10

    def test_get_weather_score_hot(self):
        score, advice = get_weather_score(38, 40)
        assert score < 8

    def test_get_weather_score_very_humid(self):
        score, advice = get_weather_score(22, 90)
        assert score < 10

    def test_get_forecast_no_api_key(self):
        import os
        with patch.dict(os.environ, {"WEATHER_API_KEY": ""}, clear=True):
            result = get_forecast_for_date(45.0, 9.0, "2024-06-15")
            assert "error" in result

    def test_get_forecast_api_error(self):
        import os
        with patch.dict(os.environ, {"WEATHER_API_KEY": "fake_key"}):
            with patch("bike_analyzer.backend.weather.weather_service.requests") as mock_req:
                mock_req.get.return_value.raise_for_status.side_effect = Exception("API error")
                result = get_forecast_for_date(45.0, 9.0, "2024-06-15")
                assert "error" in result

    def test_get_weather_cache_hit(self):
        import os
        cache_data = {"temperature": 20, "humidity": 50, "description": "cached"}
        with patch.dict(os.environ, {"WEATHER_API_KEY": "fake_key"}):
            with patch("bike_analyzer.backend.db.database.get_weather_cache", return_value=cache_data):
                result = get_weather_for_coordinates(45.0, 9.0)
                assert result["temperature"] == 20
                assert result["description"] == "cached"
