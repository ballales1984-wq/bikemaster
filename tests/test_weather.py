"""Tests for weather service."""

from bike_analyzer.backend.weather.weather_service import get_weather_score


def test_weather_score_ideal():
    score, advice = get_weather_score(20.0, 50.0)
    assert score == 10
    assert "Great" in advice


def test_weather_score_cold():
    score, advice = get_weather_score(2.0, 50.0)
    assert score < 10
    assert "Cold" in advice
    assert score == 7


def test_weather_score_hot():
    score, advice = get_weather_score(32.0, 50.0)
    assert score < 10
    assert "Hot" in advice


def test_weather_score_very_hot():
    score, advice = get_weather_score(36.0, 50.0)
    assert score < 10
    assert score <= 6


def test_weather_score_high_humidity():
    score, advice = get_weather_score(20.0, 90.0)
    assert score < 10
    assert score == 8


def test_weather_score_bad_conditions():
    score, advice = get_weather_score(38.0, 95.0)
    assert score < 5
    assert "Not ideal" in advice


def test_weather_score_freezing():
    score, advice = get_weather_score(-2.0, 50.0)
    assert score <= 5
