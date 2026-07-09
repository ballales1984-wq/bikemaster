"""Vector database integration for RAG using PGVector.

Provides embedding storage and similarity search for knowledge base.
"""

from __future__ import annotations

import numpy as np
from sqlalchemy import text
from typing import Any
from sqlalchemy.ext.asyncio import create_async_engine

from ..settings import get_settings

_s = get_settings()


class VectorDB:
    """PGVector wrapper for embedding storage and similarity search."""

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or _s.database_url
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        self._engine = None

    async def _get_engine(self):
        if self._engine is None:
            self._engine = create_async_engine(self.database_url, echo=False)
        return self._engine

    async def init_vector_table(self) -> None:
        """Create the vector extension and embeddings table."""
        engine = await self._get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS kb_embeddings (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    section TEXT,
                    content TEXT,
                    embedding VECTOR(1536)
                )
            """)
            )
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_kb_embedding ON kb_embeddings
                USING IVFFLAT (embedding vector_cosine_ops)
            """)
            )

    async def upsert_embedding(
        self,
        id: str,
        topic: str,
        section: str,
        content: str,
        embedding: list[float],
    ) -> None:
        """Insert or update an embedding."""
        engine = await self._get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                INSERT INTO kb_embeddings (id, topic, section, content, embedding)
                VALUES (:id, :topic, :section, :content, :embedding)
                ON CONFLICT (id) DO UPDATE SET
                    topic = EXCLUDED.topic,
                    section = EXCLUDED.section,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
            """),
                {
                    "id": id,
                    "topic": topic,
                    "section": section,
                    "content": content,
                    "embedding": embedding,
                },
            )

    async def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 4,
        min_similarity: float = 0.2,
    ) -> list[dict[str, Any]]:
        """Find similar embeddings using cosine similarity."""
        engine = await self._get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                SELECT id, topic, section, content, 1 - (embedding <=> :q) as similarity
                FROM kb_embeddings
                WHERE 1 - (embedding <=> :q) > :min_sim
                ORDER BY embedding <=> :q
                LIMIT :limit
            """),
                {"q": query_embedding, "min_similarity": min_similarity, "limit": top_k},
            )
            rows = result.fetchall()
            return [{"id": r[0], "topic": r[1], "section": r[2], "content": r[3], "similarity": r[4]} for r in rows]


def get_embedding(text: str) -> list[float]:
    """Get deterministic embedding (offline/dev fallback)."""
    # Deterministic fallback so tests/imports work without an external API.
    np.random.seed(len(text))
    return np.random.random(1536).tolist()
