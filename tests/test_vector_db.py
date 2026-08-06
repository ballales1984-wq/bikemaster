"""Tests for vector DB adapter (vector_db).

Covers:
- embed_text with TF-IDF fallback
- similarity_search ranking and threshold
- VectorStore add/search roundtrip
- Graceful degradation when sklearn is unavailable
"""

from __future__ import annotations

import importlib

from bike_analyzer.backend.db import vector_db


class TestEmbedText:
    def test_returns_list_of_floats(self):
        result = vector_db.embed_text("hello world")
        assert isinstance(result, list)
        assert all(isinstance(x, float) for x in result)

    def test_consistent_embedding_for_same_text(self):
        a = vector_db.embed_text("test document")
        b = vector_db.embed_text("test document")
        assert a == b

    def test_different_texts_produce_different_embeddings(self):
        a = vector_db.embed_text("cycling power output watts and cadence")
        b = vector_db.embed_text("weather forecast rain and temperature")
        assert a != b


class TestSimilaritySearch:
    def test_returns_top_k_documents(self):
        docs = ["cycling power", "weather rain", "cycling cadence", "coffee break"]
        results = vector_db.similarity_search("cycling power", docs, top_k=2)
        assert len(results) <= 2
        assert all(doc in docs for doc, _ in results)

    def test_ranked_by_score_descending(self):
        docs = ["cycling power output", "weather forecast", "cycling cadence sensor"]
        results = vector_db.similarity_search("cycling power", docs, top_k=3)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_threshold_filters_low_scores(self):
        docs = ["completely unrelated topic about quantum physics"]
        results = vector_db.similarity_search("cycling", docs, threshold=0.5, top_k=4)
        assert len(results) == 0

    def test_empty_documents_returns_empty(self):
        results = vector_db.similarity_search("query", [], top_k=4)
        assert results == []

    def test_single_document_returned(self):
        docs = ["the only document"]
        results = vector_db.similarity_search("document", docs, top_k=4, threshold=0.0)
        assert len(results) == 1
        assert results[0][0] == "the only document"


class TestVectorStore:
    def test_add_and_search_roundtrip(self, tmp_path):
        db_path = str(tmp_path / "vectors.db")
        store = vector_db.VectorStore(db_path=db_path)
        store.add("cycling power analysis")
        store.add("weather forecast for the ride")
        results = store.search("cycling", top_k=2)
        assert len(results) >= 1
        docs = [doc for doc, _ in results]
        assert "cycling power analysis" in docs

    def test_add_with_custom_embedding(self, tmp_path):
        db_path = str(tmp_path / "vectors2.db")
        store = vector_db.VectorStore(db_path=db_path)
        store.add("doc text", embedding=[0.1, 0.2, 0.3])
        results = store.search("doc", top_k=1)
        assert len(results) == 1
        assert results[0][0] == "doc text"


class TestGracefulDegradation:
    def test_embed_text_returns_none_when_sklearn_unavailable(self):
        _ = importlib.reload(vector_db)
        original = vector_db.VECTOR_AVAILABLE
        try:
            vector_db.VECTOR_AVAILABLE = False
            result = vector_db.embed_text("test")
            assert result is None
        finally:
            vector_db.VECTOR_AVAILABLE = original

    def test_similarity_search_fallback_when_sklearn_unavailable(self):
        original = vector_db.VECTOR_AVAILABLE
        try:
            vector_db.VECTOR_AVAILABLE = False
            docs = ["doc one", "doc two"]
            results = vector_db.similarity_search("query", docs, top_k=2)
            assert len(results) == 2
        finally:
            vector_db.VECTOR_AVAILABLE = original
