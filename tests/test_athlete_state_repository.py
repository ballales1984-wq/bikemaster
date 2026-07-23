"""Tests for backend.analytics.athlete_state.repository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from bike_analyzer.backend.analytics.athlete_state.models import AthleteState
from bike_analyzer.backend.analytics.athlete_state.repository import (
    AthleteStateRepository,
)


def _make_state(**overrides):
    base = {
        "athlete_id": 1,
        "computed_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        "atl": 45.0,
        "ctl": 80.0,
        "tsb": 10.0,
        "fitness": 80.0,
        "fatigue": 45.0,
        "form": 10.0,
        "fatigue_score": 0.3,
        "readiness": 85.0,
        "acwr": 0.9,
        "recovery_hours_needed": 12.0,
        "weekly_tss": 450.0,
        "monthly_tss": 1800.0,
        "trend_7d": "improving",
        "trend_30d": "stable",
        "risk_indicators": [],
        "recommendation": "Keep going",
        "risk_level": "ok",
    }
    base.update(overrides)
    return AthleteState(**base)


class TestToFitnessDict:
    def test_basic_fields(self):
        repo = AthleteStateRepository()
        state = _make_state()
        d = repo._to_fitness_dict(state, tenant_id=0)
        assert d["athlete_id"] == 1
        assert d["fitness"] == 80.0
        assert d["fatigue"] == 45.0
        assert d["form"] == 10.0
        assert d["ctl"] == 80.0
        assert d["atl"] == 45.0
        assert d["tsb"] == 10.0

    def test_risk_indicators_embedded_in_payload(self):
        repo = AthleteStateRepository()
        state = _make_state(risk_indicators=["existing"])
        d = repo._to_fitness_dict(state, tenant_id=0)
        assert len(d["risk_indicators"]) == 2
        assert d["risk_indicators"][0] == "existing"
        extra = d["risk_indicators"][1]
        parsed = __import__("json").loads(extra)
        assert parsed["fatigue_score"] == 0.3
        assert parsed["readiness"] == 85.0
        assert parsed["acwr"] == 0.9
        assert parsed["risk_level"] == "ok"

    def test_tenant_id_passed_through(self):
        repo = AthleteStateRepository()
        state = _make_state()
        d = repo._to_fitness_dict(state, tenant_id=5)
        assert d["tenant_id"] == 5


class TestFromFitnessRow:
    def test_basic_row(self):
        repo = AthleteStateRepository()
        row = {
            "athlete_id": 1,
            "computed_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            "atl": 45.0,
            "ctl": 80.0,
            "tsb": 10.0,
            "fitness": 80.0,
            "fatigue": 45.0,
            "form": 10.0,
            "recovery_hours_needed": 12.0,
            "weekly_tss": 450.0,
            "monthly_tss": 1800.0,
            "trend_7d": "improving",
            "trend_30d": "stable",
            "risk_indicators": [],
            "recommendation": "Keep going",
        }
        state = repo._from_fitness_row(row)
        assert state.athlete_id == 1
        assert state.fatigue_score == 0.0
        assert state.readiness == 100.0
        assert state.acwr == 1.0
        assert state.risk_level == "ok"

    def test_row_with_json_string_risk_indicators(self):
        repo = AthleteStateRepository()
        extra_json = __import__("json").dumps({
            "fatigue_score": 0.7,
            "readiness": 55.0,
            "acwr": 1.4,
            "risk_level": "high",
        })
        row = {
            "athlete_id": 2,
            "computed_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            "atl": 50.0,
            "ctl": 70.0,
            "tsb": -5.0,
            "fitness": 70.0,
            "fatigue": 50.0,
            "form": -5.0,
            "recovery_hours_needed": 24.0,
            "weekly_tss": 500.0,
            "monthly_tss": 2000.0,
            "trend_7d": "stable",
            "trend_30d": "declining",
            "risk_indicators": [extra_json],
            "recommendation": "Rest",
        }
        state = repo._from_fitness_row(row)
        assert state.fatigue_score == 0.7
        assert state.readiness == 55.0
        assert state.acwr == 1.4
        assert state.risk_level == "high"

    def test_row_with_mixed_risk_indicators(self):
        repo = AthleteStateRepository()
        extra = __import__("json").dumps({"fatigue_score": 0.5, "risk_level": "high"})
        row = {
            "athlete_id": 3,
            "computed_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            "atl": 48.0,
            "ctl": 75.0,
            "tsb": 5.0,
            "fitness": 75.0,
            "fatigue": 48.0,
            "form": 5.0,
            "recovery_hours_needed": 8.0,
            "weekly_tss": 400.0,
            "monthly_tss": 1600.0,
            "trend_7d": "stable",
            "trend_30d": "stable",
            "risk_indicators": ["string-item", extra],
            "recommendation": "",
        }
        state = repo._from_fitness_row(row)
        assert state.fatigue_score == 0.5
        assert state.risk_level == "high"
        assert state.risk_indicators == ["string-item", extra]

    def test_row_with_string_risk_indicators(self):
        repo = AthleteStateRepository()
        extra = __import__("json").dumps({"readiness": 40.0, "acwr": 1.5})
        row = {
            "athlete_id": 4,
            "computed_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            "atl": 55.0,
            "ctl": 65.0,
            "tsb": -10.0,
            "fitness": 65.0,
            "fatigue": 55.0,
            "form": -10.0,
            "recovery_hours_needed": 36.0,
            "weekly_tss": 600.0,
            "monthly_tss": 2400.0,
            "trend_7d": "declining",
            "trend_30d": "declining",
            "risk_indicators": extra,
            "recommendation": "Take a rest day",
        }
        state = repo._from_fitness_row(row)
        assert state.readiness == 40.0
        assert state.acwr == 1.5

    def test_row_with_malformed_json_in_indicators(self):
        repo = AthleteStateRepository()
        row = {
            "athlete_id": 5,
            "computed_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            "atl": 40.0,
            "ctl": 70.0,
            "tsb": 15.0,
            "fitness": 70.0,
            "fatigue": 40.0,
            "form": 15.0,
            "recovery_hours_needed": 0.0,
            "weekly_tss": 300.0,
            "monthly_tss": 1200.0,
            "trend_7d": "improving",
            "trend_30d": "improving",
            "risk_indicators": ["not-valid-json"],
            "recommendation": "",
        }
        state = repo._from_fitness_row(row)
        assert state.fatigue_score == 0.0
        assert state.readiness == 100.0


class TestAsyncWrappers:
    @pytest.mark.asyncio
    async def test_save_calls_fitness_repo(self):
        repo = AthleteStateRepository()
        state = _make_state()
        fake_result = AsyncMock(return_value=42)
        repo._fitness_repo = AsyncMock()
        repo._fitness_repo.save = fake_result
        result = await repo.save(state, tenant_id=1)
        assert result == 42
        fake_result.assert_called_once()
        call_args = fake_result.call_args[0]
        assert call_args[0]["athlete_id"] == 1

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_when_no_row(self):
        repo = AthleteStateRepository()
        repo._fitness_repo = AsyncMock()
        repo._fitness_repo.get_latest = AsyncMock(return_value=None)
        result = await repo.get_latest(1, tenant_id=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_returns_state(self):
        repo = AthleteStateRepository()
        row = {
            "athlete_id": 1,
            "computed_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            "atl": 45.0,
            "ctl": 80.0,
            "tsb": 10.0,
            "fitness": 80.0,
            "fatigue": 45.0,
            "form": 10.0,
            "recovery_hours_needed": 12.0,
            "weekly_tss": 450.0,
            "monthly_tss": 1800.0,
            "trend_7d": "stable",
            "trend_30d": "stable",
            "risk_indicators": [],
            "recommendation": "",
        }
        repo._fitness_repo = AsyncMock()
        repo._fitness_repo.get_latest = AsyncMock(return_value=row)
        result = await repo.get_latest(1, tenant_id=0)
        assert result is not None
        assert result.athlete_id == 1
        assert result.acwr == 1.0

    @pytest.mark.asyncio
    async def test_get_history_maps_rows(self):
        repo = AthleteStateRepository()
        rows = [
            {
                "athlete_id": 1,
                "computed_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
                "atl": 45.0,
                "ctl": 80.0,
                "tsb": 10.0,
                "fitness": 80.0,
                "fatigue": 45.0,
                "form": 10.0,
                "recovery_hours_needed": 12.0,
                "weekly_tss": 450.0,
                "monthly_tss": 1800.0,
                "trend_7d": "stable",
                "trend_30d": "stable",
                "risk_indicators": [],
                "recommendation": "",
            },
            {
                "athlete_id": 1,
                "computed_at": datetime(2025, 1, 14, 10, 0, 0, tzinfo=UTC),
                "atl": 44.0,
                "ctl": 79.0,
                "tsb": 11.0,
                "fitness": 79.0,
                "fatigue": 44.0,
                "form": 11.0,
                "recovery_hours_needed": 10.0,
                "weekly_tss": 400.0,
                "monthly_tss": 1700.0,
                "trend_7d": "stable",
                "trend_30d": "stable",
                "risk_indicators": [],
                "recommendation": "",
            },
        ]
        repo._fitness_repo = AsyncMock()
        repo._fitness_repo.get_history = AsyncMock(return_value=rows)
        result = await repo.get_history(1, days=7, tenant_id=0)
        assert len(result) == 2
        assert result[0].atl == 45.0
        assert result[1].atl == 44.0
