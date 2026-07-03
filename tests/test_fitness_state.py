"""Tests for fitness_state module."""

from datetime import UTC, datetime

from bike_analyzer.core.fitness_state import FitnessStateVector, TrainingStressDay


class TestTrainingStressDay:
    def test_default(self):
        from datetime import date
        d = TrainingStressDay(date=date(2024, 6, 15))
        assert d.tss == 0.0
        assert d.atl == 0.0
        assert d.ctl == 0.0
        assert d.tsb == 0.0

    def test_with_values(self):
        from datetime import date
        d = TrainingStressDay(date=date(2024, 6, 15), tss=100.0, atl=80.0, ctl=90.0, tsb=10.0)
        assert d.tss == 100.0
        assert d.tsb == 10.0


class TestFitnessStateVector:
    def _make(self, **kwargs):
        defaults = dict(
            athlete_id=1,
            computed_at=datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC),
            atl=75.0, ctl=85.0, tsb=10.0,
            fitness=85.0, fatigue=75.0, form=10.0,
            recovery_hours_needed=12.0,
            weekly_tss=500.0, monthly_tss=2000.0,
            trend_7d="improving", trend_30d="stable",
        )
        defaults.update(kwargs)
        return FitnessStateVector(**defaults)

    def test_defaults(self):
        v = FitnessStateVector(athlete_id=1, computed_at=datetime.now(UTC))
        assert v.risk_indicators == []
        assert v.recommendation == ""
        assert v.trend_7d == "stable"

    def test_is_fresh(self):
        v = self._make(tsb=20.0)
        assert v.is_fresh is True

    def test_not_fresh(self):
        v = self._make(tsb=10.0)
        assert v.is_fresh is False

    def test_overtraining_risk(self):
        v = self._make(atl=120.0, ctl=85.0, tsb=-25.0)
        assert v.is_overtraining_risk is True

    def test_no_overtraining(self):
        v = self._make(atl=80.0, ctl=85.0, tsb=5.0)
        assert v.is_overtraining_risk is False

    def test_ready_for_hard_effort(self):
        v = self._make(tsb=10.0, atl=80.0, ctl=85.0)
        assert v.is_ready_for_hard_effort is True

    def test_not_ready_for_hard_effort(self):
        v = self._make(tsb=0.0, atl=95.0, ctl=85.0)
        assert v.is_ready_for_hard_effort is False

    def test_to_dict_keys(self):
        v = self._make()
        d = v.to_dict()
        assert d["athlete_id"] == 1
        assert "atl" in d
        assert "ctl" in d
        assert "tsb" in d
        assert "is_overtraining_risk" in d
        assert "is_fresh" in d
        assert "is_ready_for_hard_effort" in d

    def test_to_dict_rounding(self):
        v = self._make(atl=75.555, ctl=85.333)
        d = v.to_dict()
        assert d["atl"] == 75.6
        assert d["ctl"] == 85.3

    def test_to_dict_datetime(self):
        v = self._make()
        d = v.to_dict()
        assert "2024-06-15" in d["computed_at"]

    def test_to_dict_risk_indicators(self):
        v = self._make(risk_indicators=["high_fatigue", "low_form"])
        d = v.to_dict()
        assert d["risk_indicators"] == ["high_fatigue", "low_form"]

    def test_to_dict_recommendation(self):
        v = self._make(recommendation="Rest day")
        d = v.to_dict()
        assert d["recommendation"] == "Rest day"
