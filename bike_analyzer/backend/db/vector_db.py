"""Vector database for RAG with PGVector/SQLAlchemy fallback to BM25."""

from __future__ import annotations

import sqlite3

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

# Simple fallback embedding using TF-IDF
_embeddings_cache: dict[str, np.ndarray] = {}


def _get_vectorizer() -> TfidfVectorizer | None:
    return (
        TfidfVectorizer(max_features=1000, stop_words="english")
        if VECTOR_AVAILABLE
        else None
    )


def embed_text(text: str) -> list[float] | None:
    """Get TF-IDF embedding for text (fallback to BM25)."""
    if not VECTOR_AVAILABLE:
        return None
    if text not in _embeddings_cache:
        vec = _get_vectorizer()
        if vec is None:
            return None
        _embeddings_cache[text] = vec.fit_transform([text]).toarray()[0]
    return _embeddings_cache[text].tolist()


def similarity_search(
    query: str, documents: list[str], threshold: float = 0.1, top_k: int = 4
) -> list[tuple[str, float]]:
    """Search documents by similarity."""
    if not documents or not VECTOR_AVAILABLE:
        return [(d, 1.0) for d in documents[:top_k]]

    vec = _get_vectorizer()
    if vec is None:
        return []

    doc_vectors = vec.fit_transform(documents)
    query_vec = vec.transform([query])

    scores = cosine_similarity(query_vec, doc_vectors).flatten()
    pairs = list(zip(documents, scores, strict=True))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return [(d, s) for d, s in pairs[:top_k] if s >= threshold]


class VectorStore:
    """Simple SQLite-backed vector store for development."""

    def __init__(self, db_path: str = "vectors.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS vectors "
            "(id INTEGER PRIMARY KEY, doc TEXT, embedding BLOB)"
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
