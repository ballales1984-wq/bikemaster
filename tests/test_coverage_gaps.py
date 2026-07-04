"""Coverage gap tests: strava/garmin token refresh, engine async paths."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bike_analyzer.core.engine import AnalysisEngine
from bike_analyzer.core.models import Ride
from bike_analyzer.core.pipeline import PipelineResult

# ---------------------------------------------------------------------------
# Strava client token refresh
# ---------------------------------------------------------------------------


class TestStravaTokenRefresh:
    """Test get_valid_token refresh flow and related functions."""

    def test_get_valid_token_refreshes_expired(self, monkeypatch):
        import bike_analyzer.backend.ingestion.strava_client as sc

        now = time.time()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            "old_access",
            "old_refresh",
            int(now - 10000),
        )

        with (
            patch.object(sc, "_ensure_token_table"),
            patch.object(sc, "_get_conn", return_value=mock_conn),
            patch.object(
                sc,
                "refresh_access_token",
                return_value={"access_token": "new_access", "refresh_token": "new_refresh"},
            ),
        ):
            result = sc.get_valid_token(1)
            assert result == "new_access"

    def test_get_valid_token_returns_existing_when_valid(self, monkeypatch):
        import bike_analyzer.backend.ingestion.strava_client as sc

        now = time.time()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            "valid_access",
            "valid_refresh",
            int(now + 3600),
        )

        with patch.object(sc, "_ensure_token_table"), patch.object(sc, "_get_conn", return_value=mock_conn):
            result = sc.get_valid_token(1)
            assert result == "valid_access"

    def test_get_valid_token_returns_none_when_no_row(self, monkeypatch):
        import bike_analyzer.backend.ingestion.strava_client as sc

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch.object(sc, "_ensure_token_table"), patch.object(sc, "_get_conn", return_value=mock_conn):
            result = sc.get_valid_token(999)
            assert result is None

    def test_store_token_calls_upsert(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch.object(sc, "_ensure_token_table"), patch.object(sc, "_get_conn", return_value=mock_conn):
            sc.store_token(1, {"access_token": "at", "refresh_token": "rt", "expires_at": 12345})
            assert mock_conn.execute.called

    def test_revoke_token_deletes_row(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch.object(sc, "_ensure_token_table"), patch.object(sc, "_get_conn", return_value=mock_conn):
            sc.revoke_token(1)
            assert mock_conn.execute.called

    def test_get_authorization_url_returns_dict(self, monkeypatch):
        import bike_analyzer.backend.ingestion.strava_client as sc

        monkeypatch.setattr(sc, "STRAVA_CLIENT_ID", "test_client_id")
        result = sc.get_authorization_url()
        assert "auth_url" in result
        assert "state" in result
        assert "code_verifier" in result

    def test_build_authorization_url(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        url = sc.build_authorization_url("state123", "challenge456")
        assert "client_id=" in url
        assert "state=state123" in url
        assert "code_challenge=challenge456" in url

    def test_refresh_access_token_http_call(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "rt_at", "refresh_token": "rt_rt"}
        mock_response.raise_for_status.return_value = None

        with patch("bike_analyzer.backend.ingestion.strava_client.requests.post", return_value=mock_response):
            result = sc.refresh_access_token("refresh_token_abc")
            assert result["access_token"] == "rt_at"

    def test_get_valid_token_refresh_failure_returns_none(self, monkeypatch):
        import bike_analyzer.backend.ingestion.strava_client as sc

        now = time.time()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            "old_access",
            "old_refresh",
            int(now - 10000),
        )

        with (
            patch.object(sc, "_ensure_token_table"),
            patch.object(sc, "_get_conn", return_value=mock_conn),
            patch.object(
                sc,
                "refresh_access_token",
                side_effect=RuntimeError("refresh failed"),
            ),
        ):
            result = sc.get_valid_token(1)
            assert result is None

    def test_fetch_activities_success(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "name": "Ride1"}, {"id": 2, "name": "Ride2"}]
        mock_response.raise_for_status.return_value = None

        with patch("bike_analyzer.backend.ingestion.strava_client.requests.get", return_value=mock_response):
            result = sc.fetch_activities("token123", page=1, per_page=10)
            assert len(result) == 2

    def test_fetch_all_activities_stops_on_empty_batch(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        with patch.object(sc, "fetch_activities", return_value=[]) as mock_fetch:
            result = sc.fetch_all_activities("token123", max_pages=5)
            assert result == []
            mock_fetch.assert_called_once()

    def test_fetch_all_activities_accumulates(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        batch = [{"id": i} for i in range(10)]
        empty_batch = []
        with patch.object(sc, "fetch_activities", side_effect=[batch, empty_batch]):
            result = sc.fetch_all_activities("token123", max_pages=2)
            assert len(result) == 10


# ---------------------------------------------------------------------------
# Garmin client token refresh
# ---------------------------------------------------------------------------


class TestGarminTokenRefresh:
    """Test get_valid_token refresh flow and related functions."""

    def test_get_valid_token_refreshes_expired(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        now = time.time()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            "old_access",
            "old_refresh",
            int(now - 10000),
        )

        with (
            patch.object(gc, "_ensure_garmin_table"),
            patch.object(gc, "_get_conn", return_value=mock_conn),
            patch.object(
                gc,
                "refresh_access_token",
                return_value={"access_token": "new_access", "refresh_token": "new_refresh"},
            ),
        ):
            result = gc.get_valid_token(1)
            assert result == "new_access"

    def test_get_valid_token_returns_existing_when_valid(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        now = time.time()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            "valid_access",
            "valid_refresh",
            int(now + 3600),
        )

        with patch.object(gc, "_ensure_garmin_table"), patch.object(gc, "_get_conn", return_value=mock_conn):
            result = gc.get_valid_token(1)
            assert result == "valid_access"

    def test_get_valid_token_returns_none_when_no_row(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch.object(gc, "_ensure_garmin_table"), patch.object(gc, "_get_conn", return_value=mock_conn):
            result = gc.get_valid_token(999)
            assert result is None

    def test_store_token_handles_string_expires_at(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch.object(gc, "_ensure_garmin_table"), patch.object(gc, "_get_conn", return_value=mock_conn):
            gc.store_token(1, {"access_token": "at", "refresh_token": "rt", "expires_at": "9999999999"})
            assert mock_conn.execute.called

    def test_store_token_handles_expires_in(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch.object(gc, "_ensure_garmin_table"), patch.object(gc, "_get_conn", return_value=mock_conn):
            gc.store_token(1, {"access_token": "at", "refresh_token": "rt", "expires_in": 3600})
            assert mock_conn.execute.called

    def test_revoke_token_deletes_row(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch.object(gc, "_ensure_garmin_table"), patch.object(gc, "_get_conn", return_value=mock_conn):
            gc.revoke_token(1)
            assert mock_conn.execute.called

    def test_fetch_activities_returns_list(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        mock_response = MagicMock()
        mock_response.json.return_value = [{"activityId": 1}]
        mock_response.raise_for_status.return_value = None

        with patch("bike_analyzer.backend.ingestion.garmin_client.requests.get", return_value=mock_response):
            result = gc.fetch_activities("token123")
            assert len(result) == 1

    def test_fetch_activities_returns_nested(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        mock_response = MagicMock()
        mock_response.json.return_value = {"activities": [{"activityId": 2}]}
        mock_response.raise_for_status.return_value = None

        with patch("bike_analyzer.backend.ingestion.garmin_client.requests.get", return_value=mock_response):
            result = gc.fetch_activities("token123")
            assert len(result) == 1
            assert result[0]["activityId"] == 2

    def test_refresh_access_token_http_call(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "rt_at", "refresh_token": "rt_rt"}
        mock_response.raise_for_status.return_value = None

        with patch("bike_analyzer.backend.ingestion.garmin_client.requests.post", return_value=mock_response):
            result = gc.refresh_access_token("refresh_token_abc")
            assert result["access_token"] == "rt_at"


# ---------------------------------------------------------------------------
# Engine async paths
# ---------------------------------------------------------------------------


class TestEngineAsyncPaths:
    """Test AnalysisEngine async methods."""

    def _make_ride(self) -> Ride:
        return Ride(
            id=1,
            athlete_id=1,
            date="2026-06-14T10:00:00+00:00",
            distance_km=40.0,
            duration_minutes=120.0,
            avg_speed_kmh=20.0,
            weight_kg=75.0,
            calories=800.0,
            heart_rate_avg=155.0,
            elevation_gain_m=400.0,
            gps_points=[],
        )

    def test_process_ride_async_success(self):
        engine = AnalysisEngine()
        ride = self._make_ride()

        mock_result = PipelineResult(ride=ride, metrics={"tss": 50.0})
        mock_fitness = MagicMock()

        async def fake_run(r):
            return mock_result

        async def fake_update(ride, athlete_id, session_factory, historical_rides=None):
            return mock_fitness

        with (
            patch.object(engine.pipeline, "run", side_effect=fake_run),
            patch.object(engine, "_update_fitness_state", side_effect=fake_update),
        ):
            import asyncio

            result = asyncio.run(engine.process_ride(ride, athlete_id=1))
            assert result.success is True
            assert result.result == mock_result
            assert result.fitness_state == mock_fitness

    def test_process_ride_async_failure(self):
        engine = AnalysisEngine()
        ride = self._make_ride()

        async def fake_run(r):
            raise RuntimeError("Pipeline error")

        with patch.object(engine.pipeline, "run", side_effect=fake_run):
            import asyncio

            result = asyncio.run(engine.process_ride(ride))
            assert result.success is False
            assert "Pipeline error" in result.error

    def test_process_ride_sync_success(self):
        engine = AnalysisEngine()
        ride = self._make_ride()
        result = engine.process_ride_sync(ride)
        assert result.success is True
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_update_fitness_state_none_athlete_id(self):
        engine = AnalysisEngine()
        ride = self._make_ride()
        fv = await engine._update_fitness_state(ride, None, None)
        assert fv is None

    @pytest.mark.asyncio
    async def test_update_fitness_state_with_session_factory(self):
        engine = AnalysisEngine()
        ride = self._make_ride()

        mock_repo = AsyncMock()
        mock_repo.save.return_value = None

        with patch(
            "bike_analyzer.core.engine.FitnessStateRepository",
            return_value=mock_repo,
        ):
            fv = await engine._update_fitness_state(ride, 1, MagicMock())
            assert fv is not None
            assert fv.athlete_id == 1
            mock_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_fitness_state_persist_failure_does_not_raise(self):
        engine = AnalysisEngine()
        ride = self._make_ride()

        mock_repo = AsyncMock()
        mock_repo.save.side_effect = RuntimeError("db error")

        with patch(
            "bike_analyzer.core.engine.FitnessStateRepository",
            return_value=mock_repo,
        ):
            fv = await engine._update_fitness_state(ride, 1, MagicMock())
            assert fv is not None

    def test_process_rides_batch(self):
        engine = AnalysisEngine()
        ride = self._make_ride()

        import asyncio

        async def fake_run(r):
            return PipelineResult(ride=r, metrics={"tss": 10.0})

        with patch.object(engine.pipeline, "run", side_effect=fake_run):
            results = asyncio.run(engine.process_rides_batch([ride, ride], athlete_id=1))
            assert len(results) == 2
            assert all(r.success for r in results)
