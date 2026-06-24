"""Tests for BackgroundTaskQueue coverage gaps."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bike_analyzer.backend.task_queue import (
    BackgroundTaskQueue,
    Task,
)


class TestTask:
    def test_task_creation(self):
        t = Task(id="1", kind="import", payload={"file": "test.gpx"})
        assert t.id == "1"
        assert t.kind == "import"
        assert t.status == "pending"
        assert t.error is None

    def test_task_to_dict(self):
        t = Task(id="1", kind="import", payload={"file": "test.gpx"}, status="completed")
        d = t.to_dict()
        assert d["id"] == "1"
        assert d["kind"] == "import"
        assert d["status"] == "completed"


class TestBackgroundTaskQueue:
    def test_constructor_defaults(self):
        q = BackgroundTaskQueue()
        assert q._max_workers == 2
        assert q._running is False

    def test_constructor_custom_workers(self):
        q = BackgroundTaskQueue(max_workers=4)
        assert q._max_workers == 4

    @pytest.mark.asyncio
    async def test_start_stop(self):
        q = BackgroundTaskQueue(max_workers=1)
        assert not q._running
        await q.start()
        assert q._running
        assert len(q._workers) == 1
        await q.stop()
        assert not q._running

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        q = BackgroundTaskQueue(max_workers=1)
        await q.start()
        await q.start()
        assert len(q._workers) == 1
        await q.stop()

    @pytest.mark.asyncio
    async def test_enqueue_task(self):
        q = BackgroundTaskQueue(max_workers=1)
        await q.start()
        task = await q.enqueue("batch_import", {"files": []})
        assert isinstance(task.id, str)
        assert task.kind == "batch_import"
        assert task.id in q._tasks
        await q.stop()

    def test_get_task_found(self):
        q = BackgroundTaskQueue()
        t = Task(id="task1", kind="test")
        q._tasks["task1"] = t
        result = q.get_task("task1")
        assert result is t

    def test_get_task_not_found(self):
        q = BackgroundTaskQueue()
        result = q.get_task("nonexistent")
        assert result is None

    def test_get_pending_empty(self):
        q = BackgroundTaskQueue()
        assert q.get_pending() == []

    def test_get_running_empty(self):
        q = BackgroundTaskQueue()
        assert q.get_running() == []

    def test_get_pending_with_tasks(self):
        q = BackgroundTaskQueue()
        q._tasks["t1"] = Task(id="t1", kind="test", status="pending")
        q._tasks["t2"] = Task(id="t2", kind="test", status="running")
        pending = q.get_pending()
        assert len(pending) == 1
        assert pending[0].id == "t1"

    def test_get_running_with_tasks(self):
        q = BackgroundTaskQueue()
        q._tasks["t1"] = Task(id="t1", kind="test", status="running")
        running = q.get_running()
        assert len(running) == 1
        assert running[0].id == "t1"

    @pytest.mark.asyncio
    async def test_worker_processes_batch_import(self):
        q = BackgroundTaskQueue(max_workers=1)
        await q.start()
        await q.enqueue("batch_import", {"files": []})
        await asyncio.sleep(0.3)
        await q.stop()

    @pytest.mark.asyncio
    async def test_worker_handles_unknown_kind(self):
        q = BackgroundTaskQueue(max_workers=1)
        await q.start()
        task = await q.enqueue("unknown_kind", {})
        await asyncio.sleep(0.3)
        assert q._tasks[task.id].status == "failed"
        await q.stop()

    @pytest.mark.asyncio
    async def test_worker_handles_failing_handler(self):
        q = BackgroundTaskQueue(max_workers=1)
        await q.start()
        await q.enqueue(
            "generate_map",
            {
                "points": [
                    {
                        "lat": 45.0,
                        "lon": 9.0,
                        "altitude": 100,
                        "speed": 10,
                        "timestamp": "2024-06-15T10:00:00Z",
                    }
                ],
                "ride_id": "1",
            },
        )
        await asyncio.sleep(0.3)
        await q.stop()
