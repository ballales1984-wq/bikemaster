"""Tests for monitoring module."""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.monitoring import (
    HealthStatus,
    MetricsMiddleware,
    asyncio_if_awaitable,
    check_database_health,
    check_redis_health,
    check_task_queue_health,
    comprehensive_health_check,
)


def test_health_status_defaults():
    hs = HealthStatus(healthy=True)
    assert hs.healthy is True
    assert hs.checks == {}
    assert isinstance(hs.timestamp, float)
    d = hs.to_dict()
    assert d["healthy"] is True
    assert "timestamp" in d


def test_health_status_with_checks():
    hs = HealthStatus(healthy=False, checks={"db": "unhealthy: err"})
    assert hs.healthy is False
    assert hs.checks["db"] == "unhealthy: err"


@pytest.mark.asyncio
async def test_check_database_health_success():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = (1,)
    mock_conn.cursor.return_value = mock_cur
    with patch("bike_analyzer.backend.db.database.get_db_connection", return_value=mock_conn):
        status, msg = await check_database_health()
    assert status == "healthy"
    assert "OK" in msg


@pytest.mark.asyncio
async def test_check_database_health_failure():
    with patch(
        "bike_analyzer.backend.db.database.get_db_connection",
        side_effect=RuntimeError("db down"),
    ):
        status, msg = await check_database_health()
    assert status == "unhealthy"
    assert "db down" in msg


@pytest.mark.asyncio
async def test_check_redis_health_success():
    mock_r = MagicMock()
    mock_r.ping.return_value = True
    with patch("bike_analyzer.backend.redis_client.get_redis", return_value=mock_r):
        status, msg = await check_redis_health()
    assert status == "healthy"
    assert "OK" in msg


@pytest.mark.asyncio
async def test_check_redis_health_degraded():
    with patch("bike_analyzer.backend.redis_client.get_redis", return_value=None):
        status, msg = await check_redis_health()
    assert status == "degraded"
    assert "in-memory" in msg


@pytest.mark.asyncio
async def test_check_redis_health_failure():
    with patch(
        "bike_analyzer.backend.redis_client.get_redis",
        side_effect=RuntimeError("redis down"),
    ):
        status, msg = await check_redis_health()
    assert status == "unhealthy"


@pytest.mark.asyncio
async def test_check_task_queue_health_success():
    mock_q = MagicMock()
    mock_q._tasks = [1, 2, 3]
    with patch("bike_analyzer.backend.task_queue.get_task_queue", return_value=mock_q):
        status, msg = await check_task_queue_health()
    assert status == "healthy"
    assert "3 tasks" in msg


@pytest.mark.asyncio
async def test_check_task_queue_health_failure():
    with patch(
        "bike_analyzer.backend.task_queue.get_task_queue",
        side_effect=RuntimeError("tq down"),
    ):
        status, msg = await check_task_queue_health()
    assert status == "unhealthy"


@pytest.mark.asyncio
async def test_comprehensive_health_check():
    with patch(
        "bike_analyzer.backend.monitoring.check_database_health",
        return_value=("healthy", "OK"),
    ), patch(
        "bike_analyzer.backend.monitoring.check_redis_health",
        return_value=("healthy", "OK"),
    ), patch(
        "bike_analyzer.backend.monitoring.check_task_queue_health",
        return_value=("healthy", "OK"),
    ):
        hs = await comprehensive_health_check()
    assert hs.healthy is True
    assert "database" in hs.checks


@pytest.mark.asyncio
async def test_asyncio_if_awaitable_coroutine():
    async def coro():
        return 42

    result = await asyncio_if_awaitable(coro())
    assert result == 42


@pytest.mark.asyncio
async def test_asyncio_if_awaitable_plain():
    result = await asyncio_if_awaitable(99)
    assert result == 99


def test_record_functions_no_prometheus(monkeypatch):
    import bike_analyzer.backend.monitoring as mon

    monkeypatch.setattr(mon, "PROMETHEUS_AVAILABLE", False)
    mon.record_http_request("GET", "/test", 200, 0.1)
    mon.record_ride_processed("success")
    mon.record_background_task("import", "done")
    mon.record_cache(True)
    mon.record_ai_coach_request("success")
    mon.record_import("strava", "success")
    mon.record_gps_import("gpx", "upload")
    mon.record_ride_analysis_duration(1.5)
    mon.record_fatigue_score(5.0)
    mon.record_ai_coach_query("groq", "success")
    mon.record_tracking_session()
    mon.set_active_athletes(10)


def test_start_metrics_server_no_prometheus(monkeypatch):
    import bike_analyzer.backend.monitoring as mon

    monkeypatch.setattr(mon, "PROMETHEUS_AVAILABLE", False)
    with patch.object(mon.logger, "info") as mock_info:
        mon.start_metrics_server()
    mock_info.assert_called_once()


def test_metrics_middleware():
    app = MagicMock()
    middleware = MetricsMiddleware(app)
    scope = {"type": "http", "method": "GET", "path": "/test"}

    async def receive():
        return {"type": "http.request"}

    sent = []

    async def send(message):
        sent.append(message)

    async def fake_app(s, r, snd):
        await snd({"type": "http.response.start", "status": 200})
        await snd({"type": "http.response.body", "body": b"ok"})

    middleware.app = fake_app
    asyncio.run(middleware(scope, receive, send))
    assert sent[0]["status"] == 200
