"""Tests for BackgroundTaskQueue and task_queue module."""

import asyncio

import pytest

from bike_analyzer.backend.task_queue import (
    BackgroundTaskQueue,
    Task,
    get_task_queue,
)


class TestTask:
    def test_create_task_defaults(self):
        t = Task(id="1", kind="test", payload={"key": "val"})
        assert t.id == "1"
        assert t.kind == "test"
        assert t.payload == {"key": "val"}
        assert t.status == "pending"
        assert t.result is None
        assert t.error is None

    def test_to_dict(self):
        t = Task(id="t1", kind="import", payload={"a": 1}, status="completed", result={"ok": True}, error=None)
        d = t.to_dict()
        assert d["id"] == "t1"
        assert d["kind"] == "import"
        assert d["payload"] == {"a": 1}
        assert d["status"] == "completed"
        assert d["result"] == {"ok": True}
        assert d["error"] is None


class TestBackgroundTaskQueue:
    @pytest.mark.asyncio
    async def test_init(self):
        q = BackgroundTaskQueue(max_workers=3)
        assert q._max_workers == 3
        assert q._tasks == {}
        assert q._workers == []
        assert q._running is False

    @pytest.mark.asyncio
    async def test_start(self):
        q = BackgroundTaskQueue(max_workers=1)
        await q.start()
        assert q._running is True
        assert len(q._workers) == 1
        await q.stop()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        q = BackgroundTaskQueue(max_workers=1)
        await q.start()
        await q.start()  # should not double workers
        assert len(q._workers) == 1
        await q.stop()

    @pytest.mark.asyncio
    async def test_stop(self):
        q = BackgroundTaskQueue(max_workers=1)
        await q.start()
        assert q._running is True
        await q.stop()
        assert q._running is False
        assert q._workers == []

    @pytest.mark.asyncio
    async def test_enqueue(self):
        q = BackgroundTaskQueue(max_workers=1)
        task = await q.enqueue("test", {"data": 1})
        assert task.id is not None
        assert task.kind == "test"
        assert task.status == "pending"
        assert task.payload == {"data": 1}
        assert task.id in q._tasks

    @pytest.mark.asyncio
    async def test_enqueue_no_payload(self):
        q = BackgroundTaskQueue(max_workers=1)
        task = await q.enqueue("test")
        assert task.payload == {}

    @pytest.mark.asyncio
    async def test_get_task_found(self):
        q = BackgroundTaskQueue(max_workers=1)
        task = await q.enqueue("test")
        found = q.get_task(task.id)
        assert found is task

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        q = BackgroundTaskQueue(max_workers=1)
        assert q.get_task("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_pending(self):
        q = BackgroundTaskQueue(max_workers=1)
        t1 = await q.enqueue("test", {"name": "t1"})
        t2 = await q.enqueue("test", {"name": "t2"})
        pending = q.get_pending()
        assert len(pending) == 2
        assert t1 in pending
        assert t2 in pending

    @pytest.mark.asyncio
    async def test_get_running(self):
        q = BackgroundTaskQueue(max_workers=1)
        t1 = await q.enqueue("test")
        t1.status = "running"
        running = q.get_running()
        assert len(running) == 1
        assert running[0] is t1

    @pytest.mark.asyncio
    async def test_execute_raises_task_failed(self):
        q = BackgroundTaskQueue(max_workers=1)
        task = Task(id="bad", kind="unknown_kind", payload={})

        await q._execute(task, "worker-0")
        assert task.status == "failed"
        assert "Unknown task kind" in (task.error or "")

    @pytest.mark.asyncio
    async def test_worker_timeout_and_continue(self):
        q = BackgroundTaskQueue(max_workers=1)
        # No tasks enqueued, worker should timeout and continue
        await q.start()
        await asyncio.sleep(0.2)  # let timeout occur
        await q.stop()
        assert q._running is False


class TestGetTaskQueue:
    def test_returns_same_instance(self):
        q1 = get_task_queue()
        q2 = get_task_queue()
        assert q1 is q2

    def test_max_workers_default(self):
        q = get_task_queue()
        assert q._max_workers == 2
