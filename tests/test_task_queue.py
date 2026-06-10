"""Tests for task_queue module."""
import pytest

from bike_analyzer.backend.task_queue import BackgroundTaskQueue, Task, get_task_queue


class TestTask:
    def test_task_creation(self):
        task = Task(id="test-123", kind="batch_import")
        assert task.id == "test-123"
        assert task.kind == "batch_import"
        assert task.status == "pending"
        assert task.result is None
        assert task.error is None

    def test_task_to_dict(self):
        task = Task(id="test-456", kind="generate_map", payload={"ride_id": 1})
        d = task.to_dict()
        assert d["id"] == "test-456"
        assert d["kind"] == "batch_map"
        assert d["status"] == "pending"
        assert d["payload"] == {"ride_id": 1}


class TestBackgroundTaskQueue:
    @pytest.mark.asyncio
    async def test_enqueue_task(self):
        queue = BackgroundTaskQueue(max_workers=1)
        task = await queue.enqueue("batch_import", {"files": []})
        assert task.id is not None
        assert task.kind == "batch_import"
        assert task.status == "pending"

    def test_get_task(self):
        queue = BackgroundTaskQueue(max_workers=1)
        task = queue._tasks.get("nonexistent")
        assert task is None

    def test_get_pending_empty(self):
        queue = BackgroundTaskQueue()
        pending = queue.get_pending()
        assert pending == []

    def test_get_running_empty(self):
        queue = BackgroundTaskQueue()
        running = queue.get_running()
        assert running == []

    @pytest.mark.asyncio
    async def test_start_stop_workers(self):
        queue = BackgroundTaskQueue(max_workers=1)
        await queue.start()
        assert queue._running is True
        await queue.stop()
        assert queue._running is False


class TestGetTaskQueue:
    def test_singleton(self):
        q1 = get_task_queue()
        q2 = get_task_queue()
        assert q1 is q2

    def test_returns_background_task_queue(self):
        queue = get_task_queue()
        assert isinstance(queue, BackgroundTaskQueue)
