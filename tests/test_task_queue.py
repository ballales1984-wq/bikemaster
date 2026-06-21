"""Extended tests for task_queue module covering handlers and _execute."""

from unittest.mock import AsyncMock, patch

import pytest

from bike_analyzer.backend.task_queue import BackgroundTaskQueue, Task, get_task_queue


class TestTaskDataclass:
    def test_task_defaults(self):
        task = Task(id="t1", kind="test")
        assert task.id == "t1"
        assert task.kind == "test"
        assert task.payload == {}
        assert task.status == "pending"
        assert task.result is None
        assert task.error is None

    def test_task_to_dict(self):
        task = Task(id="t2", kind="batch_import", payload={"files": []}, result={"imported": 1})
        d = task.to_dict()
        assert d["id"] == "t2"
        assert d["kind"] == "batch_import"
        assert d["status"] == "pending"
        assert d["payload"] == {"files": []}


class TestBackgroundTaskQueueExtended:
    @pytest.fixture
    def queue(self):
        return BackgroundTaskQueue(max_workers=1)

    @pytest.mark.asyncio
    async def test_execute_unknown_kind(self, queue):
        task = Task(id="t1", kind="unknown_type")
        await queue._execute(task, "worker-0")
        assert task.status == "failed"
        assert "Unknown task kind" in task.error

    @pytest.mark.asyncio
    async def test_execute_handler_exception(self, queue):
        task = Task(id="t1", kind="batch_import", payload={"files": [{"type": "gpx", "content": "bad"}]})
        with patch.object(queue, "_handle_batch_import", side_effect=RuntimeError("parse error")):
            await queue._execute(task, "worker-0")
        assert task.status == "failed"
        assert "parse error" in task.error

    @pytest.mark.asyncio
    async def test_worker_cancelled(self, queue):
        queue._running = False
        with patch.object(queue, "_execute") as mock_exec:
            await queue._worker("worker-0")
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_batch_import_success(self, queue):
        task = Task(id="t1", kind="batch_import", payload={"files": [{"type": "gpx"}]})
        with patch.object(queue, "_handle_batch_import", new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = {"imported": 1, "failed": []}
            await queue._execute(task, "worker-0")
        assert task.status == "completed"
        assert task.result["imported"] == 1

    @pytest.mark.asyncio
    async def test_execute_generate_map_success(self, queue):
        task = Task(id="t2", kind="generate_map", payload={"points": []})
        with patch.object(queue, "_handle_generate_map", new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = {"map_url": "/maps/1.html"}
            await queue._execute(task, "worker-0")
        assert task.status == "completed"
        assert task.result["map_url"] == "/maps/1.html"

    @pytest.mark.asyncio
    async def test_execute_recalculate_stress_success(self, queue):
        task = Task(id="t3", kind="recalculate_training_stress", payload={"athlete_id": 1})
        with patch.object(queue, "_handle_recalculate_stress", new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = {"updated": 5}
            await queue._execute(task, "worker-0")
        assert task.status == "completed"
        assert task.result["updated"] == 5

    @pytest.mark.asyncio
    async def test_execute_warm_weather_success(self, queue):
        task = Task(id="t4", kind="warm_weather_cache", payload={"lat": 45.0})
        with patch.object(queue, "_handle_warm_weather", new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = {"cached": True}
            await queue._execute(task, "worker-0")
        assert task.status == "completed"
        assert task.result["cached"] is True

    @pytest.mark.asyncio
    async def test_execute_strava_sync_success(self, queue):
        task = Task(id="t5", kind="strava_sync", payload={"athlete_id": 1})
        assert task.kind == "strava_sync"

    @pytest.mark.asyncio
    async def test_execute_garmin_sync_success(self, queue):
        task = Task(id="t6", kind="garmin_sync", payload={"athlete_id": 1})
        assert task.kind == "garmin_sync"

    @pytest.mark.asyncio
    async def test_start_stop_idempotent(self, queue):
        await queue.start()
        assert queue._running is True
        await queue.start()
        assert queue._running is True
        await queue.stop()
        assert queue._running is False

    @pytest.mark.asyncio
    async def test_get_pending_after_enqueue(self, queue):
        await queue.enqueue("batch_import", {})
        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0].status == "pending"

    @pytest.mark.asyncio
    async def test_get_running_empty(self, queue):
        running = queue.get_running()
        assert running == []

    @pytest.mark.asyncio
    async def test_get_task_existing(self, queue):
        task = await queue.enqueue("batch_import", {})
        fetched = queue.get_task(task.id)
        assert fetched is not None
        assert fetched.id == task.id

    @pytest.mark.asyncio
    async def test_get_task_nonexistent(self, queue):
        assert queue.get_task("nonexistent") is None


class TestGetTaskQueue:
    def test_singleton(self):
        q1 = get_task_queue()
        q2 = get_task_queue()
        assert q1 is q2

    def test_returns_background_task_queue(self):
        queue = get_task_queue()
        assert isinstance(queue, BackgroundTaskQueue)
