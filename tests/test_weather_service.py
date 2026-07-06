
from bike_analyzer.backend.weather.weather_service import (
    _get_weather_api_key,
    get_weather_score,
)


def test_get_weather_api_key_from_env(monkeypatch):
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)
    monkeypatch.setenv("OPENWEATHER_API_KEY", "env-key")
    assert _get_weather_api_key() == "env-key"


def test_get_weather_api_key_from_config(monkeypatch):
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    import bike_analyzer.backend.weather.weather_service as ws
    monkeypatch.setattr(ws, "WEATHER_API_KEY", "config-key", raising=False)
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    result = _get_weather_api_key()
    assert isinstance(result, str)


def test_get_weather_score_hot():
    score, advice = get_weather_score(35.0, 50.0)
    assert 0 <= score <= 10
    assert isinstance(advice, str)


def test_get_weather_score_cold():
    score, advice = get_weather_score(0.0, 50.0)
    assert 0 <= score <= 10
    assert isinstance(advice, str)


def test_get_weather_score_ideal():
    score, advice = get_weather_score(20.0, 50.0)
    assert 0 <= score <= 10


def test_get_weather_score_very_hot():
    score, advice = get_weather_score(38.0, 80.0)
    assert score < 10
    assert "hydration" in advice.lower() or "hot" in advice.lower()


def test_get_weather_score_very_cold():
    score, advice = get_weather_score(-5.0, 50.0)
    assert score < 10
    assert "cold" in advice.lower() or "warm" in advice.lower()
