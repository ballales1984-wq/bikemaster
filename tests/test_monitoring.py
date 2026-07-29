"""Tests for the monitoring module (Prometheus metrics + health checks)."""

from __future__ import annotations

import asyncio

import pytest

import bike_analyzer.backend.monitoring as mon


def test_health_status_to_dict():
    status = mon.HealthStatus(healthy=True, checks={"db": "healthy: ok"})
    d = status.to_dict()
    assert d["healthy"] is True
    assert d["checks"]["db"] == "healthy: ok"
    assert "timestamp" in d


def test_health_status_default_timestamp():
    import time

    before = time.time()
    status = mon.HealthStatus(healthy=False)
    after = time.time()
    assert before <= status.timestamp <= after


def test_record_functions_prometheus_available():
    # These must not raise when prometheus_client is installed.
    mon.record_http_request("GET", "/rides", 200, 0.05)
    mon.record_ride_processed("success")
    mon.record_background_task("import", "done")
    mon.record_cache(True)
    mon.record_cache(False)
    mon.record_ai_coach_request("success")
    mon.record_import("strava", "success")
    mon.record_gps_import("gpx", "strava", "success")
    mon.record_ride_analysis_duration(1.5)
    mon.record_fatigue_score(4.0)
    mon.record_ai_coach_query("groq", "success")
    mon.record_tracking_session()
    mon.set_active_athletes(3)


def test_start_metrics_server_oserror(monkeypatch):
    def boom(port):
        raise OSError("port in use")

    monkeypatch.setattr(mon, "start_http_server", boom)
    # Should swallow the OSError and not propagate.
    mon.start_metrics_server()


def test_start_metrics_server_success(monkeypatch):
    calls = []

    def noop(port):
        calls.append(port)

    monkeypatch.setattr(mon, "start_http_server", noop)
    mon.start_metrics_server()
    assert calls == [mon.PROMETHEUS_PORT]


async def test_check_database_health():
    status, msg = await mon.check_database_health()
    assert status in ("healthy", "unhealthy")
    assert isinstance(msg, str)


async def test_check_database_health_error(monkeypatch):
    import bike_analyzer.backend.db.database as db_mod

    class FakeConn:
        def __enter__(self):
            raise RuntimeError("db down")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(db_mod, "get_db_connection", lambda: FakeConn())
    status, msg = await mon.check_database_health()
    assert status == "unhealthy"
    assert "db down" in msg


async def test_check_redis_health_not_configured():
    status, msg = await mon.check_redis_health()
    assert status in ("degraded", "healthy", "unhealthy")
    assert "Redis" in msg


async def test_check_redis_health_configured(monkeypatch):
    import bike_analyzer.backend.redis_client as redis_client

    class FakeRedis:
        def ping(self):
            return True

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(redis_client, "get_redis", fake_get_redis)
    status, msg = await mon.check_redis_health()
    assert status == "healthy"


async def test_check_redis_health_ping_fails(monkeypatch):
    import bike_analyzer.backend.redis_client as redis_client

    class FakeRedis:
        def ping(self):
            raise ConnectionError("redis down")

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(redis_client, "get_redis", fake_get_redis)
    status, msg = await mon.check_redis_health()
    assert status == "unhealthy"


async def test_check_task_queue_health(monkeypatch):
    import bike_analyzer.backend.task_queue as task_queue

    class FakeQueue:
        _tasks = [1, 2, 3]

    monkeypatch.setattr(task_queue, "get_task_queue", lambda: FakeQueue())
    status, msg = await mon.check_task_queue_health()
    assert status == "healthy"
    assert "3" in msg


async def test_check_task_queue_health_error(monkeypatch):
    import bike_analyzer.backend.task_queue as task_queue

    def boom():
        raise RuntimeError("no queue")

    monkeypatch.setattr(task_queue, "get_task_queue", boom)
    status, msg = await mon.check_task_queue_health()
    assert status == "unhealthy"


async def test_comprehensive_health_check():
    status = await mon.comprehensive_health_check()
    assert isinstance(status, mon.HealthStatus)
    assert "database" in status.checks
    assert "redis" in status.checks
    assert "task_queue" in status.checks
    assert "ai_coach" in status.checks


async def test_check_ai_coach_health_no_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    import bike_analyzer.backend.settings as settings_mod

    monkeypatch.setattr(settings_mod, "get_settings", lambda: type("S", (), {"groq_api_key": ""})())
    status, msg = await mon.check_ai_coach_health()
    assert status == "degraded"
    assert "GROQ_API_KEY" in msg


async def test_check_ai_coach_health_invalid_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "invalid-key")
    import bike_analyzer.backend.settings as settings_mod

    monkeypatch.setattr(settings_mod, "get_settings", lambda: type("S", (), {"groq_api_key": ""})())
    status, msg = await mon.check_ai_coach_health()
    assert status == "degraded"
    assert "gsk_" in msg


async def test_check_ai_coach_health_valid_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key")
    import bike_analyzer.backend.settings as settings_mod

    monkeypatch.setattr(settings_mod, "get_settings", lambda: type("S", (), {"groq_api_key": ""})())
    status, msg = await mon.check_ai_coach_health()
    assert status == "healthy"
    assert "Groq key configured" in msg


async def test_asyncio_if_awaitable_with_awaitable():
    async def coro():
        return 42

    result = await mon.asyncio_if_awaitable(coro())
    assert result == 42


async def test_asyncio_if_awaitable_with_plain():
    result = await mon.asyncio_if_awaitable(42)
    assert result == 42


def test_metrics_middleware_http():
    received = []

    async def fake_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def send(message):
        received.append(message)

    async def receive():
        return {"type": "http.request", "body": b""}

    mw = mon.MetricsMiddleware(fake_app)
    asyncio.run(
        mw(
            {"type": "http", "method": "POST", "path": "/x"},
            receive,
            send,
        )
    )
    start_msg = next(m for m in received if m["type"] == "http.response.start")
    assert start_msg["status"] == 201


def test_metrics_middleware_non_http():
    called = {"yes": False}

    async def fake_app(scope, receive, send):
        called["yes"] = True

    async def send(message):
        pass

    async def receive():
        return {}

    mw = mon.MetricsMiddleware(fake_app)
    asyncio.run(mw({"type": "websocket"}, receive, send))
    assert called["yes"] is True


def test_metrics_middleware_exception_handling():
    async def fake_app(scope, receive, send):
        raise RuntimeError("app error")

    async def send(message):
        pass

    async def receive():
        return {"type": "http.request", "body": b""}

    mw = mon.MetricsMiddleware(fake_app)
    with pytest.raises(RuntimeError, match="app error"):
        asyncio.run(
            mw({"type": "http", "method": "GET", "path": "/test"}, receive, send)
        )


def test_prometheus_unavailable_branch(monkeypatch):
    """Exercise the PROMETHEUS_AVAILABLE=False paths (no-op record_* and the
    'not installed' branch of start_metrics_server) without re-importing the
    module (which would re-register Prometheus collectors)."""
    monkeypatch.setattr(mon, "PROMETHEUS_AVAILABLE", False)
    # record_* functions become safe no-ops.
    mon.record_http_request("GET", "/", 200, 0.1)
    mon.record_ride_processed()
    mon.record_background_task("k", "s")
    mon.record_cache(True)
    mon.record_cache(False)
    mon.record_ai_coach_request()
    mon.record_import("src")
    mon.record_gps_import("gpx", "src")
    mon.record_ride_analysis_duration(1.0)
    mon.record_fatigue_score(3.0)
    mon.record_ai_coach_query("groq")
    mon.record_tracking_session()
    mon.set_active_athletes(5)
    # No metrics server started, no exception.
    mon.start_metrics_server()
    # Health checks still function without prometheus.
    status = asyncio.run(mon.comprehensive_health_check())
    assert status is not None
