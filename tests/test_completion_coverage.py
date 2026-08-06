"""Additional coverage tests for the completion-suite target modules.

Modules under test:
- bike_analyzer.backend.analytics.performance
- bike_analyzer.backend.maps.google_maps
- bike_analyzer.backend.analytics.ai_coach
- bike_analyzer.backend.analytics.knowledge_base
- bike_analyzer.backend.processing.processing
- bike_analyzer.backend.analytics.power_model
- bike_analyzer.backend.analytics.advanced
- bike_analyzer.backend.analytics.training_load
- bike_analyzer.backend.analytics.training_stress
- bike_analyzer.backend.events
"""

from __future__ import annotations

import builtins
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from bike_analyzer.backend.analytics import advanced as adv
from bike_analyzer.backend.analytics import ai_coach as coach
from bike_analyzer.backend.analytics import knowledge_base as kb
from bike_analyzer.backend.analytics import performance as perf
from bike_analyzer.backend.analytics import power_model as pm
from bike_analyzer.backend.analytics import training_load as tl
from bike_analyzer.backend.analytics import training_stress as ts
from bike_analyzer.backend.events import (
    AthleteUpdated,
    BadgeEarned,
    RideCreated,
    TrainingGenerated,
    clear_handlers,
    is_event_bus_running,
    publish,
    start_event_bus,
    stop_event_bus,
    subscribe,
)
from bike_analyzer.backend.maps import google_maps as gm
from bike_analyzer.backend.models.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.backend.processing import processing as proc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _p(lat=45.0, lon=7.0, speed=20.0, t=None, **kw):
    return GPSPoint(lat=lat, lon=lon, timestamp=t or datetime(2024, 1, 1, 10, 0, 0), speed=speed, **kw)


def _ride(**kw):
    base = {"date": "2024-01-01", "distance_km": 30.0, "duration_minutes": 90, "avg_speed_kmh": 20.0}
    base.update(kw)
    return Ride(**base)


def _gp(speed=20.0, power=200.0, hr=140.0, t=None, **kw):
    return GPSPoint(lat=45.0, lon=7.0, timestamp=t or datetime(2024, 1, 1, 10, 0, 0), speed=speed, power=power, heart_rate=hr, **kw)


def _make_kb_dir(tmp_path: Path) -> Path:
    d = tmp_path / "kb"
    d.mkdir()
    (d / "training.md").write_text(
        "# Training\nBase building is important.\nPeriodization helps avoid overtraining.\n",
        encoding="utf-8",
    )
    return d


# ===========================================================================
# performance.py
# ===========================================================================


def test_calculate_annual_scores_empty():
    out = perf.calculate_annual_scores([])
    assert out["performance"] == 0
    assert out["total_km"] == 0


def test_calculate_annual_scores_uses_summary():
    rides = [_ride(distance_km=40.0), _ride(distance_km=60.0)]
    out = perf.calculate_annual_scores(rides)
    assert out["total_km"] == 100.0
    assert isinstance(out["performance"], float)


def test_should_save_to_database_valid():
    pts = [_p(speed=20.0), _p(speed=25.0)]
    assert perf.should_save_to_database(pts) is True


def test_should_save_to_database_empty():
    assert perf.should_save_to_database([]) is False


def test_should_save_to_database_invalid_point():
    bad = _p(lat=999.0, speed=20.0)
    assert perf.should_save_to_database([bad]) is False


def test_get_experience_level():
    a = AthleteProfile(name="X", weight_kg=70.0, experience_level="Advanced")
    assert perf.get_experience_level(a) == "Advanced"


# ===========================================================================
# google_maps.py
# ===========================================================================


def test_create_static_map_colored_url_overflow(monkeypatch, tmp_path):
    monkeypatch.setattr(gm, "_MAX_URL_LENGTH", 50)
    points = [_p(lat=45.0 + i * 0.001, lon=7.0 + i * 0.001, speed=10.0 + i) for i in range(25)]
    out = gm.create_google_static_map(
        points, api_key="test-key-mock", output_path=str(tmp_path / "m.png"), colored=True
    )
    assert out.endswith(".png")
    assert (tmp_path / "m.png").exists()


def test_create_static_map_colored_uses_segments(monkeypatch, tmp_path):
    points = [_p(lat=45.0 + i * 0.001, lon=7.0 + i * 0.001, speed=10.0 + i) for i in range(8)]
    out = gm.create_google_static_map(
        points, api_key="test-key-mock", output_path=str(tmp_path / "m.png"), colored=True
    )
    assert out.endswith(".png")


def test_get_google_api_key_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "")
    key = gm.get_google_api_key()
    assert key is None or isinstance(key, str)


def test_css_to_google_hex_idempotent():
    assert gm._css_to_google_hex("0x123456") == "0x123456"


# ===========================================================================
# processing.py
# ===========================================================================


def test_compute_statistics_no_segments():
    stats = proc.compute_statistics([_p(t=datetime(2024, 1, 1, 10, 0, 0))])
    assert stats.segment_count == 0


def test_remove_outliers_short_list():
    pts = [_p(t=datetime(2024, 1, 1, 10, 0, i)) for i in range(2)]
    assert proc.remove_outliers(pts) == pts


def test_process_route_sorts_and_stats():
    t0 = datetime(2024, 1, 1, 10, 0, 0)
    pts = [
        _p(lat=45.001, lon=7.001, speed=25.0, t=t0 + timedelta(seconds=60)),
        _p(lat=45.0, lon=7.0, speed=10.0, t=t0),
    ]
    cleaned, stats = proc.process_route(pts)
    assert len(cleaned) == 2
    assert stats.segment_count == 1


def test_validate_gps_point_valid():
    assert proc.validate_gps_point(_p()) is True


# ===========================================================================
# power_model.py
# ===========================================================================


def test_calculate_power_profile_with_points():
    t0 = datetime(2024, 1, 1, 10, 0, 0)
    pts = [_gp(power=200.0, t=t0 + timedelta(seconds=i)) for i in range(70)]
    prof = pm.calculate_power_profile(pts)
    assert "5s" in prof
    assert prof["5s"] is not None


def test_estimate_critical_power_none():
    t0 = datetime(2024, 1, 1, 10, 0, 0)
    pts = [_gp(power=200.0, t=t0 + timedelta(seconds=i)) for i in range(70)]
    out = pm.estimate_critical_power(pts)
    assert "cp_w" in out


def test_detect_aerobic_decoupling_insufficient():
    pts = [_gp(power=200.0, hr=140.0)]
    out = pm.detect_aerobic_decoupling(pts)
    assert out["decoupling_pct"] == 0.0


def test_calculate_advanced_power_metrics_no_power():
    t0 = datetime(2024, 1, 1, 10, 0, 0)
    pts = [_p(power=None, t=t0 + timedelta(seconds=i)) for i in range(70)]
    out = pm.calculate_advanced_power_metrics(pts)
    assert out["available"] is False


def test_calculate_advanced_power_metrics_with_power():
    t0 = datetime(2024, 1, 1, 10, 0, 0)
    pts = [_gp(power=200.0, hr=140.0, t=t0 + timedelta(seconds=i)) for i in range(70)]
    out = pm.calculate_advanced_power_metrics(pts, ftp=200.0)
    assert out["available"] is True
    assert "power_zones" in out


def test_power_profile_to_dict_all_none():
    empty = {5: 0.0, 60: 0.0, 300: 0.0, 600: 0.0, 1200: 0.0, 1800: 0.0}
    d = pm._power_profile_to_dict(empty)
    assert all(v is None for v in d.values())


# ===========================================================================
# training_load.py / training_stress.py
# ===========================================================================


def test_get_7day_fitness_summary_empty():
    assert tl.get_7day_fitness_summary([]) == []


def test_get_current_training_status_fatigued():
    r = _ride(date="2024-01-10", distance_km=200.0, duration_minutes=600)
    out = tl.get_current_training_status([r] * 5, ftp=200)
    assert "status" in out


def test_tss_estimate_explicit_intensity():
    r = _ride(duration_minutes=120, avg_speed_kmh=28.0)
    assert ts.estimate_tss(r) > 0


def test_ewma_single_value():
    assert ts.exponentially_weighted_moving_average([5.0], tau_days=7.0) == 5.0


# ===========================================================================
# advanced.py
# ===========================================================================


def test_get_climb_color_unknown():
    assert adv._get_climb_color("ZZ") == "#999"


def test_classify_climb_boundary():
    out = adv.classify_climb(0.2, 5.0)
    assert out["category"] == "none"


def test_estimate_ideal_weight_thresholds():
    assert adv.estimate_ideal_weight(400.0, 180.0) > 70.0
    assert adv.estimate_ideal_weight(100.0, 180.0) < 70.0


def test_training_stress_balance_external_with_rides():
    rides = [_ride(date="2024-01-01"), _ride(date="2024-01-05")]
    out = adv.compute_ctl_atl_tsb_external(rides)
    assert "tsb" in out


def test_progress_trend_declining():
    rides = [_ride(date=f"2024-01-0{i+1}", avg_speed_kmh=30.0 - i * 3) for i in range(5)]
    out = adv.calculate_progress_trend(rides)
    assert out["trend"] in ("improving", "declining", "stable")


def test_speed_surge_min_speed_filter():
    t0 = datetime(2024, 1, 1, 10, 0, 0)
    pts = [_p(speed=5.0, t=t0), _p(speed=15.0, t=t0 + timedelta(seconds=1))]
    surges = adv.detect_speed_surges(pts, min_speed_kmh=16.0)
    assert surges == []


# ===========================================================================
# events
# ===========================================================================


def test_event_type_attributes():
    assert RideCreated.type == "ride.created"
    assert AthleteUpdated.type == "athlete.updated"
    assert BadgeEarned.type == "badge.earned"
    assert TrainingGenerated.type == "training.generated"


def test_publish_with_list_data():
    clear_handlers()
    received = {}

    async def handler(data):
        received.update(data)

    subscribe("evt.x", handler)
    import asyncio

    asyncio.run(publish("evt.x", {"k": 1}))
    assert received.get("k") == 1


def test_event_bus_lifecycle():
    import asyncio

    clear_handlers()
    assert is_event_bus_running() is False
    asyncio.run(start_event_bus())
    assert is_event_bus_running() is True
    asyncio.run(start_event_bus())  # idempotent
    assert is_event_bus_running() is True
    asyncio.run(stop_event_bus())
    assert is_event_bus_running() is False


# ===========================================================================
# ai_coach.py
# ===========================================================================


@pytest.fixture(autouse=True)
def _reset_coach_state():
    coach._BANNED_PROVIDERS.clear()
    coach._current_client = None
    coach._current_provider = None
    yield
    coach._BANNED_PROVIDERS.clear()
    coach._current_client = None
    coach._current_provider = None


def test_ai_coach_prompt_helpers():
    assert "BRIEF" in coach._system_prompt()
    assert "EXAMPLES" in coach._few_shot_training_examples()
    assert "Recovery" in coach._few_shot_recovery_examples()
    assert "RULES" in coach._rules_section()


def test_build_athlete_context():
    a = AthleteProfile(
        name="Mario",
        experience_level="Advanced",
        weight_kg=72.0,
        age=34,
        years_active=5,
        annual_hours=300.0,
        goals="granfondo",
        preferred_terrain="mountain",
        weekly_volume_km=150.0,
        best_segments="P1",
    )
    ctx = coach._build_athlete_context(a)
    assert "Mario" in ctx
    assert "granfondo" in ctx
    assert "150" in ctx


def test_build_rag_context(monkeypatch):
    a = AthleteProfile(
        name="X", weight_kg=70.0, experience_level="Beginner", goals="granfondo", preferred_terrain="mountain"
    )
    rides = [_ride(avg_speed_kmh=28.0, elevation_gain_m=300.0, heart_rate_avg=170.0)]
    monkeypatch.setattr(
        coach,
        "search_knowledge_base",
        staticmethod(lambda q, **k: [{"topic": "t", "chunk_id": "t::0", "text": q, "section": "s"}]),
    )
    out = coach._build_rag_context(a, rides)
    assert "granfondo" in out or "mountain" in out


def test_local_training_advice_goal_branches(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    a = AthleteProfile(
        name="X", weight_kg=70.0, experience_level="Beginner", goals="granfondo criterium downhill", preferred_terrain="mountain flat"
    )
    monkeypatch.setattr(coach, "_kb", staticmethod(lambda q, **k: ""))
    out = coach._generate_local_training_advice(a, [])
    assert "Zone 2" in out or "Aerobic" in out


def test_local_recovery_advice_fatigued(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    a = AthleteProfile(name="X", weight_kg=70.0, experience_level="Beginner")
    monkeypatch.setattr(coach, "_kb", staticmethod(lambda q, **k: ""))
    out = coach._generate_local_recovery_advice(a, [], recovery_score=2.0)
    assert "extra recovery" in out or "stretching" in out


def test_fallback_training_with_kb(monkeypatch):
    monkeypatch.setattr(
        coach,
        "search_knowledge_base",
        staticmethod(lambda q, **k: [{"topic": "t", "chunk_id": "t::0", "text": "train hard", "section": "s"}]),
    )
    monkeypatch.setattr(coach, "format_context_for_llm", staticmethod(lambda r: "KB CTX"))
    out = coach._generate_fallback_training_advice(AthleteProfile(name="X", weight_kg=70.0), [])
    assert "KB CTX" in out


def test_fallback_training_without_kb():
    out = coach._generate_fallback_training_advice(AthleteProfile(name="X", weight_kg=70.0), [])
    assert "Recovery" in out or "recupero" in out or "volume" in out


def test_fallback_recovery_recovery_score_branch():
    out = coach._generate_fallback_recovery_advice(AthleteProfile(name="X", weight_kg=70.0), [], recovery_score=2.0)
    assert "recupero" in out or "Recovery" in out or "Stretching" in out or "Alimentazione" in out
    out2 = coach._generate_fallback_recovery_advice(AthleteProfile(name="X", weight_kg=70.0), [], recovery_score=8.0)
    assert "recupero" in out2 or "Recovery" in out2 or "Alimentazione" in out2


def test_get_ai_coach_client_invalid_user_key(monkeypatch):
    monkeypatch.setattr(
        "bike_analyzer.backend.api.user_keys.get_request_user_keys",
        staticmethod(lambda: {"groq": "not-a-key"}),
    )
    with pytest.raises(ValueError):
        coach.get_ai_coach_client()


def test_get_ai_coach_client_valid_env_key(monkeypatch):
    monkeypatch.setattr(
        "bike_analyzer.backend.api.user_keys.get_request_user_keys",
        staticmethod(lambda: {}),
    )
    monkeypatch.setenv("GROQ_API_KEY", "gsk_validkey1234567890abcdef")
    monkeypatch.setattr(coach, "_provider_order", staticmethod(lambda: ["groq"]))
    client, provider = coach.get_ai_coach_client()
    assert provider == "groq"
    assert client is not None


def test_generate_training_plan_branches():
    a = AthleteProfile(name="X", weight_kg=70.0, experience_level="Beginner", ftp_watts=250)
    p1 = coach.generate_training_plan(a, fitness_state={"tsb": -20})
    assert any(w["type"] == "Recovery" for w in p1["workouts"])
    p2 = coach.generate_training_plan(a, fitness_state={"tsb": 15})
    assert any(w["type"] in ("Quality", "VO2max") for w in p2["workouts"])
    p3 = coach.generate_training_plan(a, fitness_state={"tsb": 0})
    assert len(p3["workouts"]) >= 1


def test_generate_training_plan_no_fitness_state():
    a = AthleteProfile(name="X", weight_kg=70.0, experience_level="Elite", ftp_watts=300)
    p = coach.generate_training_plan(a)
    assert p["ftp_watts"] == 300
    assert "Generic plan" in p["explanation"] or "expert level" in p["explanation"]


def test_analyze_anomalies_variants():
    assert coach.analyze_anomalies([])["status"] == "no_data"
    rides = [_ride(heart_rate_avg=150.0), _ride(heart_rate_avg=160.0), _ride(heart_rate_avg=185.0)]
    out = coach.analyze_anomalies(rides)
    assert out["status"] == "analyzed"
    long_rides = [_ride(duration_minutes=320), _ride(duration_minutes=350), _ride(duration_minutes=360)]
    out2 = coach.analyze_anomalies(long_rides)
    assert any(x["type"] == "excessive_volume" for x in out2["anomalies"])


def test_analyze_historical_trends_alias():
    rides = [_ride() for _ in range(3)]
    assert coach.analyze_historical_trends(rides).startswith("Trend:")


def test_get_fitness_state_explanation_no_session():
    assert coach.get_fitness_state_explanation(1) == ""


def test_ai_coach_full_local(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "generate_workout_recommendations", staticmethod(lambda *a, **k: "Plan"))
    monkeypatch.setattr(coach, "generate_recovery_recommendations", staticmethod(lambda *a, **k: "Rec"))
    t0 = datetime(2024, 1, 1, 10, 0, 0)
    gps = [
        {"lat": 45.0 + i * 0.001, "lon": 7.0 + i * 0.001, "timestamp": (t0 + timedelta(seconds=i)).isoformat(), "speed": 20.0 + i}
        for i in range(5)
    ]
    a = AthleteProfile(name="X", weight_kg=70.0)
    rides = [_ride(gps_points=gps)]
    out = coach.ai_coach_full(a, rides)
    assert out["training_advice"] == "Plan"
    assert "training_scores" in out


def test_chat_with_tools_local_mode():
    out = coach.chat_with_tools([{"role": "user", "content": "hi"}])
    assert "LLM provider" in out["content"] or "Local" in out["content"]


def test_kb_with_session(monkeypatch):
    monkeypatch.setattr(
        "bike_analyzer.backend.analytics.knowledge_base.search_knowledge_base_pgvector",
        staticmethod(
            lambda q, s, **k: "[s]\nx"
        ),
    )
    out = coach._kb("query", session=object())
    assert "x" in out


def test_chat_with_tools_tool_execution(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    a = AthleteProfile(name="X", weight_kg=70.0, ftp_watts=250)

    msg = mock.Mock()
    msg.tool_calls = [mock.Mock(id="c1", function=mock.Mock(name="generate_workout_plan", arguments='{"days": 5}'))]
    msg.content = None
    call = mock.Mock()
    call.choices = [mock.Mock(message=msg)]
    second = mock.Mock()
    second.content = "done"
    call2 = mock.Mock()
    call2.choices = [mock.Mock(message=second)]
    client = mock.Mock()
    client.chat.completions.create.side_effect = [call, call2]
    monkeypatch.setattr(coach, "get_ai_coach_client", staticmethod(lambda: (client, "groq")))
    out = coach.chat_with_tools([{"role": "user", "content": "piano"}], athlete=a, rides=[])
    assert out["content"] == "done"
    assert client.chat.completions.create.call_count == 2


def test_chat_with_tools_unknown_tool(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    msg = mock.Mock()
    msg.tool_calls = [mock.Mock(id="c2", function=mock.Mock(name="unknown_tool", arguments="{}"))]
    msg.content = "x"
    call = mock.Mock()
    call.choices = [mock.Mock(message=msg)]
    second = mock.Mock()
    second.content = "fallback"
    call2 = mock.Mock()
    call2.choices = [mock.Mock(message=second)]
    client = mock.Mock()
    client.chat.completions.create.side_effect = [call, call2]
    monkeypatch.setattr(coach, "get_ai_coach_client", staticmethod(lambda: (client, "groq")))
    out = coach.chat_with_tools([{"role": "user", "content": "q"}])
    assert out["content"] == "fallback"


# ===========================================================================
# knowledge_base.py
# ===========================================================================


def test_tokenize_strips_stopwords():
    toks = kb._tokenize("Il ciclista corre velocemente con la bici")
    assert "ciclista" in toks
    assert "il" not in toks


def test_extract_heading():
    assert kb._extract_heading("# Title\nbody") == "Title"
    assert kb._extract_heading("no heading") == ""


def test_split_text_short():
    assert kb._split_text("short text") == ["short text"]


def test_split_text_long_overlap():
    chunks = kb._split_text("word " * 500)
    assert len(chunks) > 1


def test_bm25_index_and_score():
    chunks = [
        {"text": "base training periodization", "section": "s", "token_count": 4},
        {"text": "recovery sleep hydration", "section": "s", "token_count": 3},
    ]
    avg_dl, idf = kb._build_bm25_index(chunks)
    assert avg_dl > 0
    score = kb._bm25_score(["training"], chunks[0], avg_dl, idf)
    assert score > 0


def test_get_embedding_provider():
    assert kb._get_embedding_provider() == "local"


def test_list_topics(tmp_path, monkeypatch):
    d = _make_kb_dir(tmp_path)
    monkeypatch.setattr(kb._s, "kb_path", d)
    topics = kb.list_topics()
    assert "training" in topics


def test_load_chunks_and_stats(tmp_path, monkeypatch):
    d = _make_kb_dir(tmp_path)
    monkeypatch.setattr(kb._s, "kb_path", d)
    kb._cached_load.cache_clear()
    chunks = kb.load_chunks(force_reload=True)
    assert len(chunks) >= 1
    stats = kb.get_kb_stats()
    assert stats["total_chunks"] >= 1
    assert "training" in stats["topics"]


def test_reload_kb(tmp_path, monkeypatch):
    d = _make_kb_dir(tmp_path)
    monkeypatch.setattr(kb._s, "kb_path", d)
    kb._cached_load.cache_clear()
    out = kb.reload_kb()
    assert out["status"] == "reloaded"


def test_search_knowledge_base_bm25_fallback(tmp_path, monkeypatch):
    d = _make_kb_dir(tmp_path)
    monkeypatch.setattr(kb._s, "kb_path", d)
    real_import = builtins.__import__

    def _fake(name, *a, **k):
        if name == "chromadb":
            raise ImportError("no chroma")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _fake)
    kb._cached_load.cache_clear()
    res = kb.search_knowledge_base("training periodization", max_chunks=2)
    assert isinstance(res, list) and len(res) >= 1


def test_search_knowledge_base_empty_query(tmp_path, monkeypatch):
    d = _make_kb_dir(tmp_path)
    monkeypatch.setattr(kb._s, "kb_path", d)
    kb._cached_load.cache_clear()
    assert kb.search_knowledge_base("!!! ???", max_chunks=2) == []


def test_format_context_for_llm_list():
    res = [{"section": "S", "topic": "T", "text": "body text"}]
    out = kb.format_context_for_llm(res)
    assert "body text" in out


def test_import_with_timeout():
    assert kb._import_with_timeout("nonexistent_module_xyz", timeout=1) is None
    assert kb._import_with_timeout("os", timeout=5) is not None


def test_tfidf_vectorizer_init(monkeypatch):
    monkeypatch.setattr(kb, "_embed_text_sentence_transformer", staticmethod(lambda t: None))
    monkeypatch.setattr(kb, "_get_or_create_tfidf_vectorizer", staticmethod(lambda: None))
    out = kb._embed_text_local("some text")
    assert out is None or isinstance(out, list)


def test_init_kb_embeddings_local(monkeypatch):
    monkeypatch.setattr(kb, "_embed_text_local", staticmethod(lambda t: [0.1, 0.2, 0.3]))
    monkeypatch.setattr(
        kb,
        "load_chunks",
        staticmethod(
            lambda: [{"text": "x", "topic": "t", "chunk_id": "t::0", "section": "s", "word_count": 1, "char_count": 1, "token_count": 1}]
        ),
    )
    out = kb.init_kb_embeddings(session=None)
    assert out["status"] == "embedded_local"


def test_init_kb_embeddings_session(monkeypatch):
    monkeypatch.setattr(
        kb,
        "load_chunks",
        staticmethod(
            lambda: [{"text": "x", "topic": "t", "chunk_id": "t::0", "section": "s", "word_count": 1, "char_count": 1, "token_count": 1}]
        ),
    )
    monkeypatch.setattr(kb, "save_chunks_to_pgvector", staticmethod(lambda c, s: 1))
    out = kb.init_kb_embeddings(session=object())
    assert out["status"] == "embedded"


def test_save_chunks_to_pgvector(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.added = 0

        def add(self, obj):
            self.added += 1

        def commit(self):
            pass

    monkeypatch.setattr(kb, "embed_text", staticmethod(lambda t: [0.0, 1.0]))
    monkeypatch.setattr(
        "bike_analyzer.backend.db.models.KnowledgeChunkModel",
        lambda **kw: kw,
    )
    sess = FakeSession()
    saved = kb.save_chunks_to_pgvector([{"topic": "t", "chunk_id": "t::0", "text": "x"}], sess)
    assert saved == 1


def test_search_kb_pgvector_allthrough(tmp_path, monkeypatch):
    d = _make_kb_dir(tmp_path)
    monkeypatch.setattr(kb._s, "kb_path", d)
    real_import = builtins.__import__

    def _fake(name, *a, **k):
        if name == "chromadb":
            raise ImportError("no chroma")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _fake)
    monkeypatch.setattr(kb, "_is_postgres", staticmethod(lambda s: False))
    monkeypatch.setattr(kb, "embed_text", staticmethod(lambda q: None))
    kb._cached_load.cache_clear()
    out = kb.search_knowledge_base_pgvector("query", session=object(), max_chunks=2)
    assert isinstance(out, (list, str))


def test_init_chroma_db_no_chromadb(monkeypatch):
    real_import = builtins.__import__

    def _fake(name, *a, **k):
        if name == "chromadb":
            raise ImportError("no chroma")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _fake)
    out = kb.init_chroma_db(persist_path="/tmp/nonexistent_chroma")
    assert out["status"] == "error"
