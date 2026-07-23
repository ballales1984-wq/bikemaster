"""Tests for backend.sync.client to improve coverage."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from bike_analyzer.backend.sync.client import SyncClient, SyncClientError


@pytest.fixture()
def client():
    return SyncClient("http://sync.example.com", auth_token="tok123", timeout=5.0)


def test_build_headers_without_auth():
    c = SyncClient("http://example.com")
    assert c._headers == {"Accept": "application/json"}


def test_build_headers_with_auth():
    c = SyncClient("http://example.com", auth_token="abc")
    assert c._headers["Authorization"] == "Bearer abc"
    assert c._headers["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_check_success(client):
    data = {
        "last_sync_ts": "2025-01-01T00:00:00+00:00",
        "server_changes_count": 2,
        "server_changes": [{"id": 1}, {"id": 2}],
        "server_version": "1.0",
    }
    mock = AsyncMock(return_value=data)
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.check()
    assert result.last_sync_ts == "2025-01-01T00:00:00+00:00"
    assert result.server_changes_count == 2
    assert len(result.server_changes) == 2


@pytest.mark.asyncio
async def test_check_success_without_last_sync_ts(client):
    data = {
        "last_sync_ts": "2025-01-01T00:00:00+00:00",
        "server_changes_count": 0,
        "server_changes": [],
        "server_version": "1.0",
    }
    mock = AsyncMock(return_value=data)
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.check(last_sync_ts="2024-12-01T00:00:00+00:00")
    assert result.server_changes_count == 0
    mock.assert_called_once()
    call_kwargs = mock.call_args[1]
    assert call_kwargs["params"] == {"since": "2024-12-01T00:00:00+00:00"}


@pytest.mark.asyncio
async def test_check_error_returns_error_dict(client):
    mock = AsyncMock(side_effect=RuntimeError("network down"))
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.check()
    assert result["error"] == "network down"


@pytest.mark.asyncio
async def test_push_success_without_conflicts(client):
    from bike_analyzer.backend.sync.models import ChangeDelta
    deltas = [ChangeDelta(entity_type="ride", entity_id=1, operation="update", data={"km": 10})]
    data = {
        "accepted": 1,
        "conflicts": [],
        "errors": [],
    }
    mock = AsyncMock(return_value=data)
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.push(deltas)
    assert result.accepted == 1
    assert result.conflicts == []


@pytest.mark.asyncio
async def test_push_with_conflicts(client):
    from bike_analyzer.backend.sync.models import ChangeDelta
    deltas = [ChangeDelta(entity_type="ride", entity_id=1, operation="update", data={"km": 10})]
    data = {
        "accepted": 0,
        "conflicts": [
            {
                "entity_type": "ride",
                "entity_id": 1,
                "local_data": {"km": 10},
                "remote_data": {"km": 12},
                "local_reliability": 0.9,
                "remote_reliability": 0.8,
                "local_modified": "2025-01-01T00:00:00+00:00",
                "remote_modified": "2025-01-02T00:00:00+00:00",
            }
        ],
        "errors": [],
    }
    mock = AsyncMock(return_value=data)
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.push(deltas)
    assert result.accepted == 0
    assert len(result.conflicts) == 1
    assert result.conflicts[0].entity_type == "ride"


@pytest.mark.asyncio
async def test_push_error_returns_error_dict(client):
    from bike_analyzer.backend.sync.models import ChangeDelta
    deltas = [ChangeDelta(entity_type="ride", entity_id=1, operation="update", data={"km": 10})]
    mock = AsyncMock(side_effect=RuntimeError("connection lost"))
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.push(deltas)
    assert result["error"] == "connection lost"


@pytest.mark.asyncio
async def test_pull_success_with_changes_key(client):
    data = {
        "changes": [
            {"entity_type": "ride", "entity_id": 1, "operation": "update"},
            {"entity_type": "ride", "entity_id": 2, "operation": "delete"},
        ]
    }
    mock = AsyncMock(return_value=data)
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.pull(since="2025-01-01T00:00:00+00:00")
    assert len(result) == 2
    assert result[0]["entity_type"] == "ride"


@pytest.mark.asyncio
async def test_pull_success_with_list_response(client):
    data = [
        {"entity_type": "ride", "entity_id": 1, "operation": "update"},
        {"entity_type": "ride", "entity_id": 2, "operation": "update"},
    ]
    mock = AsyncMock(return_value=data)
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.pull()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_pull_unexpected_response(client):
    data = {"unexpected": True}
    mock = AsyncMock(return_value=data)
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.pull()
    assert result == {"unexpected": True}


@pytest.mark.asyncio
async def test_pull_error_returns_error_dict(client):
    mock = AsyncMock(side_effect=RuntimeError("timeout"))
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.pull()
    assert result["error"] == "timeout"


@pytest.mark.asyncio
async def test_health_success(client):
    data = {"status": "healthy", "version": "1.0"}
    mock = AsyncMock(return_value=data)
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.health()
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_success_non_dict_response(client):
    mock = AsyncMock(return_value="ok")
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.health()
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_health_error_returns_status_error(client):
    mock = AsyncMock(side_effect=RuntimeError("unreachable"))
    with patch("bike_analyzer.backend.sync.client.request_json", mock):
        result = await client.health()
    assert result["status"] == "error"
    assert "error" in result
