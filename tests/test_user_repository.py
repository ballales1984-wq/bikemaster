"""Tests for User repository."""

from __future__ import annotations

import pytest


class TestUserRepositoryAsync:
    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self):
        from unittest.mock import AsyncMock, MagicMock

        from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        mock_session_factory = MagicMock(return_value=mock_session)
        repo = UserRepository(session_factory=mock_session_factory)
        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_username_returns_none_for_missing(self):
        from unittest.mock import AsyncMock, MagicMock

        from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        mock_session_factory = MagicMock(return_value=mock_session)
        repo = UserRepository(session_factory=mock_session_factory)
        result = await repo.get_by_username("nonexistent")

        assert result is None


class TestUserRepositorySync:
    def test_save_sync_raises_not_implemented(self):
        from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository

        repo = UserRepository(sync_conn=None)
        with pytest.raises(NotImplementedError):
            repo._save_sync({"username": "test"})

    def test_get_by_id_sync_raises_not_implemented(self):
        from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository

        repo = UserRepository(sync_conn=None)
        with pytest.raises(NotImplementedError):
            repo._get_by_id_sync(1)

    def test_get_by_username_sync_raises_not_implemented(self):
        from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository

        repo = UserRepository(sync_conn=None)
        with pytest.raises(NotImplementedError):
            repo._get_by_username_sync("test")

    def test_get_by_email_sync_raises_not_implemented(self):
        from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository

        repo = UserRepository(sync_conn=None)
        with pytest.raises(NotImplementedError):
            repo._get_by_email_sync("test@test.com")

    def test_list_all_sync_raises_not_implemented(self):
        from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository

        repo = UserRepository(sync_conn=None)
        with pytest.raises(NotImplementedError):
            repo._list_all_sync()