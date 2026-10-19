"""Background task queue for heavy operations.

Provides a simple async task queue using asyncio with optional Redis integration.
Used for: batch GPX/FIT import, map generation, AI Coach batch processing,
          weather cache warming, training stress recalculation.

Tasks are executed by a fixed pool of worker coroutines. Each task kind has
a dedicated handler and a configurable timeout. Completed tasks are purged
after a TTL to prevent unbounded memory growth.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


def _ensure_calories(ride_data: dict) -> None:
    """Ensure a ride dict has calories; backfill via physics estimator if missing."""
    if ride_data.get("calories"):
        return
    try:
        from bike_analyzer.backend.analytics.calories import ensure_calories
        from bike_analyzer.backend.models.models import Ride

        allowed = set(Ride.__dataclass_fields__.keys())
        clean = {k: v for k, v in ride_data.items() if k in allowed and k not in ("gps_points", "id")}
        ride_data["calories"] = ensure_calories(Ride(**clean))
    except Exception:
        ride_data["calories"] = 0


@dataclass
class Task:
    """Background task descriptor.

    Attributes:
        id: Unique task identifier (UUID).
        kind: Task type (e.g. ``"batch_import"``, ``"strava_sync"``).
        payload: Arbitrary task parameters.
        created_at: Unix timestamp of creation.
        status: One of: ``"pending"``, ``"running"``, ``"completed"``, ``"failed"``.
        result: Task result (set on completion).
        error: Error message (set on failure).
    """

    id: str
    kind: str
    payload: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
        """Serialize the task to a JSON-compatible dict."""
        return {
            "id": self.id,
            "kind": self.kind,
            "payload": self.payload,
            "status": self.status,
            "created_at": self.created_at,
            "result": self.result,
            "error": self.error,
        }


class BackgroundTaskQueue:
    """Async task queue with a fixed worker pool.

    Workers consume tasks from an internal asyncio.Queue, execute the
    appropriate handler for the task kind, and record results. Completed
    tasks are automatically purged after ``_TASK_TTL`` seconds.
    """

    def __init__(self, max_workers: int = 2):
        """Initialize the queue with a fixed number of worker coroutines.

        Args:
            max_workers: Maximum concurrent task workers.
        """
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: dict[str, Task] = {}
        self._workers: list[asyncio.Task] = []
        self._max_workers = max_workers
        self._running = False
        self._TASK_TTL = 300.0
        self._completed_at: dict[str, float] = {}
        self._lock = asyncio.Lock()
        # Per-task-kind timeouts (seconds). Falls back to 300s for unknown kinds.
        self._TASK_TIMEOUTS = {
            "batch_import": 600.0,
            "generate_map": 120.0,
            "recalculate_training_stress": 300.0,
            "warm_weather_cache": 180.0,
            "strava_sync": 300.0,
            "garmin_sync": 300.0,
            "wahoo_sync": 300.0,
        }

    async def start(self) -> None:
        """Start the worker pool. No-op if already running."""
        if self._running:
            return
        self._running = True
        for i in range(self._max_workers):
            t = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(t)
        logger.info("Background task queue started with %d workers", self._max_workers)

    async def stop(self) -> None:
        """Stop the worker pool and cancel all pending tasks."""
        self._running = False
        for w in self._workers:
            w.cancel()
        self._workers.clear()
        logger.info("Background task queue stopped")

    async def _worker(self, name: str) -> None:
        """Worker coroutine: consumes tasks from the queue until stopped.

        Each iteration blocks on ``queue.get()`` with a 1s timeout so the
        worker can check ``self._running`` periodically.
        """
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                logger.debug("[%s] processing task %s", name, task.id)
                task.status = "running"
                self._tasks[task.id] = task
                await self._execute(task, name)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[%s] unexpected error: %s", name, exc)

    async def _execute(self, task: Task, worker_name: str) -> None:
        """Dispatch a task to its kind-specific handler with timeout enforcement.

        Args:
            task: The task to execute.
            worker_name: Worker identifier for logging.
        """
        try:
            task_id = task.id
            kind = task.kind
            payload = task.payload
            timeout = self._TASK_TIMEOUTS.get(kind, 300.0)

            if kind == "batch_import":
                result = await asyncio.wait_for(
                    self._handle_batch_import(payload), timeout=timeout
                )
            elif kind == "generate_map":
                result = await asyncio.wait_for(
                    self._handle_generate_map(payload), timeout=timeout
                )
            elif kind == "recalculate_training_stress":
                result = await asyncio.wait_for(
                    self._handle_recalculate_stress(payload), timeout=timeout
                )
            elif kind == "warm_weather_cache":
                result = await asyncio.wait_for(
                    self._handle_warm_weather(payload), timeout=timeout
                )
            elif kind == "strava_sync":
                result = await asyncio.wait_for(
                    self._handle_strava_sync(payload), timeout=timeout
                )
            elif kind == "garmin_sync":
                result = await asyncio.wait_for(
                    self._handle_garmin_sync(payload), timeout=timeout
                )
            elif kind == "wahoo_sync":
                result = await asyncio.wait_for(
                    self._handle_wahoo_sync(payload), timeout=timeout
                )
            else:
                raise ValueError(f"Unknown task kind: {kind}")

            task.status = "completed"
            task.result = result
            async with self._lock:
                self._completed_at[task_id] = time.time()
            logger.info("[%s] task %s completed", worker_name, task_id)
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            async with self._lock:
                self._completed_at[task.id] = time.time()
            logger.error("[%s] task %s failed: %s", worker_name, task.id, exc)

    def _purge_expired(self) -> None:
        """Remove completed tasks older than ``_TASK_TTL`` from memory."""
        now = time.time()
        expired = [
            tid for tid, ts in self._completed_at.items()
            if now - ts > self._TASK_TTL
        ]
        for tid in expired:
            self._tasks.pop(tid, None)
            self._completed_at.pop(tid, None)

    async def enqueue(self, kind: str, payload: dict | None = None) -> Task:
        """Add a new task to the queue.

        Args:
            kind: Task type identifier.
            payload: Task-specific parameters.

        Returns:
            The created Task object.
        """
        import uuid

        async with self._lock:
            self._purge_expired()
            task = Task(id=str(uuid.uuid4()), kind=kind, payload=payload or {})
            self._tasks[task.id] = task
        await self._queue.put(task)
        logger.debug("Enqueued task %s (%s)", task.id, kind)
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Retrieve a task by id, purging expired entries first."""
        self._purge_expired()
        return self._tasks.get(task_id)

    def get_pending(self) -> list[Task]:
        """Return all pending (not yet started) tasks."""
        self._purge_expired()
        return [t for t in self._tasks.values() if t.status == "pending"]

    def get_running(self) -> list[Task]:
        """Return all currently running tasks."""
        self._purge_expired()
        return [t for t in self._tasks.values() if t.status == "running"]

    async def _handle_batch_import(self, payload: dict) -> dict:
        """Import multiple GPX/FIT files in batch.

        Args:
            payload: Dict with ``files`` list and ``athlete_id``/``tenant_id``.

        Returns:
            Dict with ``imported`` and ``failed`` lists.
        """
        from bike_analyzer.backend.services.import_service import ImportService

        results = {"imported": [], "failed": []}
        files = payload.get("files", [])
        athlete_id = payload.get("athlete_id")
        tenant_id = payload.get("tenant_id", athlete_id)
        for f in files:
            try:
                if f["type"] == "gpx":
                    ride_data = ImportService.import_file(
                        "gpx",
                        content=f["content"],
                        name=f["name"],
                        athlete_id=athlete_id,
                        tenant_id=tenant_id,
                    )
                else:
                    ride_data = ImportService.import_file(
                        "fit",
                        file_path=f["path"],
                        name=f["name"],
                        athlete_id=athlete_id,
                        tenant_id=tenant_id,
                    )
                results["imported"].append(ride_data)
            except Exception as exc:
                results["failed"].append({"name": f.get("name"), "error": str(exc)})
        return results

    async def _handle_generate_map(self, payload: dict) -> dict:
        """Generate an HTML map for a ride.

        Args:
            payload: Dict with ``points`` (GPS list) and ``ride_id``.

        Returns:
            Dict with ``map_url`` or ``error``.
        """
        from pathlib import Path

        from bike_analyzer.backend.maps.map_renderer import create_route_map
        from bike_analyzer.backend.models.models import GPSPoint

        try:
            points = [GPSPoint(**p) for p in payload["points"]]
            ride_id = str(payload["ride_id"])
            safe_id = "".join(c if c.isalnum() or c == "_" else "_" for c in ride_id)
            base_dir = Path(__file__).resolve().parent.parent / "static"
            path = base_dir / f"ride_{safe_id}_map.html"
            resolved = path.resolve()
            if not resolved.is_relative_to(base_dir.resolve()):
                return {"error": "Invalid path"}
            create_route_map(points, output_path=str(resolved))
            return {"map_url": f"/static/{resolved.name}"}
        except Exception as exc:
            return {"error": str(exc)}

    async def _handle_recalculate_stress(self, payload: dict) -> dict:
        """Recalculate training stress (TSS/ATL/CTL/TSB) for an athlete.

        Args:
            payload: Dict with ``athlete_id`` and optional ``ftp``.

        Returns:
            Dict with ``updated`` count or ``error``.
        """
        from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
        from bike_analyzer.backend.analytics.training_load import (
            recalculate_training_stress_for_athlete,
        )

        athlete_id = payload.get("athlete_id")
        ftp = payload.get("ftp", 250.0)
        rides = RideRepository.get_rides_by_athlete(athlete_id)
        if not rides:
            return {"updated": 0}
        recalculate_training_stress_for_athlete(athlete_id, ftp=ftp)
        return {"updated": len(rides)}

    async def _handle_warm_weather(self, payload: dict) -> dict:
        """Warm the weather cache for a list of dates.

        Args:
            payload: Dict with ``lat``, ``lon``, and ``dates`` list.

        Returns:
            Dict with ``cached_days`` count.
        """
        from bike_analyzer.backend.weather.weather_service import get_forecast_for_date

        lat = payload.get("lat")
        lon = payload.get("lon")
        dates = payload.get("dates", [])
        cached = 0
        for d in dates:
            try:
                data = get_forecast_for_date(lat, lon, d)
                if "error" not in data:
                    from bike_analyzer.backend.db.database import save_weather_cache

                    save_weather_cache(lat, lon, d, data)
                    cached += 1
            except Exception:
                logger.debug("Weather cache save failed", exc_info=True)
                pass
        return {"cached_days": cached}

    async def _handle_strava_sync(self, payload: dict) -> dict:
        """Sync new activities from Strava for an athlete.

        Handles rate-limited stream fetching by falling back to basic activity data.

        Args:
            payload: Dict with ``athlete_id`` and optional ``tenant_id``.

        Returns:
            Dict with ``imported`` count, ``total_fetched``, or ``error``.
        """
        import time

        from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
        from bike_analyzer.backend.ingestion.strava_client import (
            StravaRateLimitError,
            fetch_all_activities,
            get_last_sync_ts,
            get_valid_token,
            set_last_sync_ts,
            strava_to_ride,
            strava_to_ride_with_streams,
        )

        athlete_id = payload["athlete_id"]
        tenant_id = payload.get("tenant_id", athlete_id)
        access_token = await get_valid_token(athlete_id)
        if not access_token:
            return {"imported": 0, "error": "no_valid_token"}
        last_sync = get_last_sync_ts(athlete_id)
        sync_ts = int(time.time())
        activities = await fetch_all_activities(access_token, after=last_sync)
        imported = []
        imported_ids: set[int] = set()
        streams_rate_limited = False
        for act in activities:
            if streams_rate_limited:
                ride_data = strava_to_ride(act)
            else:
                try:
                    ride_data = await strava_to_ride_with_streams(act, access_token)
                except StravaRateLimitError:
                    streams_rate_limited = True
                    ride_data = strava_to_ride(act)
            if ride_data.get("skipped") or "error" in ride_data:
                continue
            ride_data["athlete_id"] = athlete_id
            ride_data["tenant_id"] = tenant_id
            db_ride = {k: v for k, v in ride_data.items() if k != "id"}
            _ensure_calories(db_ride)
            ride_id = RideRepository.save_ride(db_ride)
            if ride_id not in imported_ids:
                imported.append({"id": int(ride_id), **ride_data})
                imported_ids.add(int(ride_id))
        set_last_sync_ts(athlete_id, sync_ts)
        return {"imported": len(imported), "total_fetched": len(activities)}

    async def _handle_garmin_sync(self, payload: dict) -> dict:
        """Sync new activities from Garmin for an athlete.

        Args:
            payload: Dict with ``athlete_id`` and optional ``tenant_id``.

        Returns:
            Dict with ``imported`` count and ``total_fetched``.
        """
        from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
        from bike_analyzer.backend.ingestion.garmin_client import (
            fetch_activities,
            garmin_to_ride,
            get_valid_token,
        )

        athlete_id = payload["athlete_id"]
        tenant_id = payload.get("tenant_id", athlete_id)
        access_token = await get_valid_token(athlete_id)
        if not access_token:
            return {"imported": 0, "error": "no_valid_token"}
        activities = await fetch_activities(access_token)
        imported = []
        imported_ids: set[int] = set()
        for act in activities:
            ride_data = garmin_to_ride(act)
            if ride_data.get("skipped") or "error" in ride_data:
                continue
            ride_data["athlete_id"] = athlete_id
            ride_data["tenant_id"] = tenant_id
            db_ride = {k: v for k, v in ride_data.items() if k != "id"}
            _ensure_calories(db_ride)
            ride_id = RideRepository.save_ride(db_ride)
            if ride_id not in imported_ids:
                imported.append({"id": int(ride_id), **ride_data})
                imported_ids.add(int(ride_id))
        return {"imported": len(imported), "total_fetched": len(activities)}

    async def _handle_wahoo_sync(self, payload: dict) -> dict:
        """Sync new workouts from Wahoo for an athlete.

        Args:
            payload: Dict with ``athlete_id`` and optional ``tenant_id``.

        Returns:
            Dict with ``imported`` count and ``total_fetched``.
        """
        from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
        from bike_analyzer.backend.ingestion.wahoo_client import (
            fetch_workouts,
            get_valid_token,
            wahoo_to_ride,
        )

        athlete_id = payload["athlete_id"]
        tenant_id = payload.get("tenant_id", athlete_id)
        access_token = get_valid_token(athlete_id)
        if not access_token:
            return {"imported": 0, "error": "no_valid_token"}
        workouts = fetch_workouts(access_token)
        imported = []
        imported_ids: set[int] = set()
        for workout in workouts:
            ride_data = wahoo_to_ride(workout)
            if ride_data.get("skipped") or "error" in ride_data:
                continue
            ride_data["athlete_id"] = athlete_id
            ride_data["tenant_id"] = tenant_id
            db_ride = {k: v for k, v in ride_data.items() if k != "id"}
            _ensure_calories(db_ride)
            ride_id = RideRepository.save_ride(db_ride)
            if ride_id not in imported_ids:
                imported.append({"id": int(ride_id), **ride_data})
                imported_ids.add(int(ride_id))
        return {"imported": len(imported), "total_fetched": len(workouts)}


_task_queue: BackgroundTaskQueue | None = None


def get_task_queue() -> BackgroundTaskQueue:
    """Return the singleton task queue instance, creating it if needed."""
    global _task_queue
    if _task_queue is None:
        _task_queue = BackgroundTaskQueue(max_workers=2)
    return _task_queue


__all__ = ["BackgroundTaskQueue", "Task", "get_task_queue"]
