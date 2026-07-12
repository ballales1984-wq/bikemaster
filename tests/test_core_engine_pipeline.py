"""Tests for the core analysis engine and processing pipeline.

Raises coverage of ``bike_analyzer.core.engine`` and ``bike_analyzer.core.pipeline``
by exercising both the synchronous and async entry points, the historical vs.
single-ride fitness-state branches, and the failure paths.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from bike_analyzer.core.engine import AnalysisEngine, EngineResult
from bike_analyzer.core.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.core.pipeline import AnalysisPipeline, PipelineResult


def _make_ride(*, with_points: bool = True, duration_minutes: float = 60.0, **kw) -> Ride:
    points = None
    if with_points:
        base = datetime(2026, 6, 1, 8, 0, 0)
        points = [
            GPSPoint(lat=45.0 + i * 0.0001, lon=9.0 + i * 0.0001, timestamp=base + timedelta(seconds=i), altitude=100.0 + i, speed=10.0)
            for i in range(10)
        ]
    kw.setdefault("id", 1)
    kw.setdefault("athlete_id", 1)
    return Ride(
        date="2026-06-01T08:00:00",
        distance_km=10.0,
        duration_minutes=duration_minutes,
        avg_speed_kmh=10.0,
        weight_kg=70.0,
        gps_points=points,
        **kw,
    )


# --------------------------------------------------------------------------- #
# AnalysisPipeline
# --------------------------------------------------------------------------- #
def test_pipeline_run_with_gps_points():
    ride = _make_ride()
    result = AnalysisPipeline(ftp=250.0).run_sync(ride)
    assert isinstance(result, PipelineResult)
    assert result.ride is ride
    assert result.route_statistics is not None
    assert result.route_statistics.segment_count > 0
    assert "tss" in result.metrics
    assert result.metrics["fatigue_score"] >= 0


def test_pipeline_run_without_gps_points():
    ride = _make_ride(with_points=False)
    result = AnalysisPipeline().run_sync(ride)
    assert result.route_statistics is None
    assert result.metrics is not None
    assert "calories" in result.metrics


@pytest.mark.asyncio
async def test_pipeline_run_async():
    result = await AnalysisPipeline().run(_make_ride())
    assert isinstance(result, PipelineResult)


# --------------------------------------------------------------------------- #
# AnalysisEngine — success paths
# --------------------------------------------------------------------------- #
def test_engine_sync_processing():
    engine = AnalysisEngine(ftp=250.0, athlete_profile=AthleteProfile(id=1))
    res = engine.process_ride_sync(_make_ride())
    assert res.success is True
    assert res.result is not None
    assert res.fitness_state is None  # no athlete_id passed


def test_engine_sync_processing_handles_error():
    engine = AnalysisEngine()

    def boom(ride):
        raise RuntimeError("sync boom")

    engine.pipeline.run_sync = boom  # type: ignore[assignment]
    res = engine.process_ride_sync(_make_ride())
    assert res.success is False
    assert "sync boom" in res.error


@pytest.mark.asyncio
async def test_engine_process_ride_no_athlete():
    engine = AnalysisEngine()
    res = await engine.process_ride(_make_ride(), athlete_id=None)
    assert res.success is True
    assert res.fitness_state is None


@pytest.mark.asyncio
async def test_engine_process_ride_single_ride_fitness_state():
    engine = AnalysisEngine(ftp=250.0)
    res = await engine.process_ride(_make_ride(), athlete_id=7)
    assert res.success is True
    fs = res.fitness_state
    assert fs is not None
    assert fs.athlete_id == 7
    assert fs.atl >= 0 and fs.ctl >= 0
    assert fs.tsb == round(fs.ctl - fs.atl, 1)
    assert fs.trend_7d == "stable"


@pytest.mark.asyncio
async def test_engine_process_ride_with_historical_rides():
    engine = AnalysisEngine(ftp=250.0)
    historical = [
        Ride(id=10, athlete_id=2, date="2026-05-01T08:00:00", duration_minutes=60.0, distance_km=20.0, avg_speed_kmh=20.0),
        Ride(id=11, athlete_id=2, date="2026-05-02T08:00:00", duration_minutes=90.0, distance_km=30.0, avg_speed_kmh=20.0),
    ]
    res = await engine.process_ride(_make_ride(athlete_id=2), athlete_id=2, historical_rides=historical)
    assert res.success is True
    assert res.fitness_state is not None
    assert res.fitness_state.weekly_tss >= 0


@pytest.mark.asyncio
async def test_engine_process_rides_batch():
    engine = AnalysisEngine(ftp=250.0)
    rides = [_make_ride(id=i, athlete_id=3) for i in (1, 2)]
    results = await engine.process_rides_batch(rides, athlete_id=3)
    assert len(results) == 2
    assert all(isinstance(r, EngineResult) and r.success for r in results)


# --------------------------------------------------------------------------- #
# AnalysisEngine — failure / degradation paths
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_engine_process_ride_handles_pipeline_error():
    engine = AnalysisEngine()

    async def boom(ride):
        raise RuntimeError("boom")

    engine.pipeline.run = boom  # type: ignore[assignment]
    res = await engine.process_ride(_make_ride(), athlete_id=None)
    assert res.success is False
    assert "boom" in res.error


@pytest.mark.asyncio
async def test_engine_persist_skipped_when_repository_unavailable(monkeypatch: pytest.MonkeyPatch):
    import bike_analyzer.core.engine as engine_mod

    monkeypatch.setattr(engine_mod, "FitnessStateRepository", None)
    engine = AnalysisEngine(ftp=250.0)

    class FakeSession:
        pass

    fs = await engine._update_fitness_state(_make_ride(), athlete_id=5, session_factory=FakeSession())
    assert fs is not None
    assert fs.athlete_id == 5


@pytest.mark.asyncio
async def test_engine_persists_fitness_state(monkeypatch: pytest.MonkeyPatch):
    import bike_analyzer.core.engine as engine_mod

    class FakeRepo:
        saved: dict | None = None

        def __init__(self, session_factory):
            self.session_factory = session_factory

        async def save(self, data: dict) -> None:
            FakeRepo.saved = data

    monkeypatch.setattr(engine_mod, "FitnessStateRepository", FakeRepo)
    engine = AnalysisEngine(ftp=250.0)

    fs = await engine._update_fitness_state(_make_ride(), athlete_id=9, session_factory=object())
    assert fs is not None
    assert FakeRepo.saved is not None
    assert FakeRepo.saved["athlete_id"] == 9


@pytest.mark.asyncio
async def test_engine_batch_loads_historical_rides(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_rides(athlete_id, tenant_id=None, limit=90):
        return [
            {
                "id": 20,
                "athlete_id": athlete_id,
                "tenant_id": 0,
                "date": "2026-05-01T08:00:00",
                "distance_km": 20.0,
                "duration_minutes": 60.0,
                "avg_speed_kmh": 20.0,
                "weight_kg": 70.0,
                "calories": 0.0,
                "activity_type": "ride",
                "is_official": True,
                "source": "manual",
            }
        ]

    monkeypatch.setattr(
        "bike_analyzer.backend.db.async_db.get_rides_by_athlete_async",
        fake_get_rides,
    )
    engine = AnalysisEngine(ftp=250.0)
    results = await engine.process_rides_batch([_make_ride(id=1, athlete_id=4)], athlete_id=4, session_factory=object())
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].fitness_state is not None
