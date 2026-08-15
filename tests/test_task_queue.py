"""Tests for task queue module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from bike_analyzer.backend.task_queue import (
    BackgroundTaskQueue,
    Task,
    get_task_queue,
)


def test_task_dataclass():
    t = Task(id="1", kind="import", payload={"x": 1})
    assert t.id == "1"
    assert t.status == "pending"
    assert t.to_dict()["kind"] == "import"


def test_task_to_dict_defaults():
    t = Task(id="1", kind="test")
    d = t.to_dict()
    assert d["payload"] == {}
    assert d["error"] is None
    assert d["status"] == "pending"
    assert isinstance(d["created_at"], float)


@pytest.mark.asyncio
async def test_queue_start_stop():
    q = BackgroundTaskQueue(max_workers=1)
    assert not q._running
    await q.start()
    assert q._running
    assert len(q._workers) == 1
    await q.stop()
    assert not q._running
    assert q._workers == []


@pytest.mark.asyncio
async def test_enqueue_and_get():
    q = BackgroundTaskQueue(max_workers=1)
    await q.start()
    task = await q.enqueue("batch_import", {"files": []})
    assert task.id is not None
    assert q.get_task(task.id) is task
    pending = q.get_pending()
    assert any(t.id == task.id for t in pending)
    await q.stop()


@pytest.mark.asyncio
async def test_execute_unknown_kind():
    q = BackgroundTaskQueue(max_workers=1)
    task = Task(id="x", kind="unknown")
    await q._execute(task, "worker-0")
    assert task.status == "failed"
    assert "Unknown task kind" in (task.error or "")


@pytest.mark.asyncio
async def test_execute_success():
    q = BackgroundTaskQueue(max_workers=1)
    with patch.object(q, "_handle_batch_import", new_callable=AsyncMock, return_value={"ok": True}):
        task = Task(id="y", kind="batch_import", payload={"files": []})
        await q._execute(task, "worker-0")
    assert task.status == "completed"
    assert task.result == {"ok": True}


@pytest.mark.asyncio
async def test_execute_failure():
    q = BackgroundTaskQueue(max_workers=1)
    with patch.object(q, "_handle_batch_import", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
        task = Task(id="z", kind="batch_import", payload={"files": []})
        await q._execute(task, "worker-0")
    assert task.status == "failed"
    assert "boom" in (task.error or "")


@pytest.mark.asyncio
async def test_worker_timeout_continues():
    q = BackgroundTaskQueue(max_workers=1)
    with patch.object(q, "_execute", new_callable=AsyncMock):
        await q.start()
        await q.enqueue("batch_import", {})
        await asyncio.sleep(0.1)
        assert q._running
    await q.stop()


@pytest.mark.asyncio
async def test_handle_batch_import_gpx():
    q = BackgroundTaskQueue()
    gpx_content = """<?xml version="1.0"?><gpx version="1.1"><trk><trkseg>
    <trkpt lat="45.0" lon="7.0"><time>2024-06-15T10:00:00Z</time></trkpt>
    <trkpt lat="45.001" lon="7.001"><time>2024-06-15T10:30:00Z</time></trkpt>
    </trkseg></trk></gpx>"""
    payload = {"files": [{"type": "gpx", "content": gpx_content, "name": "test.gpx"}]}
    with patch("bike_analyzer.backend.db.database.save_ride", return_value=1):
        result = await q._handle_batch_import(payload)
    assert "imported" in result


@pytest.mark.asyncio
async def test_handle_generate_map():
    q = BackgroundTaskQueue()
    payload = {
        "points": [{"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00Z"}],
        "ride_id": "123",
    }
    with patch("bike_analyzer.backend.maps.map_renderer.create_route_map", return_value="/tmp/map.html"):
        result = await q._handle_generate_map(payload)
    assert "map_url" in result


@pytest.mark.asyncio
async def test_handle_generate_map_invalid_path():
    q = BackgroundTaskQueue()
    payload = {"points": [], "ride_id": "123"}
    result = await q._handle_generate_map(payload)
    assert "error" in result


@pytest.mark.asyncio
async def test_handle_recalculate_stress_no_rides():
    q = BackgroundTaskQueue()
    with patch("bike_analyzer.backend.analytics.repositories.ride_repository.get_rides_by_athlete", return_value=[]):
        result = await q._handle_recalculate_stress({"athlete_id": 1})
    assert result["updated"] == 0


@pytest.mark.asyncio
async def test_handle_warm_weather():
    q = BackgroundTaskQueue()
    payload = {"lat": 45.0, "lon": 7.0, "dates": ["2024-06-15"]}
    with (
        patch(
            "bike_analyzer.backend.weather.weather_service.get_forecast_for_date",
            return_value={"temp": 25},
        ),
        patch("bike_analyzer.backend.db.database.save_weather_cache"),
    ):
        result = await q._handle_warm_weather(payload)
    assert result["cached_days"] == 1


@pytest.mark.asyncio
async def test_handle_strava_sync_no_token():
    q = BackgroundTaskQueue()
    with patch("bike_analyzer.backend.ingestion.strava_client.get_valid_token", return_value=None):
        result = await q._handle_strava_sync({"athlete_id": 1})
    assert result["error"] == "no_valid_token"


@pytest.mark.asyncio
async def test_handle_garmin_sync_no_token():
    q = BackgroundTaskQueue()
    with patch("bike_analyzer.backend.ingestion.garmin_client.get_valid_token", return_value=None):
        result = await q._handle_garmin_sync({"athlete_id": 1})
    assert result["error"] == "no_valid_token"


def test_get_task_queue_singleton():
    q1 = get_task_queue()
    q2 = get_task_queue()
    assert q1 is q2
