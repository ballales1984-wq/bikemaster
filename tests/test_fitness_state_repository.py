"""Tests for fitness state repository."""
import json

import pytest
from unittest.mock import AsyncMock, patch

from bike_analyzer.backend.analytics.repositories.fitness_state_repository import (
    FitnessStateRepository,
)


def test_repo_init():
    repo = FitnessStateRepository()
    assert repo._session_factory is None
    assert repo._sync_conn is None


@pytest.mark.asyncio
async def test_save_requires_session():
    repo = FitnessStateRepository()
    with pytest.raises(RuntimeError, match="Async session factory required"):
        await repo.save({"athlete_id": 1})


@pytest.mark.asyncio
async def test_save_success():
    repo = FitnessStateRepository(session_factory=object())
    with patch.object(repo, "_save_async", new_callable=AsyncMock, return_value=42) as mock_save:
        result = await repo.save({"athlete_id": 1})
    assert result == 42
    mock_save.assert_called_once_with({"athlete_id": 1})


@pytest.mark.asyncio
async def test_get_latest_no_session():
    repo = FitnessStateRepository()
    result = await repo.get_latest(1)
    assert result is None


@pytest.mark.asyncio
async def test_get_latest_success():
    repo = FitnessStateRepository(session_factory=object())
    sample = {
        "athlete_id": 1,
        "date": "2024-06-15",
        "fitness": 70.0,
        "risk_indicators": ["high_tsb"],
    }
    with patch.object(repo, "_get_latest_async", new_callable=AsyncMock, return_value=sample) as mock_get:
        result = await repo.get_latest(1)
    assert result == sample
    mock_get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_history_no_session():
    repo = FitnessStateRepository()
    result = await repo.get_history(1)
    assert result == []


@pytest.mark.asyncio
async def test_get_history_success():
    repo = FitnessStateRepository(session_factory=object())
    history = [
        {"date": "2024-06-15", "fitness": 70.0},
        {"date": "2024-06-14", "fitness": 68.0},
    ]
    with patch.object(repo, "_get_history_async", new_callable=AsyncMock, return_value=history) as mock_hist:
        result = await repo.get_history(1, days=7)
    assert result == history
    mock_hist.assert_called_once_with(1, 7)


@pytest.mark.asyncio
async def test_save_async_persists_fields():
    repo = FitnessStateRepository(session_factory=object())
    # Call the internal method directly via patch on class
    captured = {}

    async def fake_save_async(self, state):
        captured["state"] = state
        return 99

    with patch.object(FitnessStateRepository, "_save_async", fake_save_async):
        result = await repo.save({"athlete_id": 2, "fitness": 80.0})
    assert result == 99
    assert captured["state"]["athlete_id"] == 2


@pytest.mark.asyncio
async def test_get_history_async_returns_list():
    repo = FitnessStateRepository(session_factory=object())
    captured = {}

    async def fake_get_history(self, athlete_id, days=30):
        captured["days"] = days
        return [{"date": "2024-06-15"}]

    with patch.object(FitnessStateRepository, "_get_history_async", fake_get_history):
        result = await repo.get_history(1)
    assert result == [{"date": "2024-06-15"}]
    assert captured["days"] == 30
