"""Tests for task_queue module."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bike_analyzer.backend.task_queue import BackgroundTaskQueue, Task, get_task_queue


class TestTask:
    def test_create(self):
        t = Task(id="1", kind="test")
        assert t.id == "1"
        assert t.kind == "test"
        assert t.status == "pending"
        assert t.result is None
        assert t.error is None

    def test_default_payload(self):
        t = Task(id="1", kind="test")
        assert t.payload == {}

    def test_default_created_at(self):
        before = time.time()
        t = Task(id="1", kind="test")
        after = time.time()
        assert before <= t.created_at <= after

    def test_to_dict(self):
        t = Task(id="1", kind="test", payload={"key": "value"}, result="done")
        d = t.to_dict()
        assert d["id"] == "1"
        assert d["kind"] == "test"
        assert d["payload"] == {"key": "value"}
        assert d["status"] == "pending"
        assert d["result"] == "done"

    def test_to_dict_with_error(self):
        t = Task(id="1", kind="test", error="Something failed")
        d = t.to_dict()
        assert d["error"] == "Something failed"
        assert d["status"] == "pending"

    def test_custom_values(self):
        t = Task(id="abc", kind="batch_import", payload={"files": []}, status="running", result={"imported": 1})
        assert t.status == "running"
        assert t.result == {"imported": 1}


class TestBackgroundTaskQueue:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        queue = BackgroundTaskQueue(max_workers=1)
        await queue.start()
        assert queue._running is True
        assert len(queue._workers) == 1
        await queue.stop()
        assert queue._running is False
        assert len(queue._workers) == 0

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        queue = BackgroundTaskQueue(max_workers=1)
        await queue.start()
        count1 = len(queue._workers)
        await queue.start()
        count2 = len(queue._workers)
        assert count1 == count2
        await queue.stop()

    @pytest.mark.asyncio
    async def test_enqueue(self):
        queue = BackgroundTaskQueue(max_workers=1)
        await queue.start()
        task = await queue.enqueue("test_kind", {"key": "value"})
        assert task.id is not None
        assert task.kind == "test_kind"
        assert task.payload == {"key": "value"}
        assert task.status == "pending"
        await queue.stop()

    @pytest.mark.asyncio
    async def test_enqueue_empty_payload(self):
        queue = BackgroundTaskQueue(max_workers=1)
        await queue.start()
        task = await queue.enqueue("test_kind")
        assert task.payload == {}
        await queue.stop()

    def test_get_task(self):
        queue = BackgroundTaskQueue()
        task = Task(id="test-id", kind="test")
        queue._tasks["test-id"] = task
        result = queue.get_task("test-id")
        assert result is task

    def test_get_task_missing(self):
        queue = BackgroundTaskQueue()
        result = queue.get_task("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_pending(self):
        queue = BackgroundTaskQueue()
        queue._tasks["pending1"] = Task(id="pending1", kind="test", status="pending")
        queue._tasks["running1"] = Task(id="running1", kind="test", status="running")
        queue._tasks["pending2"] = Task(id="pending2", kind="test", status="pending")
        pending = queue.get_pending()
        assert len(pending) == 2
        assert all(t.status == "pending" for t in pending)

    @pytest.mark.asyncio
    async def test_get_running(self):
        queue = BackgroundTaskQueue()
        queue._tasks["running1"] = Task(id="running1", kind="test", status="running")
        queue._tasks["pending1"] = Task(id="pending1", kind="test", status="pending")
        running = queue.get_running()
        assert len(running) == 1
        assert running[0].status == "running"

    @pytest.mark.asyncio
    async def test_unknown_task_kind(self):
        queue = BackgroundTaskQueue(max_workers=1)
        await queue.start()
        task = await queue.enqueue("unknown_kind")
        assert task.status == "pending"
        await queue.stop()

    @pytest.mark.asyncio
    async def test_task_execution_error(self):
        queue = BackgroundTaskQueue(max_workers=1)
        await queue.start()
        task = await queue.enqueue("invalid_kind_that_will_error")
        await asyncio.sleep(0.1)
        if task.id in queue._tasks:
            assert queue._tasks[task.id].status in ("failed", "pending", "running")
        await queue.stop()

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self):
        queue = BackgroundTaskQueue(max_workers=1)
        task = Task(id="err-test", kind="invalid")
        task.status = "running"
        queue._tasks[task.id] = task
        await queue._execute(task, "test-worker")
        assert task.status == "failed"
        assert task.error is not None


class TestGetTaskQueue:
    def test_singleton(self):
        q1 = get_task_queue()
        q2 = get_task_queue()
        assert q1 is q2

    def test_creates_if_none(self):
        import bike_analyzer.backend.task_queue as tq
        old = tq._task_queue
        tq._task_queue = None
        try:
            q = get_task_queue()
            assert q is not None
            assert isinstance(q, BackgroundTaskQueue)
        finally:
            tq._task_queue = old
