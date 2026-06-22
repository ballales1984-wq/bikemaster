"""Tests for async_db layer coverage."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from bike_analyzer.backend.db.async_db import (
    _get_engine,
    get_session_factory,
    _ride_model_to_dict,
)


class TestEngineFactory:
    def test_get_engine_caches(self):
        with patch("bike_analyzer.backend.db.async_db._engine", None):
            with patch("bike_analyzer.backend.db.async_db.get_settings") as mock_settings:
                mock_settings.return_value.database_url = ""
                mock_settings.return_value.db_path = ":memory:"
                engine1 = _get_engine()
                engine2 = _get_engine()
                assert engine1 is engine2

    @patch("bike_analyzer.backend.db.async_db._engine", None)
    def test_get_engine_sqlite_url(self):
        with patch("bike_analyzer.backend.db.async_db.get_settings") as mock_settings:
            mock_settings.return_value.database_url = ""
            mock_settings.return_value.db_path = "test.db"
            engine = _get_engine()
            assert engine is not None

    @pytest.mark.skip(reason="Requires asyncpg PostgreSQL driver")
    @patch("bike_analyzer.backend.db.async_db._engine", None)
    def test_get_engine_postgres_url(self):
        with patch("bike_analyzer.backend.db.async_db.get_settings") as mock_settings:
            mock_settings.return_value.database_url = "postgresql://user:pass@localhost/db"
            mock_settings.return_value.db_path = "test.db"
            engine = _get_engine()
            assert engine is not None


class TestSessionFactory:
    @pytest.mark.skip(reason="Requires aiosqlite or asyncpg driver")
    @patch("bike_analyzer.backend.db.async_db._engine", None)
    @patch("bike_analyzer.backend.db.async_db._async_session_factory", None)
    def test_get_session_factory_creates(self):
        with patch("bike_analyzer.backend.db.async_db.get_settings") as mock_settings:
            mock_settings.return_value.database_url = "sqlite:///:memory:"
            mock_settings.return_value.db_path = ":memory:"
            factory = get_session_factory()
            assert factory is not None


class TestRideModelToDict:
    def _make_row(self, **kwargs):
        defaults = {
            "id": 1, "athlete_id": 1, "date": "2024-06-15",
            "distance_km": 25.0, "duration_minutes": 60.0,
            "avg_speed_kmh": 25.0, "weight_kg": 70.0,
            "calories": 600.0, "heart_rate_avg": 150.0,
            "elevation_gain_m": 200.0, "gps_points": None,
            "created_at": None,
        }
        defaults.update(kwargs)
        row = MagicMock()
        for k, v in defaults.items():
            setattr(row, k, v)
        return row

    def test_basic_row(self):
        row = self._make_row()
        result = _ride_model_to_dict(row)
        assert result["id"] == 1
        assert result["distance_km"] == 25.0
        assert result["gps_points"] is None

    def test_row_with_gps_points(self):
        import json
        gps_data = [{"lat": 45.0, "lon": 9.0}]
        row = self._make_row(gps_points=json.dumps(gps_data))
        result = _ride_model_to_dict(row)
        assert result["gps_points"] == gps_data

    def test_row_with_datetime(self):
        from datetime import datetime, UTC
        row = self._make_row(created_at=datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC))
        result = _ride_model_to_dict(row)
        assert "2024-06-15" in result["created_at"]
