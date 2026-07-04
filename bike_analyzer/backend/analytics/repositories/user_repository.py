"""User repository - data access abstraction for users."""

from __future__ import annotations

from datetime import UTC, datetime


class UserRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    async def save(self, user: dict) -> int:
        if self._session_factory:
            return await self._save_async(user)
        return self._save_sync(user)

    async def get_by_id(self, user_id: int) -> dict | None:
        if self._session_factory:
            return await self._get_by_id_async(user_id)
        return self._get_by_id_sync(user_id)

    async def get_by_username(self, username: str) -> dict | None:
        if self._session_factory:
            return await self._get_by_username_async(username)
        return self._get_by_username_sync(username)

    async def get_by_email(self, email: str) -> dict | None:
        if self._session_factory:
            return await self._get_by_email_async(email)
        return self._get_by_email_sync(email)

    async def list_all(self) -> list[dict]:
        if self._session_factory:
            return await self._list_all_async()
        return self._list_all_sync()

    async def _save_async(self, user: dict) -> int:
        from sqlalchemy import insert

        async with self._session_factory() as session:
            stmt = (
                insert(self._table)
                .values(
                    username=user.get("username", ""),
                    email=user.get("email"),
                    password_hash=user.get("password_hash"),
                    is_admin=user.get("is_admin", False),
                    is_active=user.get("is_active", True),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                .returning(self._table.id)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def _get_by_id_async(self, user_id: int) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.id == user_id)
            result = await session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None

    async def _get_by_username_async(self, username: str) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.username == username)
            result = await session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None

    async def _get_by_email_async(self, email: str) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.email == email)
            result = await session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None

    async def _list_all_async(self) -> list[dict]:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table)
            result = await session.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    @property
    def _table(self):
        from ...db.models import UserModel

        return UserModel

    def _save_sync(self, user: dict) -> int:
        raise NotImplementedError("Sync user save not implemented")

    def _get_by_id_sync(self, user_id: int) -> dict | None:
        raise NotImplementedError("Sync user get_by_id not implemented")

    def _get_by_username_sync(self, username: str) -> dict | None:
        raise NotImplementedError("Sync user get_by_username not implemented")

    def _get_by_email_sync(self, email: str) -> dict | None:
        raise NotImplementedError("Sync user get_by_email not implemented")

    def _list_all_sync(self) -> list[dict]:
        raise NotImplementedError("Sync user list_all not implemented")
