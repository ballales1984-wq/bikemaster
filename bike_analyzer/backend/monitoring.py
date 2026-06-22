"""Monitoring module with Prometheus metrics and health checks."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

if PROMETHEUS_AVAILABLE:
    http_requests_total = Counter(
        "bikemaster_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
    )
    http_request_duration_seconds = Histogram(
        "bikemaster_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    active_users_gauge = Gauge(
        "bikemaster_active_users",
        "Number of currently active authenticated users",
    )
    rides_processed_total = Counter(
        "bikemaster_rides_processed_total",
        "Total rides processed",
        ["status"],
    )
    background_tasks_total = Counter(
        "bikemaster_background_tasks_total",
        "Total background tasks",
        ["kind", "status"],
    )
    db_connections_active = Gauge(
        "bikemaster_db_connections_active",
        "Active database connections",
    )
    cache_hits_total = Counter(
        "bikemaster_cache_hits_total",
        "Total cache hits",
    )
    cache_misses_total = Counter(
        "bikemaster_cache_misses_total",
        "Total cache misses",
    )
    ai_coach_requests_total = Counter(
        "bikemaster_ai_coach_requests_total",
        "Total AI Coach requests",
        ["status"],
    )
    import_operations_total = Counter(
        "bikemaster_import_operations_total",
        "Total import operations",
        ["source", "status"],
    )
    system_info = Gauge(
        "bikemaster_system_info",
        "System information",
        ["version", "environment"],
    )
else:
    http_requests_total = None
    http_request_duration_seconds = None
    active_users_gauge = None
    rides_processed_total = None
    background_tasks_total = None
    db_connections_active = None
    cache_hits_total = None
    cache_misses_total = None
    ai_coach_requests_total = None
    import_operations_total = None
    system_info = None


@dataclass
class HealthStatus:
    healthy: bool
    checks: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "checks": self.checks,
            "timestamp": self.timestamp,
        }


async def check_database_health() -> tuple[str, str]:
    try:
        from ..db.database import get_db_connection
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        return "healthy", "Database connection OK"
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return "unhealthy", f"Database error: {exc}"


async def check_redis_health() -> tuple[str, str]:
    try:
        from ..redis_client import get_redis
        r = await get_redis()
        if r is not None:
            await asyncio_if_awaitable(r.ping())
            return "healthy", "Redis connection OK"
        return "degraded", "Redis not configured (in-memory fallback)"
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        return "unhealthy", f"Redis error: {exc}"


async def check_task_queue_health() -> tuple[str, str]:
    try:
        from ..task_queue import get_task_queue
        q = get_task_queue()
        return "healthy", f"Task queue: {len(q._tasks)} tasks tracked"
    except Exception as exc:
        logger.error("Task queue health check failed: %s", exc)
        return "unhealthy", f"Task queue error: {exc}"


async def asyncio_if_awaitable(value):
    if hasattr(value, "__await__"):
        return await value
    return value


async def comprehensive_health_check() -> HealthStatus:
    checks: dict[str, str] = {}
    overall_healthy = True

    db_status, db_msg = await check_database_health()
    checks["database"] = f"{db_status}: {db_msg}"
    if db_status == "unhealthy":
        overall_healthy = False

    redis_status, redis_msg = await check_redis_health()
    checks["redis"] = f"{redis_status}: {redis_msg}"

    tq_status, tq_msg = await check_task_queue_health()
    checks["task_queue"] = f"{tq_status}: {tq_msg}"
    if tq_status == "unhealthy":
        overall_healthy = False

    return HealthStatus(healthy=overall_healthy, checks=checks)


def record_http_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_ride_processed(status: str = "success") -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    rides_processed_total.labels(status=status).inc()


def record_background_task(kind: str, status: str) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    background_tasks_total.labels(kind=kind, status=status).inc()


def record_cache(hit: bool) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    if hit:
        cache_hits_total.inc()
    else:
        cache_misses_total.inc()


def record_ai_coach_request(status: str = "success") -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    ai_coach_requests_total.labels(status=status).inc()


def record_import(source: str, status: str = "success") -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    import_operations_total.labels(source=source, status=status).inc()


def start_metrics_server() -> None:
    if not PROMETHEUS_AVAILABLE:
        logger.info("Prometheus client not installed, metrics server not started")
        return
    try:
        start_http_server(PROMETHEUS_PORT)
        logger.info("Prometheus metrics server started on port %d", PROMETHEUS_PORT)
    except OSError as exc:
        logger.warning("Could not start Prometheus server: %s", exc)


class MetricsMiddleware:
    """FastAPI middleware for automatic HTTP metrics collection."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time as _time
        start_time = _time.time()
        method = scope.get("method", "unknown")
        path = scope.get("path", "unknown")

        status_code = 500
        async def send_with_metrics(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_with_metrics)
        finally:
            duration = _time.time() - start_time
            if PROMETHEUS_AVAILABLE:
                record_http_request(method, path, status_code, duration)
