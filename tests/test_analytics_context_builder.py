"""Tests for ContextBuilder."""

import pytest

from bike_analyzer.backend.analytics.services.context_builder import ContextBuilder


@pytest.fixture
def builder():
    return ContextBuilder(athlete_id=1)


def test_build_training_context_defaults(builder):
    ctx = builder.build_training_context()
    assert ctx["athlete"] == {}
    assert ctx["fitness_state"] == {}
    assert ctx["recent_rides"] == []
    assert ctx["trends"] == {"short_term": "stable", "long_term": "stable"}
    assert ctx["recommendations"] == []


def test_build_training_context_with_data(builder):
    athlete = {"name": "Test", "ftp_watts": 250}
    rides = [{"performance_score": 6.0}, {"performance_score": 7.0}]
    fitness = {"tsb": 10, "atl": 60, "ctl": 70}
    ctx = builder.build_training_context(athlete=athlete, rides=rides, fitness_state=fitness)
    assert ctx["athlete"] == athlete
    assert ctx["recent_rides"] == rides
    assert ctx["fitness_state"] == fitness
    assert "Almost ready for quality work" in ctx["recommendations"][0]


def test_build_training_context_rides_truncated(builder):
    rides = [{"performance_score": 5.0}] * 15
    ctx = builder.build_training_context(rides=rides)
    assert len(ctx["recent_rides"]) == 10


def test_build_recovery_context_no_fitness(builder):
    ctx = builder.build_recovery_context()
    assert ctx["recovery_score"] == 10.0
    assert ctx["recovery_needed"] is False
    assert ctx["explanation"] == "Nessun dato fitness disponibile"


def test_build_recovery_context_with_fitness(builder):
    fitness = {"tsb": -30, "recovery_hours_needed": 36}
    ctx = builder.build_recovery_context(fitness_state=fitness)
    assert ctx["recovery_score"] == 2.0
    assert ctx["recovery_needed"] is True
    assert ctx["hours_needed"] == 36
    assert "accumulated fatigue" in ctx["explanation"]


def test_build_recovery_context_score_clamped(builder):
    fitness = {"tsb": -100}
    ctx = builder.build_recovery_context(fitness_state=fitness)
    assert ctx["recovery_score"] == 0.0


def test_compute_trends_empty(builder):
    assert builder._compute_trends([]) == {"short_term": "stable", "long_term": "stable"}
    assert builder._compute_trends(None) == {"short_term": "stable", "long_term": "stable"}


def test_compute_trends_single_ride(builder):
    rides = [{"performance_score": 5.0, "weekly_tss": 100, "monthly_tss": 400}]
    trends = builder._compute_trends(rides)
    assert trends["short_term"] == "stable"
    assert trends["long_term"] == "stable"


def test_compute_trends_improving(builder):
    rides = [
        {"performance_score": 4.0, "weekly_tss": 100, "monthly_tss": 400},
        {"performance_score": 5.0},
        {"performance_score": 6.0},
        {"performance_score": 7.0},
        {"performance_score": 8.0},
    ]
    trends = builder._compute_trends(rides)
    assert trends["short_term"] == "improving"


def test_compute_trends_declining(builder):
    rides = [
        {"performance_score": 8.0, "weekly_tss": 100, "monthly_tss": 400},
        {"performance_score": 7.0},
        {"performance_score": 6.0},
        {"performance_score": 5.0},
        {"performance_score": 4.0},
    ]
    trends = builder._compute_trends(rides)
    assert trends["short_term"] == "declining"


def test_recommendations_positive_tsb(builder):
    recs = builder._recommendations_from_state({"tsb": 20, "atl": 50, "ctl": 60})
    assert any("Ready for intense efforts" in r for r in recs)


def test_recommendations_negative_tsb(builder):
    recs = builder._recommendations_from_state({"tsb": -25, "atl": 70, "ctl": 50})
    assert any("affaticamento" in r for r in recs)


def test_recommendations_overtraining(builder):
    recs = builder._recommendations_from_state({"tsb": 5, "atl": 80, "ctl": 50})
    assert any("sovrallenamento" in r for r in recs)


def test_recommendations_none(builder):
    assert builder._recommendations_from_state(None) == []
    assert builder._recommendations_from_state({}) == []


def test_build_explanation_fatigue(builder):
    fitness = {"tsb": -25, "atl": 70, "ctl": 60, "recovery_hours_needed": 12}
    exp = builder._build_explanation(fitness)
    assert "accumulated fatigue" in exp


def test_build_explanation_fresh(builder):
    fitness = {"tsb": 20, "atl": 50, "ctl": 60}
    exp = builder._build_explanation(fitness)
    assert "good freshness" in exp


def test_build_explanation_stable(builder):
    fitness = {"tsb": 5, "atl": 55, "ctl": 60}
    exp = builder._build_explanation(fitness)
    assert exp == "Stable fitness state"


def test_build_explanation_no_data(builder):
    assert builder._build_explanation(None) == "Nessun dato fitness disponibile"
    assert builder._build_explanation({}) == "Nessun dato fitness disponibile"


@pytest.mark.asyncio
async def test_fetch_full_context_no_factory(builder):
    ctx = await builder.fetch_full_context()
    assert ctx["athlete"] == {}
    assert ctx["recent_rides"] == []
