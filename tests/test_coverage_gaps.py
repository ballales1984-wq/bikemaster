"""Coverage gap tests: strava/garmin token refresh, engine async paths."""

from __future__ import annotations

import asyncio
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

    def test_get_valid_token_refreshes_expired(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        with (
            patch("bike_analyzer.backend.db.database.get_strava_token", return_value={
                "access_token": "old_access",
                "refresh_token": "old_refresh",
                "expires_at": int(time.time()) - 10000,
            }),
            patch("bike_analyzer.backend.db.token_crypto.decrypt_token", side_effect=lambda x: x),
            patch(
                "bike_analyzer.backend.ingestion.strava_client.refresh_access_token",
                new=AsyncMock(
                    return_value={"access_token": "new_access", "refresh_token": "new_refresh"}
                ),
            ),
        ):
            result = asyncio.run(sc.get_valid_token(1))
            assert result == "new_access"

    def test_get_valid_token_returns_existing_when_valid(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        with (
            patch("bike_analyzer.backend.db.database.get_strava_token", return_value={
                "access_token": "valid_access",
                "refresh_token": "valid_refresh",
                "expires_at": int(time.time()) + 3600,
            }),
            patch("bike_analyzer.backend.db.token_crypto.decrypt_token", side_effect=lambda x: x),
        ):
            result = asyncio.run(sc.get_valid_token(1))
            assert result == "valid_access"

    def test_get_valid_token_returns_none_when_no_row(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        with patch("bike_analyzer.backend.db.database.get_strava_token", return_value=None):
            result = asyncio.run(sc.get_valid_token(999))
            assert result is None

    def test_store_token_calls_upsert(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        with (
            patch("bike_analyzer.backend.db.database.save_strava_token") as mock_save,
            patch("bike_analyzer.backend.db.token_crypto.encrypt_token", side_effect=lambda x: x),
        ):
            sc.store_token(1, {"access_token": "at", "refresh_token": "rt", "expires_at": 12345})
            mock_save.assert_called_once()

    def test_revoke_token_deletes_row(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        with patch("bike_analyzer.backend.db.database.revoke_strava_token") as mock_revoke:
            sc.revoke_token(1)
            mock_revoke.assert_called_once_with(1)

    def test_get_authorization_url_returns_dict(self, monkeypatch):
        import bike_analyzer.backend.ingestion.strava_client as sc

        monkeypatch.setattr(sc._s, "strava_client_id", "test_client_id")
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

        async def fake_request_json(method, url, **kwargs):
            return {"access_token": "rt_at", "refresh_token": "rt_rt"}

        with patch.object(sc, "request_json", side_effect=fake_request_json):
            result = asyncio.run(sc.refresh_access_token("refresh_token_abc"))
            assert result["access_token"] == "rt_at"

    def test_get_valid_token_refresh_failure_returns_none(self, monkeypatch):
        import bike_analyzer.backend.ingestion.strava_client as sc

        with (
            patch("bike_analyzer.backend.db.database.get_strava_token", return_value={
                "access_token": "old_access",
                "refresh_token": "old_refresh",
                "expires_at": int(time.time()) - 10000,
            }),
            patch("bike_analyzer.backend.db.token_crypto.decrypt_token", side_effect=lambda x: x),
            patch.object(
                sc,
                "refresh_access_token",
                side_effect=RuntimeError("refresh failed"),
            ),
        ):
            result = asyncio.run(sc.get_valid_token(1))
            assert result is None

    def test_fetch_activities_success(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        async def fake_request_json(method, url, **kwargs):
            return [{"id": 1, "name": "Ride1"}, {"id": 2, "name": "Ride2"}]

        with patch.object(sc, "request_json", side_effect=fake_request_json):
            result = asyncio.run(sc.fetch_activities("token123", page=1, per_page=10))
            assert len(result) == 2

    def test_fetch_all_activities_stops_on_empty_batch(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        async def fake_fetch(*args, **kwargs):
            return []

        with patch.object(sc, "fetch_activities", side_effect=fake_fetch) as mock_fetch:
            result = asyncio.run(sc.fetch_all_activities("token123", max_pages=5))
            assert result == []
            mock_fetch.assert_called_once()

    def test_fetch_all_activities_accumulates(self):
        import bike_analyzer.backend.ingestion.strava_client as sc

        batch = [{"id": i} for i in range(10)]
        empty_batch = []

        async def fake_fetch(*args, **kwargs):
            call_count = fake_fetch.call_count
            fake_fetch.call_count += 1
            return batch if call_count == 0 else empty_batch

        fake_fetch.call_count = 0

        with patch.object(sc, "fetch_activities", side_effect=fake_fetch):
            result = asyncio.run(sc.fetch_all_activities("token123", max_pages=2))
            assert len(result) == 10


# ---------------------------------------------------------------------------
# Garmin client token refresh
# ---------------------------------------------------------------------------


class TestGarminTokenRefresh:
    """Test get_valid_token refresh flow and related functions."""

    def test_get_valid_token_refreshes_expired(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        with (
            patch("bike_analyzer.backend.db.database.get_garmin_token", return_value={
                "access_token": "old_access",
                "refresh_token": "old_refresh",
                "expires_at": int(time.time()) - 10000,
            }),
            patch("bike_analyzer.backend.db.token_crypto.decrypt_token", side_effect=lambda x: x),
            patch.object(
                gc,
                "refresh_access_token",
                new=AsyncMock(
                    return_value={"access_token": "new_access", "refresh_token": "new_refresh"}
                ),
            ),
        ):
            result = asyncio.run(gc.get_valid_token(1))
            assert result == "new_access"

    def test_get_valid_token_returns_existing_when_valid(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        with (
            patch("bike_analyzer.backend.db.database.get_garmin_token", return_value={
                "access_token": "valid_access",
                "refresh_token": "valid_refresh",
                "expires_at": int(time.time()) + 3600,
            }),
            patch("bike_analyzer.backend.db.token_crypto.decrypt_token", side_effect=lambda x: x),
        ):
            result = asyncio.run(gc.get_valid_token(1))
            assert result == "valid_access"

    def test_get_valid_token_returns_none_when_no_row(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        with patch("bike_analyzer.backend.db.database.get_garmin_token", return_value=None):
            result = asyncio.run(gc.get_valid_token(999))
            assert result is None

    def test_store_token_handles_string_expires_at(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        with (
            patch("bike_analyzer.backend.db.database.save_garmin_token") as mock_save,
            patch("bike_analyzer.backend.db.token_crypto.encrypt_token", side_effect=lambda x: x),
        ):
            gc.store_token(1, {"access_token": "at", "refresh_token": "rt", "expires_at": "9999999999"})
            mock_save.assert_called_once()

    def test_store_token_handles_expires_in(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        with (
            patch("bike_analyzer.backend.db.database.save_garmin_token") as mock_save,
            patch("bike_analyzer.backend.db.token_crypto.encrypt_token", side_effect=lambda x: x),
        ):
            gc.store_token(1, {"access_token": "at", "refresh_token": "rt", "expires_in": 3600})
            mock_save.assert_called_once()

    def test_revoke_token_deletes_row(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        with patch("bike_analyzer.backend.db.database.revoke_garmin_token") as mock_revoke:
            gc.revoke_token(1)
            mock_revoke.assert_called_once_with(1)

    def test_fetch_activities_returns_list(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        async def fake_request_json(method, url, **kwargs):
            return [{"activityId": 1}]

        with patch.object(gc, "request_json", side_effect=fake_request_json):
            result = asyncio.run(gc.fetch_activities("token123"))
            assert len(result) == 1

    def test_fetch_activities_returns_nested(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        async def fake_request_json(method, url, **kwargs):
            return {"activities": [{"activityId": 2}]}

        with patch.object(gc, "request_json", side_effect=fake_request_json):
            result = asyncio.run(gc.fetch_activities("token123"))
            assert len(result) == 1
            assert result[0]["activityId"] == 2

    def test_refresh_access_token_http_call(self):
        import bike_analyzer.backend.ingestion.garmin_client as gc

        async def fake_request_json(method, url, **kwargs):
            return {"access_token": "rt_at", "refresh_token": "rt_rt"}

        with patch.object(gc, "request_json", side_effect=fake_request_json):
            result = asyncio.run(gc.refresh_access_token("refresh_token_abc"))
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
