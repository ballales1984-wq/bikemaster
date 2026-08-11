"""Maps repository - data access abstraction for maps and async DB operations."""

from __future__ import annotations


class MapsRepository:
    @staticmethod
    def get_session_factory():
        from ...db.async_db import get_session_factory

        return get_session_factory()
