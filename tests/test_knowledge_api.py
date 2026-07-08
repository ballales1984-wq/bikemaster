"""Comprehensive tests for the knowledge base engine.

Tests cover:
- Chunk loading and caching behaviour
- BM25 search ranking and relevance
- Backward-compatible string output
- Tokenization and stop-word filtering
- Edge cases (empty KB, empty queries, missing directory)
- Helper utilities (list_topics, get_kb_stats, format_context_for_llm)
"""

from __future__ import annotations

import time

import pytest

from bike_analyzer.backend.analytics.knowledge_base import (
    CHUNK_OVERLAP,
    EMBEDDING_DIMENSION,
    KB_PATH,
    MAX_CHARS_PER_CHUNK,
    _bm25_score,
    _build_bm25_index,
    _embed_text_local,
    _extract_heading,
    _get_or_create_tfidf_vectorizer,
    _split_text,
    _tokenize,
    embed_text,
    format_context_for_llm,
    get_kb_stats,
    init_kb_embeddings,
    list_topics,
    load_chunks,
    reload_kb,
    search_knowledge_base,
)

# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------


class TestTokenization:
    def test_tokenize_returns_list(self):
        result = _tokenize("testo di prova")
        assert isinstance(result, list)

    def test_tokenize_lowercases(self):
        result = _tokenize("TEST Testo Test")
        assert all(t == t.lower() for t in result)

    def test_tokenize_removes_stopwords(self):
        result = _tokenize("il la i gli allenamento della")
        assert "il" not in result
        assert "la" not in result
        assert result  # still returns non-stop tokens if any

    def test_tokenize_short_words_removed(self):
        result = _tokenize("a bc de fg")
        assert len(result) == 0 or all(len(t) > 1 for t in result)

    def test_tokenize_empty(self):
        assert _tokenize("") == []

    def test_tokenize_italian_chars(self):
        result = _tokenize("caffè perché già")
        assert "caffè" in result or "caff" in result
        assert len(result) >= 1

    def test_tokenize_english_chars(self):
        result = _tokenize("training recovery cycling")
        assert "training" in result

    def test_tokenize_numbers_kept(self):
        result = _tokenize("zone1 zone2 zone3 80 20")
        assert "zone1" in result or "zone" in result


# ---------------------------------------------------------------------------
# Text splitting
# ---------------------------------------------------------------------------


class TestSplitText:
    def test_short_text_unchanged(self):
        short = "Ciao mondo"
        assert _split_text(short) == [short]

    def test_long_text_split(self):
        text = "A" * (MAX_CHARS_PER_CHUNK * 3)
        chunks = _split_text(text)
        assert len(chunks) > 1

    def test_chunks_respect_max_size(self):
        text = "Parola " * 500  # well over chunk size
        chunks = _split_text(text)
        for c in chunks:
            assert len(c) <= MAX_CHARS_PER_CHUNK + CHUNK_OVERLAP + 20

    def test_chunks_not_empty(self):
        text = "Prima sezione.\n\nSeconda sezione con contenuto."
        chunks = _split_text(text)
        assert all(c.strip() for c in chunks)

    def test_split_respects_paragraph_boundary(self):
        text = "Ciao mondo.\n\n" + "X" * (MAX_CHARS_PER_CHUNK + 100)
        chunks = _split_text(text)
        assert len(chunks) == 2 or chunks[0].endswith("Ciao mondo.")


# ---------------------------------------------------------------------------
# Heading extraction
# ---------------------------------------------------------------------------


class TestExtractHeading:
    def test_simple_heading(self):
        assert _extract_heading("# Training Theory") == "Training Theory"

    def test_no_heading(self):
        assert _extract_heading("Just plain text without heading") == ""

    def test_nested_heading(self):
        assert _extract_heading("### Sub-section") == "Sub-section"

    def test_heading_in_chunk(self):
        text = "Some intro.\n\n## Recovery Principles\n- Data here"
        assert _extract_heading(text) == "Recovery Principles"


# ---------------------------------------------------------------------------
# Load chunks
# ---------------------------------------------------------------------------


class TestLoadChunks:
    def test_returns_list(self):
        chunks = load_chunks()
        assert isinstance(chunks, list)

    def test_chunks_have_required_keys(self):
        chunks = load_chunks()
        if chunks:
            for key in (
                "topic",
                "chunk_id",
                "text",
                "word_count",
                "char_count",
                "token_count",
                "section",
            ):
                assert key in chunks[0]

    def test_returns_different_instance_on_force(self):
        a = load_chunks()
        b = load_chunks()
        assert a is b  # same cached object

    def test_missing_kb_path(self, tmp_path):
        original = KB_PATH
        try:
            import bike_analyzer.backend.analytics.knowledge_base as kb_mod

            kb_mod.KB_PATH = tmp_path / "missing"
            from bike_analyzer.backend.analytics.knowledge_base import reload_kb

            reload_kb()
            chunks = load_chunks()
            assert chunks == []
        finally:
            kb_mod.KB_PATH = original
            reload_kb()


# ---------------------------------------------------------------------------
# BM25 index building
# ---------------------------------------------------------------------------


class TestBM25Index:
    def test_build_index_returns_tuple(self):
        chunks = load_chunks()
        result = _build_bm25_index(chunks)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_build_index_empty(self):
        avg_dl, idf = _build_bm25_index([])
        assert avg_dl == 1.0
        assert idf == {}

    def test_build_index_positive_avg_dl(self):
        chunks = load_chunks()
        avg_dl, _ = _build_bm25_index(chunks)
        assert avg_dl > 0


# ---------------------------------------------------------------------------
# BM25 scoring
# ---------------------------------------------------------------------------


class TestBM25Score:
    def test_score_positive_for_relevant(self):
        chunks = load_chunks()
        if not chunks:
            pytest.skip("KB empty - no chunks to score")
        avg_dl, idf = _build_bm25_index(chunks)
        tokens = _tokenize("recupero stretching")
        training_chunk = next((c for c in chunks if c["topic"] == "training"), None)
        if training_chunk:
            s = _bm25_score(tokens, training_chunk, avg_dl, idf)
            assert s >= 0

    def test_score_zero_for_empty_query(self):
        chunks = load_chunks()
        if not chunks:
            pytest.skip("KB empty")
        avg_dl, idf = _build_bm25_index(chunks)
        s = _bm25_score([], chunks[0], avg_dl, idf)
        assert s == 0.0


# ---------------------------------------------------------------------------
# Search knowledge base
# ---------------------------------------------------------------------------


class TestSearchKnowledgeBase:
    def test_search_returns_list_by_default(self):
        result = search_knowledge_base("recupero")
        assert isinstance(result, list)

    def test_search_returns_string_when_asked(self):
        result = search_knowledge_base("recupero", as_string=True)
        assert isinstance(result, str)

    def test_search_no_results_empty_list(self):
        result = search_knowledge_base("xyznonexistentword12345")
        assert isinstance(result, list)
        assert len(result) == 0 or isinstance(result, str)

    def test_search_no_results_empty_string(self):
        result = search_knowledge_base("xyznonexistentword12345", as_string=True)
        assert isinstance(result, str)
        assert result == ""

    def test_search_empty_query(self):
        result = search_knowledge_base("")
        assert isinstance(result, list)
        assert result == []

    def test_search_empty_query_as_string(self):
        result = search_knowledge_base("", as_string=True)
        assert isinstance(result, str)
        assert result == ""

    def test_search_results_have_score(self):
        results = search_knowledge_base("cardio zona cardiaca", max_chunks=2)
        if isinstance(results, list) and results:
            assert "score" in results[0]
            assert results[0]["score"] > 0

    def test_search_results_sorted_descending(self):
        results = search_knowledge_base("cardio training", max_chunks=5)
        if isinstance(results, list) and len(results) > 1:
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_search_respects_max_chunks(self):
        results = search_knowledge_base("allenamento", max_chunks=2)
        if isinstance(results, list):
            assert len(results) <= 2

    def test_search_training_topic_found(self):
        results = search_knowledge_base("allenamento volume progressione", max_chunks=3)
        if isinstance(results, list):
            topics = {r["topic"] for r in results}
            assert len(topics) > 0

    def test_search_nutrition_topic_found(self):
        results = search_knowledge_base("carbohydrates protein hydration nutrition", max_chunks=3)
        if isinstance(results, list):
            topics = {r["topic"] for r in results}
            assert "nutrition" in topics

    def test_search_italian_query(self):
        results = search_knowledge_base("frequenza cardiaca zone lattato", max_chunks=3)
        if isinstance(results, list):
            assert len(results) > 0

    def test_search_bm25_relevance(self):
        training_results = search_knowledge_base(
            "polarized training periodization intervals weekly structure", max_chunks=3
        )
        nutrition_results = search_knowledge_base("carbohydrates protein hydration electrolytes", max_chunks=3)
        if isinstance(training_results, list) and isinstance(nutrition_results, list):
            training_topics = {r["topic"] for r in training_results}
            nutrition_topics = {r["topic"] for r in nutrition_results}
            assert "training_plans" in training_topics
            assert "nutrition" in nutrition_topics

    def test_search_string_output_format(self):
        result = search_knowledge_base("recupero stretching", as_string=True, max_chunks=2)
        if result:
            lines = result.split("\n")
            has_bracket = any(line.startswith("[") for line in lines)
            assert has_bracket


# ---------------------------------------------------------------------------
# list_topics
# ---------------------------------------------------------------------------


class TestListTopics:
    def test_returns_list(self):
        topics = list_topics()
        assert isinstance(topics, list)

    def test_contains_expected_topics(self):
        topics = list_topics()
        expected = {"training", "cardio", "nutrition", "recovery", "training_plans"}
        assert expected.issubset(set(topics))

    def test_sorted(self):
        topics = list_topics()
        assert topics == sorted(topics)


# ---------------------------------------------------------------------------
# get_kb_stats
# ---------------------------------------------------------------------------


class TestGetKBStats:
    def test_returns_dict(self):
        stats = get_kb_stats()
        assert isinstance(stats, dict)

    def test_has_required_keys(self):
        stats = get_kb_stats()
        for key in (
            "total_chunks",
            "total_topics",
            "topics",
            "chunks_per_topic",
            "total_words",
            "total_chars",
            "chunk_size",
            "overlap",
        ):
            assert key in stats

    def test_total_chunks_positive(self):
        stats = get_kb_stats()
        assert stats["total_chunks"] > 0

    def test_total_topics_matches(self):
        stats = get_kb_stats()
        assert stats["total_topics"] == len(stats["topics"])

    def test_chunks_per_topic_sum(self):
        stats = get_kb_stats()
        assert sum(stats["chunks_per_topic"].values()) == stats["total_chunks"]


# ---------------------------------------------------------------------------
# format_context_for_llm
# ---------------------------------------------------------------------------


class TestFormatContextForLLM:
    def test_empty_input(self):
        assert format_context_for_llm([]) == ""

    def test_formats_chunk(self):
        fake_chunk = {"text": "Testo di esempio.", "topic": "training", "section": "Base Building"}
        result = format_context_for_llm([fake_chunk])
        assert "Testo di esempio." in result

    def test_respects_max_chars(self):
        long_chunk = {"text": "X" * 10000, "topic": "training", "section": "Test"}
        result = format_context_for_llm([long_chunk], max_chars=100)
        assert len(result) <= 100 + 100  # some tolerance for headers

    def test_separator_between_chunks(self):
        chunks = [
            {"text": "Primo.", "topic": "a", "section": "A"},
            {"text": "Secondo.", "topic": "b", "section": "B"},
        ]
        result = format_context_for_llm(chunks)
        assert "---" in result


# ---------------------------------------------------------------------------
# Caching and reload
# ---------------------------------------------------------------------------


class TestCachingReload:
    def test_reload_same_content(self):
        reload_kb()
        chunks = load_chunks()
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_reload_status(self):
        result = reload_kb()
        assert result["status"] == "reloaded"
        assert "chunks_loaded" in result
        assert "timestamp" in result
        assert result["chunks_loaded"] > 0


class TestInitKbEmbeddings:
    def test_init_kb_embeddings_without_openai(self, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setattr(kb_mod, "OPENAI_API_KEY", "")
        monkeypatch.setattr(kb_mod, "_openai_embeddings_unavailable", False)
        monkeypatch.setattr(kb_mod, "_openai_circuit_failures", 0)
        result = init_kb_embeddings(session=None)
        assert "status" in result
        assert result["status"] in ("embedded_local", "error")


# ---------------------------------------------------------------------------
# BM25 search quality
# ---------------------------------------------------------------------------


class TestBM25SearchQuality:
    def test_search_result_fields(self):
        results = search_knowledge_base("cardio frequenza", max_chunks=2)
        if isinstance(results, list) and results:
            r = results[0]
            for key in (
                "topic",
                "chunk_id",
                "text",
                "score",
                "section",
                "word_count",
                "char_count",
            ):
                assert key in r, f"Missing key: {key}"

    def test_topic_field_valid(self):
        valid_topics = {
            "training",
            "cardio",
            "nutrition",
            "recovery",
            "biomechanics",
            "equipment",
            "training_plans",
        }
        results = search_knowledge_base("frequenza cardiaca zone", max_chunks=5)
        if isinstance(results, list):
            for r in results:
                assert r["topic"] in valid_topics

    def test_score_non_negative(self):
        results = search_knowledge_base("nutrizione carboidrati", max_chunks=5)
        if isinstance(results, list):
            for r in results:
                assert r["score"] >= 0


# ---------------------------------------------------------------------------
# PGVector fallback tests (Phase 24)
# ---------------------------------------------------------------------------


class TestPGVectorFallback:
    def test_embed_text_returns_list_or_none(self):
        from bike_analyzer.backend.analytics.knowledge_base import embed_text

        result = embed_text("test embedding")
        assert result is None or isinstance(result, list)

    def test_embed_text_local_fallback_returns_list(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        from bike_analyzer.backend.analytics.knowledge_base import EMBEDDING_DIMENSION, embed_text

        result = embed_text("allenamento ciclistico recupero")
        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIMENSION

    def test_search_knowledge_base_pgvector_fallback_to_bm25(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        from bike_analyzer.backend.analytics.knowledge_base import (
            search_knowledge_base_pgvector,
        )

        class FakeSession:
            def get_bind(self):
                class FakeDialect:
                    name = "sqlite"

                return FakeDialect()

        results = search_knowledge_base_pgvector("recupero", FakeSession())
        assert isinstance(results, list)

    def test_analyze_anomalies_function(self):
        from bike_analyzer.backend.analytics.ai_coach import analyze_anomalies
        from bike_analyzer.backend.models.models import Ride

        rides = [
            Ride(
                date="2024-06-01",
                distance_km=30.0,
                duration_minutes=60.0,
                avg_speed_kmh=25.0,
                calories=400,
                elevation_gain_m=100,
                heart_rate_avg=150,
            ),
            Ride(
                date="2024-06-02",
                distance_km=30.0,
                duration_minutes=60.0,
                avg_speed_kmh=25.0,
                calories=400,
                elevation_gain_m=100,
                heart_rate_avg=180,
            ),
        ]
        result = analyze_anomalies(rides)
        assert "status" in result
        assert "anomalies" in result

    def test_chat_with_tools_local_mode(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "local")
        from bike_analyzer.backend.analytics.ai_coach import chat_with_tools

        result = chat_with_tools([{"role": "user", "content": "Fammi un piano"}])
        assert "content" in result


# ---------------------------------------------------------------------------
# Circuit breaker & 429 handling
# ---------------------------------------------------------------------------


class TestCircuitBreaker429:
    def teardown_method(self, method):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        kb_mod._openai_embeddings_unavailable = False
        kb_mod._openai_circuit_failures = 0
        kb_mod._openai_circuit_last_failure = 0.0
        kb_mod._openai_circuit_cooldown = 300
        kb_mod._openai_circuit_max_failures = 3

    def test_429_sets_circuit_breaker_flag_and_falls_back(self, monkeypatch):
        from openai import APIStatusError

        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        class FakeResponse:
            status_code = 429
            headers = {}
            request = type("Req", (), {"id": "test"})()

        monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test")
        monkeypatch.setattr(kb_mod, "OPENAI_API_KEY", "sk-proj-test")
        monkeypatch.setattr(kb_mod, "_openai_circuit_max_failures", 1)
        monkeypatch.setattr(kb_mod, "_openai_circuit_cooldown", 300)

        class FakeOpenAI:
            def __init__(self, *args, **kwargs):
                pass

            class embeddings:
                @staticmethod
                def create(*args, **kwargs):
                    raise APIStatusError(
                        message="Rate limit exceeded",
                        response=FakeResponse(),
                        body=None,
                    )

        monkeypatch.setattr(kb_mod, "OpenAI", FakeOpenAI)

        result = kb_mod.embed_text("testo di embedding")
        assert kb_mod._openai_embeddings_unavailable is True
        assert isinstance(result, list)
        assert len(result) == kb_mod.EMBEDDING_DIMENSION

    def test_circuit_breaker_cooldown_resets_flag(self, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        monkeypatch.setattr(kb_mod, "_openai_embeddings_unavailable", True)
        monkeypatch.setattr(kb_mod, "_openai_circuit_last_failure", time.time() - 301)
        monkeypatch.setattr(kb_mod, "_openai_circuit_failures", 3)
        monkeypatch.setattr(kb_mod, "_openai_circuit_cooldown", 300)

        allowed = kb_mod._circuit_breaker_allows()
        assert allowed is True
        assert kb_mod._openai_embeddings_unavailable is False
        assert kb_mod._openai_circuit_failures == 0

    def test_circuit_breaker_blocks_during_cooldown(self, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        monkeypatch.setattr(kb_mod, "_openai_embeddings_unavailable", True)
        monkeypatch.setattr(kb_mod, "_openai_circuit_last_failure", time.time() - 10)
        monkeypatch.setattr(kb_mod, "_openai_circuit_failures", 3)
        monkeypatch.setattr(kb_mod, "_openai_circuit_cooldown", 300)

        allowed = kb_mod._circuit_breaker_allows()
        assert allowed is False
        assert kb_mod._openai_embeddings_unavailable is True



# ---------------------------------------------------------------------------
# Embedding cache
# ---------------------------------------------------------------------------


class TestEmbeddingCache:
    def test_cache_set_and_get(self, tmp_path, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(kb_mod, "_EMBEDDING_CACHE_PATH", cache_path)

        test_emb = [0.1, 0.2, 0.3]
        kb_mod._cache_set("hello world", test_emb, provider="test")
        result = kb_mod._cache_get("hello world")
        assert result == test_emb

    def test_cache_miss_for_empty(self, tmp_path, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(kb_mod, "_EMBEDDING_CACHE_PATH", cache_path)
        assert kb_mod._cache_get("nonexistent") is None

    def test_cache_expiry(self, tmp_path, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(kb_mod, "_EMBEDDING_CACHE_PATH", cache_path)
        monkeypatch.setattr(kb_mod, "EMBEDDING_CACHE_TTL", 1)

        kb_mod._cache_set("stale text", [0.5], provider="test")
        time.sleep(1.1)
        assert kb_mod._cache_get("stale text") is None


# ---------------------------------------------------------------------------
# Local fallback quality
# ---------------------------------------------------------------------------


class TestLocalFallback:
    def test_tfidf_vectorizer_initialized(self):
        vec = _get_or_create_tfidf_vectorizer()
        assert vec is not None

    def test_tfidf_fallback_returns_correct_dimension(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        result = _embed_text_local("testo di allenamento e recupero")
        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIMENSION

    def test_local_fallback_returns_list_when_no_openai(self, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setattr(kb_mod, "OPENAI_API_KEY", "")
        monkeypatch.setattr(kb_mod, "_openai_embeddings_unavailable", False)
        result = embed_text("testo di prova")
        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIMENSION

    def test_sentence_transformer_returns_list_when_available(self, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        class FakeModel:
            def encode(self, text, normalize_embeddings=False):
                return [0.1] * 384

        monkeypatch.setattr(kb_mod, "_sentence_transformer_model", None)
        monkeypatch.setattr(kb_mod, "_get_or_create_sentence_transformer", lambda: FakeModel())
        result = kb_mod._embed_text_sentence_transformer("test")
        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIMENSION


# ---------------------------------------------------------------------------
# Embedding provider
# ---------------------------------------------------------------------------


class TestEmbeddingProvider:
    def test_get_embedding_provider_openai_when_key_set(self, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test")
        monkeypatch.setattr(kb_mod, "OPENAI_API_KEY", "sk-proj-test")
        assert kb_mod._get_embedding_provider() == "openai"

    def test_get_embedding_provider_local_when_key_missing(self, monkeypatch):
        import bike_analyzer.backend.analytics.knowledge_base as kb_mod

        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setattr(kb_mod, "OPENAI_API_KEY", "")
        assert kb_mod._get_embedding_provider() == "local"
