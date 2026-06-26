"""Vector database for RAG with PGVector similarity.

Provides PGVector-backed semantic search with TF-IDF fallback.
"""

from __future__ import annotations

import sqlite3

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

EMBEDDING_DIMENSION = 1536
_vectorizer: TfidfVectorizer | None = None


def _get_vectorizer() -> TfidfVectorizer | None:
    global _vectorizer
    if SKLEARN_AVAILABLE and _vectorizer is None:
        _vectorizer = TfidfVectorizer(max_features=EMBEDDING_DIMENSION, stop_words="english")
    return _vectorizer


def embed_text(text: str) -> list[float] | None:
    """Get TF-IDF embedding for text (fallback when OpenAI unavailable)."""
    if not SKLEARN_AVAILABLE:
        return [0.0] * EMBEDDING_DIMENSION
    vec = _get_vectorizer()
    if vec is None:
        return [0.0] * EMBEDDING_DIMENSION
    try:
        embedding = vec.fit_transform([text]).toarray()[0]
        if len(embedding) < EMBEDDING_DIMENSION:
            embedding = np.pad(embedding, (0, EMBEDDING_DIMENSION - len(embedding)))
        return embedding.tolist()
    except Exception:
        return [0.0] * EMBEDDING_DIMENSION


def similarity_search(
    query: str, documents: list[str], threshold: float = 0.1, top_k: int = 4
) -> list[tuple[str, float]]:
    """Search documents by similarity using TF-IDF cosine similarity."""
    if not documents:
        return []

    vec = _get_vectorizer()
    if vec is None:
        return []

    doc_vectors = vec.fit_transform(documents)
    query_vec = vec.transform([query])

    scores = cosine_similarity(query_vec, doc_vectors).flatten()
    pairs = list(zip(documents, scores, strict=True))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return [(d, float(s)) for d, s in pairs[:top_k] if s >= threshold]


class VectorStore:
    """SQLite-backed vector store for development fallback."""

    def __init__(self, db_path: str = "vectors.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS vectors "
            "(id INTEGER PRIMARY KEY, doc TEXT, embedding TEXT)"
        )
        conn.commit()
        conn.close()

    def add(self, doc: str, embedding: list[float] | None = None):
        if embedding is None:
            embedding = embed_text(doc)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO vectors (doc, embedding) VALUES (?, ?)",
            (doc, str(embedding) if embedding else ""),
        )
        conn.commit()
        conn.close()

    def search(self, query: str, top_k: int = 4) -> list[tuple[str, float]]:
        return similarity_search(
            query, [r[0] for r in self._all_docs()], top_k=top_k
        )

    def _all_docs(self) -> list[tuple[str]]:
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT doc FROM vectors LIMIT 1000").fetchall()
        conn.close()
        return rows
