"""Knowledge repository - data access abstraction for knowledge base operations."""

from __future__ import annotations


class KnowledgeRepository:
    @staticmethod
    def is_sqlalchemy_available() -> bool:
        from ...db.postgres_db import SQLALCHEMY_AVAILABLE

        return SQLALCHEMY_AVAILABLE

    @staticmethod
    def init_kb_embeddings(session) -> dict:
        from ...analytics.knowledge_base import init_kb_embeddings

        return init_kb_embeddings(session)

    @staticmethod
    def reload_kb() -> dict:
        from ...analytics.knowledge_base import reload_kb

        return reload_kb()

    @staticmethod
    def get_session():
        from ...db.postgres_db import get_session

        return get_session()
