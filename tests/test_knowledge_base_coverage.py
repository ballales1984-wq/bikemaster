"""Coverage for knowledge_base load/reload and embedding helpers."""

from __future__ import annotations

import pytest

import bike_analyzer.backend.analytics.knowledge_base as kb


def test_embedding_provider_is_local():
    assert kb._get_embedding_provider() == "local"


def test_format_context_for_llm_empty():
    assert kb.format_context_for_llm([]) == ""


def test_format_context_for_llm_formats():
    results = [
        {"topic": "training", "section": "intervals", "text": "Do intervals."},
        {"topic": "recovery", "section": "sleep", "text": "Rest well."},
    ]
    out = kb.format_context_for_llm(results)
    assert "Do intervals." in out
    assert "Rest well." in out
    assert out.count("---") >= 1


def test_embed_text_local_none_when_unavailable(monkeypatch):
    monkeypatch.setattr(kb, "_embed_text_sentence_transformer", lambda text: None)
    monkeypatch.setattr(kb, "TfidfVectorizer", None)
    assert kb._embed_text_local("anything") is None
    assert kb.embed_text("anything") is None


def test_embed_text_local_tfidf_fallback(monkeypatch):
    monkeypatch.setattr(kb, "_embed_text_sentence_transformer", lambda text: None)

    class _FakeVec:
        def transform(self, texts):
            import numpy as np
            from scipy.sparse import csr_matrix

            return csr_matrix(np.zeros((1, kb.EMBEDDING_DIMENSION)))

    monkeypatch.setattr(kb, "TfidfVectorizer", object)
    monkeypatch.setattr(kb, "_bm25_tfidf_vectorizer", None)
    monkeypatch.setattr(kb, "_get_or_create_tfidf_vectorizer", lambda: _FakeVec())
    emb = kb._embed_text_local("anything")
    assert emb is not None
    assert len(emb) == kb.EMBEDDING_DIMENSION


def test_reload_kb_returns_status():
    out = kb.reload_kb()
    assert out["status"] == "reloaded"
    assert "chunks_loaded" in out
    assert "timestamp" in out


def test_load_chunks_cache_clear():
    result = kb.load_chunks(force_reload=True)
    assert isinstance(result, list)
    result2 = kb.load_chunks()
    assert isinstance(result2, list)


def test_get_kb_stats_shape():
    stats = kb.get_kb_stats()
    assert "total_chunks" in stats
    assert "topics" in stats
    assert stats["kb_path"] == str(kb._s.kb_path)


def test_search_knowledge_base_no_chunks(monkeypatch):
    monkeypatch.setattr(kb, "load_chunks", lambda *a, **k: [])
    assert kb.search_knowledge_base("query") == []
    assert kb.search_knowledge_base("query", as_string=True) == ""
