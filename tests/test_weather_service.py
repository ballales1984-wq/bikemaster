"""Tests for weather_service module."""

from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.weather.weather_service import (
    get_weather_for_coordinates,
    get_weather_score,
)


class TestGetWeatherScore:
    def test_great_conditions(self):
        score, advice = get_weather_score(temperature=20, humidity=50)
        assert score == 10
        assert "Great for a bike ride!" in advice

    def test_very_cold(self):
        score, advice = get_weather_score(temperature=-5, humidity=50)
        assert score == 5
        assert "Very low temperature" in advice

    def test_cold(self):
        score, advice = get_weather_score(temperature=3, humidity=50)
        assert score == 7
        assert "thermal" in advice.lower()

    def test_cool(self):
        score, advice = get_weather_score(temperature=8, humidity=50)
        assert score == 9
        assert "extra layer" in advice.lower()

    def test_hot(self):
        score, advice = get_weather_score(temperature=37, humidity=50)
        assert score == 6
        assert "hydration crucial" in advice.lower()

    def test_very_hot(self):
        score, advice = get_weather_score(temperature=32, humidity=50)
        assert score == 8
        assert "Hot" in advice

    def test_high_humidity(self):
        score, advice = get_weather_score(temperature=25, humidity=90)
        assert score == 8
        assert "High humidity" in advice

    def test_moderate_humidity(self):
        score, advice = get_weather_score(temperature=25, humidity=75)
        assert score == 9
        assert "Moderate humidity" in advice

    def test_combined_cold_high_humidity(self):
        score, advice = get_weather_score(temperature=3, humidity=90)
        assert score == 5
        assert score >= 0

    def test_score_never_negative(self):
        score, _ = get_weather_score(temperature=-10, humidity=95)
        assert score >= 0

    def test_perfect_conditions_score(self):
        score, _ = get_weather_score(temperature=22, humidity=40)
        assert score == 10


class TestGetWeatherForCoordinates:
    def test_no_api_key_returns_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("bike_analyzer.backend.weather.weather_service._get_weather_api_key", return_value=""):
                result = get_weather_for_coordinates(45.0, 9.0)
                assert "error" in result
                assert result["temperature"] is None

    def test_api_call_success(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "main": {"temp": 22, "feels_like": 24, "humidity": 60, "pressure": 1013},
            "weather": [{"description": "clear sky"}],
            "wind": {"speed": 5.0},
            "name": "Milan",
        }
        with patch("bike_analyzer.backend.weather.weather_service.requests.get", return_value=mock_resp):
            with patch("bike_analyzer.backend.db.database.get_weather_cache", return_value=None):
                with patch("bike_analyzer.backend.db.database.save_weather_cache"):
                    with patch("bike_analyzer.backend.weather.weather_service._get_weather_api_key", return_value="test_key"):
                        result = get_weather_for_coordinates(45.0, 9.0)
                        assert result["temperature"] == 22
                        assert result["humidity"] == 60
                        assert result["description"] == "clear sky"
                        assert result["wind_speed"] == 5.0

    def test_api_call_failure_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("Server error")
        with patch("bike_analyzer.backend.weather.weather_service.requests.get", return_value=mock_resp):
            with patch("bike_analyzer.backend.db.database.get_weather_cache", return_value=None):
                with patch("bike_analyzer.backend.weather.weather_service._get_weather_api_key", return_value="test_key"):
                    result = get_weather_for_coordinates(45.0, 9.0)
                    assert "error" in result

    def test_cached_result_returned(self):
        cached = {"temperature": 18, "cached": True}
        with patch("bike_analyzer.backend.db.database.get_weather_cache", return_value=cached):
            with patch("bike_analyzer.backend.weather.weather_service._get_weather_api_key", return_value="test_key"):
                result = get_weather_for_coordinates(45.0, 9.0)
                assert result == cached
