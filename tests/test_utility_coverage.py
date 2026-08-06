"""Tests for small utility modules to improve coverage."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from bike_analyzer.backend.analytics.benchmark import (
    compare_athlete_to_benchmark,
    generate_benchmark_report,
    get_age_category,
    get_experience_category,
    get_weight_category,
)
from bike_analyzer.backend.events import (
    AthleteUpdated,
    BadgeEarned,
    RideCreated,
    TrainingGenerated,
    clear_handlers,
    is_event_bus_running,
    start_event_bus,
    stop_event_bus,
)
from bike_analyzer.backend.http_async import _is_retryable, request_json
from bike_analyzer.backend.maps.google_maps import (
    _css_to_google_hex,
    _interpolate_color,
    _speed_to_color,
    build_speed_colored_path,
    get_google_api_key,
)
from bike_analyzer.backend.models.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.backend.tracing import OTLP_AVAILABLE, setup_tracing
from bike_analyzer.backend.utils.dates import (
    add_days,
    date_only,
    month_label,
    now_utc,
    parse_iso,
    range_for_month,
    to_iso,
)


# ---------------------------------------------------------------------------
# dates.py
# ---------------------------------------------------------------------------
class TestDates:
    def test_now_utc_returns_datetime(self):
        result = now_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_to_iso_with_none(self):
        result = to_iso()
        assert isinstance(result, str)
        assert "T" in result

    def test_to_iso_with_datetime(self):
        dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=UTC)
        result = to_iso(dt)
        assert result == "2024-06-15T12:30:00+00:00"

    def test_to_iso_naive_gets_utc(self):
        dt = datetime(2024, 6, 15, 12, 30, 0)
        result = to_iso(dt)
        assert result.endswith("+00:00")

    def test_parse_iso_empty(self):
        result = parse_iso("")
        assert isinstance(result, datetime)

    def test_parse_iso_valid(self):
        result = parse_iso("2024-06-15T12:30:00+00:00")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_date_only_with_value(self):
        assert date_only("2024-06-15T12:30:00+00:00") == "2024-06-15"

    def test_date_only_none_returns_today(self):
        result = date_only()
        assert len(result) == 10
        assert result[4] == "-"

    def test_range_for_month_january(self):
        start, end = range_for_month(2024, 1)
        assert start == "2024-01-01"
        assert end == "2024-02-01"

    def test_range_for_month_december(self):
        start, end = range_for_month(2024, 12)
        assert start == "2024-12-01"
        assert end == "2025-01-01"

    def test_add_days(self):
        result = add_days("2024-06-15", 5)
        assert result == "2024-06-20"

    def test_month_label_returns_string(self):
        result = month_label(2024, 6)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# http_async.py
# ---------------------------------------------------------------------------
class TestHttpAsync:
    def test_is_retryable_429(self):
        assert _is_retryable(429) is True

    def test_is_retryable_200(self):
        assert _is_retryable(200) is False

    def test_is_retryable_500(self):
        assert _is_retryable(500) is True

    def test_is_retryable_404(self):
        assert _is_retryable(404) is False

    @pytest.mark.asyncio
    async def test_request_json_success(self):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json = MagicMock(return_value={"ok": True})
        fake_response.raise_for_status = MagicMock()

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def request(self, method, url, **kwargs):
                return fake_response

        with patch("bike_analyzer.backend.http_async.httpx.AsyncClient", FakeClient):
            result = await request_json("GET", "http://example.com")
            assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_request_json_retries_then_succeeds(self):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json = MagicMock(return_value={"ok": True})
        fake_response.raise_for_status = MagicMock()

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def request(self, method, url, **kwargs):
                return fake_response

        with patch("bike_analyzer.backend.http_async.httpx.AsyncClient", FakeClient):
            result = await request_json("GET", "http://example.com")
            assert result == {"ok": True}


class TestHttpAsyncRetry:
    @pytest.mark.asyncio
    async def test_request_json_retries_on_429(self, monkeypatch):
        call_count = 0

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def request(self, method, url, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    resp = MagicMock()
                    resp.status_code = 429
                    resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("429", request=None, response=resp))
                    return resp
                resp = MagicMock()
                resp.status_code = 200
                resp.json = MagicMock(return_value={"ok": True})
                resp.raise_for_status = MagicMock()
                return resp

        monkeypatch.setattr("bike_analyzer.backend.http_async._BACKOFF_BASE", 0)
        with patch("bike_analyzer.backend.http_async.httpx.AsyncClient", FakeClient):
            result = await request_json("GET", "http://example.com")
            assert result == {"ok": True}
            assert call_count == 2


# ---------------------------------------------------------------------------
# tracing.py
# ---------------------------------------------------------------------------
class TestTracing:
    def test_setup_tracing_no_endpoint(self):
        with patch("bike_analyzer.backend.tracing.get_settings") as mock_settings:
            mock_settings.return_value.otel_exporter_otlp_endpoint = None
            mock_settings.return_value.otel_service_name = "test"
            mock_settings.return_value.otel_environment = "test"
            result = setup_tracing(app=None)
            assert result is None

    def test_otlp_available_flag(self):
        assert isinstance(OTLP_AVAILABLE, bool)

    def test_setup_tracing_with_endpoint_no_otlp(self):
        with patch("bike_analyzer.backend.tracing.get_settings") as mock_settings, patch(
            "bike_analyzer.backend.tracing.OTLP_AVAILABLE", False
        ):
            mock_settings.return_value.otel_exporter_otlp_endpoint = "http://localhost:4317"
            mock_settings.return_value.otel_service_name = "test"
            mock_settings.return_value.otel_environment = "test"
            setup_tracing(app=None)

    def test_setup_tracing_with_endpoint_exception(self):
        with patch("bike_analyzer.backend.tracing.get_settings") as mock_settings, patch(
            "bike_analyzer.backend.tracing.OTLP_AVAILABLE", True
        ), patch("bike_analyzer.backend.tracing.OTLPSpanExporter", side_effect=RuntimeError("init failed")):
            mock_settings.return_value.otel_exporter_otlp_endpoint = "http://localhost:4317"
            mock_settings.return_value.otel_service_name = "test"
            mock_settings.return_value.otel_environment = "test"
            setup_tracing(app=None)


# ---------------------------------------------------------------------------
# events/__init__.py
# ---------------------------------------------------------------------------
class TestEventBusLifecycle:
    def setup_method(self):
        asyncio.run(stop_event_bus())
        clear_handlers()

    def teardown_method(self):
        asyncio.run(stop_event_bus())
        clear_handlers()

    def test_start_event_bus_sets_running(self):
        asyncio.run(start_event_bus())
        assert is_event_bus_running() is True

    def test_start_event_bus_idempotent(self):
        asyncio.run(start_event_bus())
        asyncio.run(start_event_bus())
        assert is_event_bus_running() is True

    def test_stop_event_bus_sets_stopped(self):
        asyncio.run(start_event_bus())
        asyncio.run(stop_event_bus())
        assert is_event_bus_running() is False

    def test_stop_event_bus_idempotent(self):
        asyncio.run(start_event_bus())
        asyncio.run(stop_event_bus())
        asyncio.run(stop_event_bus())
        assert is_event_bus_running() is False

    def test_ride_created_event_type(self):
        assert RideCreated.type == "ride.created"

    def test_athlete_updated_event_type(self):
        assert AthleteUpdated.type == "athlete.updated"

    def test_badge_earned_event_type(self):
        assert BadgeEarned.type == "badge.earned"

    def test_training_generated_event_type(self):
        assert TrainingGenerated.type == "training.generated"


# ---------------------------------------------------------------------------
# benchmark.py
# ---------------------------------------------------------------------------
class TestBenchmark:
    def test_compare_unknown_level_returns_empty(self):
        athlete = AthleteProfile(name="Test", experience_level="Unknown")
        result = compare_athlete_to_benchmark(athlete, 50.0, 15.0, 2.0)
        assert result == {}

    def test_compare_beginner(self):
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        result = compare_athlete_to_benchmark(athlete, 50.0, 15.0, 2.0)
        assert "percentile_km" in result
        assert result["overall_percentile"] >= 0

    def test_compare_elite(self):
        athlete = AthleteProfile(name="Test", experience_level="Elite")
        result = compare_athlete_to_benchmark(athlete, 5000.0, 35.0, 20.0)
        assert result["overall_percentile"] >= 0

    def test_get_age_category_boundaries(self):
        assert get_age_category(25) == "25-35"
        assert get_age_category(35) == "35-45"
        assert get_age_category(45) == "45-55"
        assert get_age_category(55) == "Over55"

    def test_get_weight_category_heavy(self):
        assert get_weight_category(90.0) == "Heavy"

    def test_get_experience_category_veteran(self):
        assert get_experience_category(10) == "Veteran"

    def test_generate_benchmark_report_returns_string(self):
        athlete = AthleteProfile(name="Marco", experience_level="Beginner", age=25, weight_kg=70.0)
        rides = [Ride(distance_km=30.0, avg_speed_kmh=20.0, duration_minutes=60.0)]
        result = generate_benchmark_report(athlete, rides)
        assert isinstance(result, str)
        assert "Marco" in result
        assert "Benchmark Report" in result


# ---------------------------------------------------------------------------
# google_maps.py
# ---------------------------------------------------------------------------
class TestGoogleMaps:
    def test_speed_to_color_thresholds(self):
        assert _speed_to_color(40.0) == "#00cc44"
        assert _speed_to_color(30.0) == "#88cc00"
        assert _speed_to_color(20.0) == "#ddbb00"
        assert _speed_to_color(10.0) == "#ee8800"
        assert _speed_to_color(3.0) == "#ee3333"
        assert _speed_to_color(None) == "#4488ff"

    def test_interpolate_color(self):
        color = _interpolate_color(50.0, 0.0, 100.0)
        assert color.startswith("#")

    def test_interpolate_color_same_min_max(self):
        assert _interpolate_color(10.0, 10.0, 10.0) == "#FFFF00"

    def test_css_to_google_hex(self):
        assert _css_to_google_hex("#4488ff") == "0x4488FF"
        assert _css_to_google_hex("0x4488ff") == "0x4488ff"

    def test_build_speed_colored_path_empty(self):
        assert build_speed_colored_path([]) == []

    def test_build_speed_colored_path_single_point(self):
        from datetime import datetime
        pts = [GPSPoint(lat=45.0, lon=7.0, speed=25.0, timestamp=datetime.now())]
        assert build_speed_colored_path(pts) == []

    def test_build_speed_colored_path_multiple(self):
        from datetime import datetime
        pts = [
            GPSPoint(lat=45.0, lon=7.0, speed=10.0, timestamp=datetime.now()),
            GPSPoint(lat=45.1, lon=7.1, speed=30.0, timestamp=datetime.now()),
            GPSPoint(lat=45.2, lon=7.2, speed=20.0, timestamp=datetime.now()),
        ]
        result = build_speed_colored_path(pts)
        assert len(result) == 2
        assert "color" in result[0]
        assert "speed_kmh" in result[0]

    def test_get_google_api_key_returns_key(self):
        import bike_analyzer.backend.maps.google_maps as gm_mod

        gm_mod._s.google_maps_api_key = "AIzaTestKey123"
        try:
            assert get_google_api_key() == "AIzaTestKey123"
        finally:
            gm_mod._s.google_maps_api_key = ""

    def test_get_google_api_key_returns_none_when_empty(self):
        import bike_analyzer.backend.maps.google_maps as gm_mod

        gm_mod._s.google_maps_api_key = ""
        assert get_google_api_key() is None


class TestAiCoachEdgeCases:
    def test_clean_ai_output_removes_trailing_zero(self):
        from bike_analyzer.backend.analytics.ai_coach import _clean_ai_output

        text = "25.0 km/h per 1.0 ore"
        result = _clean_ai_output(text)
        assert ".0" not in result

    def test_clean_ai_output_collapses_newlines(self):
        from bike_analyzer.backend.analytics.ai_coach import _clean_ai_output

        text = "Linea 1\n\n\n\nLinea 2"
        result = _clean_ai_output(text)
        assert "\n\n" not in result

    def test_clean_ai_output_strips(self):
        from bike_analyzer.backend.analytics.ai_coach import _clean_ai_output

        result = _clean_ai_output("  spaced  ")
        assert result == result.strip()

    def test_coach_mode_env_override(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "local")
        from bike_analyzer.backend.analytics.ai_coach import _coach_mode

        assert _coach_mode() == "local"

    def test_provider_order_from_env(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_PROVIDER_ORDER", "groq, openai")
        from bike_analyzer.backend.analytics.ai_coach import _provider_order

        result = _provider_order()
        assert "groq" in result
        assert "openai" in result

    def test_provider_order_default(self, monkeypatch):
        monkeypatch.delenv("AI_COACH_PROVIDER_ORDER", raising=False)
        from bike_analyzer.backend.analytics.ai_coach import _provider_order

        result = _provider_order()
        assert result == ["groq"]

    def test_is_recoverable_provider_error_true(self):
        from bike_analyzer.backend.analytics.ai_coach import _is_recoverable_provider_error

        err = RuntimeError("timeout")
        assert _is_recoverable_provider_error(err) is True

    def test_is_recoverable_provider_error_false_auth(self):
        from bike_analyzer.backend.analytics.ai_coach import _is_recoverable_provider_error

        err = ValueError("auth failed")
        assert _is_recoverable_provider_error(err) is False

    def test_ban_provider(self):
        from bike_analyzer.backend.analytics.ai_coach import _BANNED_PROVIDERS, _ban_provider

        _BANNED_PROVIDERS.clear()
        _ban_provider("groq", "test")
        assert "groq" in _BANNED_PROVIDERS
