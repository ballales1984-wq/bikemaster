"""Tests for the async ChatHistoryRepository (AI Coach persistent memory)."""

from __future__ import annotations

import types

import pytest

from bike_analyzer.backend.analytics.repositories.chat_history_repository import ChatHistoryRepository


class _FakeRow:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeResult:
    def __init__(self, scalar=None, rows=None, rowcount=0):
        self._scalar = scalar
        self._rows = rows or []
        self._rowcount = rowcount

    def scalar_one(self):
        return self._scalar

    def mappings(self):
        class _M:
            def __init__(self_inner, rows):
                self_inner._rows = rows

            def all(self_inner):
                return self_inner._rows

        return _M(self._rows)

    def scalars(self):
        class _S:
            def __init__(self_inner, rows):
                self_inner._rows = rows

            def all(self_inner):
                return self_inner._rows

        return _S([_FakeRow(**r) if isinstance(r, dict) else r for r in self._rows])

    @property
    def rowcount(self):
        return self._rowcount


class _FakeSession:
    def __init__(self, result):
        self._result = result
        self.executed = []

    async def execute(self, stmt):
        self.executed.append(stmt)
        return self._result

    async def commit(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeFactory:
    def __init__(self, result):
        self._result = result

    def __call__(self):
        return _FakeSession(self._result)


async def test_save_returns_id():
    repo = ChatHistoryRepository(session_factory=_FakeFactory(_FakeResult(scalar=7)))
    assert await repo.save(1, "user", "ciao", tenant_id=0) == 7


async def test_get_recent_returns_rows():
    repo = ChatHistoryRepository(
        session_factory=_FakeFactory(
            _FakeResult(
                rows=[
                    {
                        "id": 1,
                        "athlete_id": 1,
                        "tenant_id": 0,
                        "role": "user",
                        "content": "x",
                        "created_at": None,
                    }
                ]
            )
        )
    )
    rows = await repo.get_recent(1, limit=5)
    assert rows == [
        {"id": 1, "athlete_id": 1, "tenant_id": 0, "role": "user", "content": "x", "created_at": None}
    ]


async def test_clear_returns_rowcount():
    repo = ChatHistoryRepository(session_factory=_FakeFactory(_FakeResult(rowcount=3)))
    assert await repo.clear(1, tenant_id=0) == 3


async def test_prune_returns_rowcount():
    repo = ChatHistoryRepository(session_factory=_FakeFactory(_FakeResult(rowcount=2)))
    assert await repo.prune(1, retention_days=90) == 2


async def test_no_factory_raises_or_returns_empty():
    repo = ChatHistoryRepository(session_factory=None)
    with pytest.raises(RuntimeError):
        await repo.save(1, "user", "x")
    assert await repo.get_recent(1) == []
    assert await repo.clear(1) == 0
    assert await repo.prune(1) == 0
