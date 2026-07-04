"""Tests for User repository."""

from unittest import mock

import pytest

from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository


def _make_async_session():
    session = mock.MagicMock()
    session.execute = mock.AsyncMock()
    session.commit = mock.AsyncMock()
    return session


def _make_factory():
    factory = mock.MagicMock()
    cm = mock.MagicMock()
    cm.__aenter__ = mock.AsyncMock(return_value=_make_async_session())
    cm.__aexit__ = mock.AsyncMock(return_value=False)
    factory.return_value = cm
    return factory


class TestUserRepository:
    def test_constructor_defaults(self):
        repo = UserRepository()
        assert repo._session_factory is None
        assert repo._sync_conn is None

    @pytest.mark.asyncio
    async def test_get_by_id_async_not_found(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        mappings_mock = mock.MagicMock()
        mappings_mock.first.return_value = None
        result_mock = mock.MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute.return_value = result_mock

        repo = UserRepository(session_factory=factory)
        result = await repo.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_username_async_not_found(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        mappings_mock = mock.MagicMock()
        mappings_mock.first.return_value = None
        result_mock = mock.MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute.return_value = result_mock

        repo = UserRepository(session_factory=factory)
        result = await repo.get_by_username("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_async_not_found(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        mappings_mock = mock.MagicMock()
        mappings_mock.first.return_value = None
        result_mock = mock.MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute.return_value = result_mock

        repo = UserRepository(session_factory=factory)
        result = await repo.get_by_email("not@found.com")
        assert result is None

    def test_sync_methods_not_implemented(self):
        repo = UserRepository(sync_conn=None)
        with pytest.raises(NotImplementedError):
            repo._save_sync({"username": "test"})
        with pytest.raises(NotImplementedError):
            repo._get_by_id_sync(1)
        with pytest.raises(NotImplementedError):
            repo._get_by_username_sync("test")
        with pytest.raises(NotImplementedError):
            repo._get_by_email_sync("test@test.com")
        with pytest.raises(NotImplementedError):
            repo._list_all_sync()
