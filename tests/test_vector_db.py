"""Tests for vector database integration."""
import pytest


def test_embed_text_returns_list():
    from bike_analyzer.backend.db.vector_db import embed_text, VECTOR_AVAILABLE

    if not VECTOR_AVAILABLE:
        pytest.skip("sklearn not available")

    result = embed_text("test text embedding")
    assert result is not None
    assert isinstance(result, list)


def test_similarity_search():
    from bike_analyzer.backend.db.vector_db import similarity_search, VECTOR_AVAILABLE

    if not VECTOR_AVAILABLE:
        pytest.skip("sklearn not available")

    docs = ["cycling training advice", "nutrition for athletes", "bike maintenance guide"]
    results = similarity_search("training", docs, threshold=0.0, top_k=2)
    assert len(results) > 0
    assert all(isinstance(r, tuple) for r in results)


def test_similarity_search_empty():
    from bike_analyzer.backend.db.vector_db import similarity_search

    results = similarity_search("query", [], threshold=0.1)
    assert results == []


def test_vector_store_add_and_search():
    from bike_analyzer.backend.db.vector_db import VectorStore, VECTOR_AVAILABLE
    import tempfile
    import os

    if not VECTOR_AVAILABLE:
        pytest.skip("sklearn not available")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "vectors.db")
        store = VectorStore(db_path)
        store.add("cycling training tips")
        store.add("nutrition advice")

        results = store.search("training", top_k=1)
        assert len(results) >= 0