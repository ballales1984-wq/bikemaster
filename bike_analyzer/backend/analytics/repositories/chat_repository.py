"""Chat repository - data access abstraction for AI coach chat history."""

from __future__ import annotations


class ChatRepository:
    @staticmethod
    def get_chat_history(athlete_id: int, tenant_id: int = 0):
        from ...db.database import get_chat_history

        return get_chat_history(athlete_id, tenant_id=tenant_id)

    @staticmethod
    def save_chat_message(athlete_id: int, role: str, content: str, tenant_id: int = 0):
        from ...db.database import save_chat_message

        return save_chat_message(athlete_id, role, content, tenant_id)
