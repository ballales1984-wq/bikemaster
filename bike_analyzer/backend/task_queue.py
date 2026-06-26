"""Background task queue for heavy operations.

Provides a simple async task queue using asyncio with optional Redis integration.
Used for: batch GPX/FIT import, map generation, AI Coach batch processing,
          weather cache warming, training stress recalculation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Task:
    id: str
    kind: str
    payload: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
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
    def __init__(self, max_workers: int = 2):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: dict[str, Task] = {}
        self._workers: list[asyncio.Task] = []
        self._max_workers = max_workers
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        for i in range(self._max_workers):
            t = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(t)
        logger.info("Background task queue started with %d workers", self._max_workers)

    async def stop(self):
        self._running = False
        for w in self._workers:
            w.cancel()
        self._workers.clear()
        logger.info("Background task queue stopped")

    async def _worker(self, name: str):
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

    async def _execute(self, task: Task, worker_name: str):
        try:
            task_id = task.id
            kind = task.kind
            payload = task.payload

            if kind == "batch_import":
                result = await self._handle_batch_import(payload)
            elif kind == "generate_map":
                result = await self._handle_generate_map(payload)
            elif kind == "recalculate_training_stress":
                result = await self._handle_recalculate_stress(payload)
            elif kind == "warm_weather_cache":
                result = await self._handle_warm_weather(payload)
            elif kind == "strava_sync":
                result = await self._handle_strava_sync(payload)
            elif kind == "garmin_sync":
                result = await self._handle_garmin_sync(payload)
            else:
                raise ValueError(f"Unknown task kind: {kind}")

            task.status = "completed"
            task.result = result
            logger.info("[%s] task %s completed", worker_name, task_id)
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            logger.error("[%s] task %s failed: %s", worker_name, task.id, exc)

    async def enqueue(self, kind: str, payload: dict | None = None) -> Task:
        import uuid

        task = Task(id=str(uuid.uuid4()), kind=kind, payload=payload or {})
        self._tasks[task.id] = task
        await self._queue.put(task)
        logger.debug("Enqueued task %s (%s)", task.id, kind)
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def get_pending(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == "pending"]

    def get_running(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == "running"]

    async def _handle_batch_import(self, payload: dict) -> dict:
        from bike_analyzer.backend.db.database import save_ride
        from bike_analyzer.backend.ingestion.gps_parser import (
            parse_fit_file,
            parse_gpx_file,
            points_to_ride,
        )

        results = {"imported": [], "failed": []}
        files = payload.get("files", [])
        athlete_id = payload.get("athlete_id")
        tenant_id = payload.get("tenant_id", athlete_id)
        for f in files:
            try:
                pts = (
                    parse_gpx_file(f["content"])
                    if f["type"] == "gpx"
                    else parse_fit_file(f["path"])
                )
                ride_data = points_to_ride(pts, name=f["name"])
                if "error" not in ride_data:
                    ride_data["athlete_id"] = athlete_id
                    ride_data["tenant_id"] = tenant_id
                    ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
                    ride_data["id"] = int(ride_id)
                    results["imported"].append(ride_data)
            except Exception as exc:
                results["failed"].append({"name": f.get("name"), "error": str(exc)})
        return results

    async def _handle_generate_map(self, payload: dict) -> dict:
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
        from bike_analyzer.backend.db.database import (
            get_rides_by_athlete,
            recalculate_training_stress_for_athlete,
        )

        athlete_id = payload.get("athlete_id")
        ftp = payload.get("ftp", 250.0)
        rides = get_rides_by_athlete(athlete_id)
        if not rides:
            return {"updated": 0}
        recalculate_training_stress_for_athlete(athlete_id, ftp=ftp)
        return {"updated": len(rides)}

    async def _handle_warm_weather(self, payload: dict) -> dict:
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
                pass
        return {"cached_days": cached}

    async def _handle_strava_sync(self, payload: dict) -> dict:
        from bike_analyzer.backend.db.database import save_ride
        from bike_analyzer.backend.ingestion.strava_client import (
            fetch_all_activities,
            get_valid_token,
            strava_to_ride,
        )

        athlete_id = payload["athlete_id"]
        tenant_id = payload.get("tenant_id", athlete_id)
        access_token = get_valid_token(athlete_id)
        if not access_token:
            return {"imported": 0, "error": "no_valid_token"}
        activities = fetch_all_activities(access_token)
        imported = []
        imported_ids: set[int] = set()
        for act in activities:
            ride_data = strava_to_ride(act)
            if ride_data.get("skipped") or "error" in ride_data:
                continue
            ride_data["athlete_id"] = athlete_id
            ride_data["tenant_id"] = tenant_id
            db_ride = {k: v for k, v in ride_data.items() if k != "id"}
            ride_id = save_ride(db_ride)
            if ride_id not in imported_ids:
                imported.append({"id": int(ride_id), **ride_data})
                imported_ids.add(int(ride_id))
        return {"imported": len(imported), "total_fetched": len(activities)}

    async def _handle_garmin_sync(self, payload: dict) -> dict:
        from bike_analyzer.backend.db.database import save_ride
        from bike_analyzer.backend.ingestion.garmin_client import (
            fetch_activities,
            garmin_to_ride,
            get_valid_token,
        )

        athlete_id = payload["athlete_id"]
        tenant_id = payload.get("tenant_id", athlete_id)
        access_token = get_valid_token(athlete_id)
        if not access_token:
            return {"imported": 0, "error": "no_valid_token"}
        activities = fetch_activities(access_token)
        imported = []
        imported_ids: set[int] = set()
        for act in activities:
            ride_data = garmin_to_ride(act)
            if ride_data.get("skipped") or "error" in ride_data:
                continue
            ride_data["athlete_id"] = athlete_id
            ride_data["tenant_id"] = tenant_id
            db_ride = {k: v for k, v in ride_data.items() if k != "id"}
            ride_id = save_ride(db_ride)
            if ride_id not in imported_ids:
                imported.append({"id": int(ride_id), **ride_data})
                imported_ids.add(int(ride_id))
        return {"imported": len(imported), "total_fetched": len(activities)}


_task_queue: BackgroundTaskQueue | None = None


def get_task_queue() -> BackgroundTaskQueue:
    global _task_queue
    if _task_queue is None:
        _task_queue = BackgroundTaskQueue(max_workers=2)
    return _task_queue


__all__ = ["BackgroundTaskQueue", "Task", "get_task_queue"]
