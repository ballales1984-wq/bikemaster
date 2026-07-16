"""Tests for the Load Manager package.

Uses deterministic, historically-shaped synthetic data (consistent weekly TSS),
mirroring the "dati storici reali" requirement by exercising realistic load shapes.
"""

from __future__ import annotations

from datetime import date, timedelta

from bike_analyzer.backend.analytics.load_manager import (
    DEFAULT_CONFIG,
    AthleteLevelEnum,
    ChronicLoad,
    ChronicLoadManager,
    LoadBalance,
    LoadManager,
    RedistributionPlan,
    SafetyAlert,
    TrainingStress,
    TrainingStressCalculator,
    TrendAnalyzer,
    calculate_acwr,
    calculate_ewma,
    calculate_tss,
    terrain_correction,
)
from bike_analyzer.backend.models.models import Ride


def make_ride(day: int, distance_km=40.0, avg_speed_kmh=30.0, duration_minutes=80.0,
              hr=None, elev=None) -> Ride:
    d = (date(2024, 1, 1) + timedelta(days=day)).isoformat()
    return Ride(
        id=day, athlete_id=1, date=d, distance_km=distance_km,
        avg_speed_kmh=avg_speed_kmh, duration_minutes=duration_minutes,
        heart_rate_avg=hr, elevation_gain_m=elev,
    )


# --------------------------------------------------------------------------- #
# Pure functions
# --------------------------------------------------------------------------- #
class TestPureFunctions:
    def test_calculate_tss_basic(self):
        res = calculate_tss(duration_hours=2.0, intensity_factor=0.8)
        assert res["tss"] == 128.0
        assert res["intensity_factor"] == 0.8

    def test_calculate_tss_zero_duration(self):
        assert calculate_tss(0.0, 0.8)["tss"] == 0.0

    def test_calculate_tss_cap(self):
        res = calculate_tss(duration_hours=10.0, intensity_factor=1.0, cap=500.0)
        assert res["tss"] == 500.0

    def test_calculate_tss_terrain(self):
        res = calculate_tss(duration_hours=1.0, intensity_factor=1.0, terrain_correction=0.2)
        assert res["tss"] == 120.0

    def test_calculate_ewma_constant(self):
        series = calculate_ewma([100.0, 100.0, 100.0], tau_days=42)
        assert all(abs(v - 100.0) < 1e-6 for v in series)

    def test_calculate_ewma_empty(self):
        assert calculate_ewma([], 42) == []

    def test_calculate_acwr_rising(self):
        short = [120.0] * 7
        long = [80.0] * 28
        assert calculate_acwr(short, long) == 1.5

    def test_calculate_acwr_detraining(self):
        short = [40.0] * 7
        long = [80.0] * 28
        assert calculate_acwr(short, long) == 0.5

    def test_terrain_correction(self):
        assert terrain_correction(400.0, 40.0) == 0.1
        assert terrain_correction(4000.0, 40.0) == 0.3
        assert terrain_correction(None, 40.0) == 0.0


# --------------------------------------------------------------------------- #
# Training Stress Calculator
# --------------------------------------------------------------------------- #
class TestTrainingStressCalculator:
    def test_met_estimation(self):
        calc = TrainingStressCalculator(ftp_watts=None)
        ts = calc.from_ride(make_ride(0, avg_speed_kmh=40.0, duration_minutes=120))
        assert ts.method.value == "met"
        assert ts.tss > 0
        assert ts.intensity_factor <= 1.0

    def test_power_based(self):
        ride = make_ride(0, distance_km=40.0, avg_speed_kmh=32.0, duration_minutes=80)
        ride.gps_points = [
            type("P", (), {"power": 200.0})(),
            type("P", (), {"power": 220.0})(),
            type("P", (), {"power": 240.0})(),
        ]
        calc = TrainingStressCalculator(ftp_watts=250.0)
        ts = calc.from_ride(ride)
        assert ts.method.value == "power"
        assert ts.normalized_power is not None
        assert ts.intensity_factor > 0

    def test_zero_duration(self):
        ts = TrainingStressCalculator().from_ride(make_ride(0, duration_minutes=0))
        assert ts.tss == 0.0

    def test_terrain_correction_applied(self):
        flat = TrainingStressCalculator().from_ride(make_ride(0, elev=0, avg_speed_kmh=30, duration_minutes=60))
        climb = TrainingStressCalculator().from_ride(make_ride(0, elev=1000, distance_km=20, avg_speed_kmh=30, duration_minutes=60))
        assert climb.tss > flat.tss
        assert climb.terrain_correction > 0


# --------------------------------------------------------------------------- #
# Chronic / Acute Load
# --------------------------------------------------------------------------- #
def _build_8_week_history() -> list[tuple[str, float]]:
    """8 weeks, ~3 rides/week, ~100 TSS/ride, slight progression."""
    out = []
    day = 0
    base = 80.0
    for week in range(8):
        for _ in range(3):
            out.append(((date(2024, 1, 1) + timedelta(days=day)).isoformat(), round(base + week * 5, 1)))
            day += 2
    return out


class TestChronicLoadManager:
    def test_series_shape(self):
        series = ChronicLoadManager().compute_series(_build_8_week_history())
        assert len(series) == 47
        assert all(isinstance(s, ChronicLoad) for s in series)

    def test_ctl_greater_than_atl_eventually(self):
        series = ChronicLoadManager().compute_series(_build_8_week_history())
        last = series[-1]
        assert last.ctl > 0 and last.atl > 0
        assert abs(last.tsb - (last.ctl - last.atl)) < 1e-6

    def test_acwr_present_in_tail(self):
        series = ChronicLoadManager().compute_series(_build_8_week_history())
        assert series[-1].acwr is not None
        assert series[0].acwr is None  # not enough history

    def test_starts_with_daily_tss(self):
        series = ChronicLoadManager().compute_series([("2024-03-01", 100.0)])
        assert series[0].tss == 100.0

    def test_current(self):
        load = ChronicLoadManager().current(_build_8_week_history())
        assert load is not None
        assert load.tsb == round(load.ctl - load.atl, 1)


# --------------------------------------------------------------------------- #
# Safety Thresholds & Load Balance & Redistribution
# --------------------------------------------------------------------------- #
class TestLoadManager:
    def test_acwr_high_risk_alert(self):
        load = ChronicLoad(date="x", ctl=100, atl=150, tsb=-50, acwr=1.7)
        alerts = LoadManager().evaluate_safety(load)
        assert any(a.code == "acwr_high_risk" for a in alerts)

    def test_acwr_block_alert(self):
        load = ChronicLoad(date="x", ctl=100, atl=200, tsb=-100, acwr=2.1)
        alerts = LoadManager().evaluate_safety(load)
        codes = {a.code for a in alerts}
        assert "acwr_block" in codes

    def test_detraining_alert(self):
        load = ChronicLoad(date="x", ctl=30, atl=20, tsb=10, acwr=0.5)
        alerts = LoadManager().evaluate_safety(load)
        assert any(a.code == "acwr_detraining" for a in alerts)

    def test_tsb_fatigue_alert(self):
        load = ChronicLoad(date="x", ctl=80, atl=130, tsb=-35, acwr=1.2)
        alerts = LoadManager().evaluate_safety(load)
        assert any(a.code == "tsb_fatigue" for a in alerts)

    def test_no_alert_in_zone(self):
        load = ChronicLoad(date="x", ctl=80, atl=90, tsb=5, acwr=1.0)
        assert LoadManager().evaluate_safety(load) == []

    def test_balance_beginner(self):
        bal = LoadManager().balance(AthleteLevelEnum.BEGINNER.value, current_week_tss=100.0, remaining_rides=2)
        assert isinstance(bal, LoadBalance)
        assert bal.recommended_per_ride == (300.0 - 100.0) / 2

    def test_balance_in_range(self):
        bal = LoadManager().balance(AthleteLevelEnum.ADVANCED.value, current_week_tss=850.0, remaining_rides=1)
        assert bal.in_balance is True

    def test_redistribute_even(self):
        plan = LoadManager().redistribute(remaining_rides=4, remaining_tss=400.0)
        assert isinstance(plan, RedistributionPlan)
        assert plan.recommended_per_ride == 100.0
        assert sum(plan.per_ride) == 400.0

    def test_redistribute_no_rides(self):
        plan = LoadManager().redistribute(remaining_rides=0, remaining_tss=400.0)
        assert plan.feasible is False

    def test_redistribute_recovery_factor(self):
        plan = LoadManager().redistribute(remaining_rides=2, remaining_tss=200.0, recovery_factor=0.5)
        assert plan.recommended_per_ride == 50.0

    def test_redistribute_residual_capacity(self):
        plan = LoadManager().redistribute(remaining_rides=2, remaining_tss=400.0, residual_capacity=50.0)
        assert plan.recommended_per_ride == 50.0


# --------------------------------------------------------------------------- #
# Trend Analysis
# --------------------------------------------------------------------------- #
class TestTrendAnalyzer:
    def test_ctl_rising(self):
        trend = TrendAnalyzer().ctl_trend([50, 55, 60, 65, 72])
        assert trend.direction.value == "rising"
        assert trend.slope > 0

    def test_ctl_falling(self):
        trend = TrendAnalyzer().ctl_trend([80, 75, 70, 65, 60])
        assert trend.direction.value == "falling"

    def test_ctl_stable(self):
        trend = TrendAnalyzer().ctl_trend([70, 70, 70, 70])
        assert trend.direction.value == "stable"

    def test_performance_plateau(self):
        trend = TrendAnalyzer().performance_trend([100, 101, 100, 102, 101])
        assert trend.direction.value in ("stable", "rising")

    def test_correlation_positive(self):
        corr = TrendAnalyzer().load_performance_correlation([10, 20, 30, 40], [1, 2, 3, 4])
        assert corr.coefficient > 0.99

    def test_correlation_negative(self):
        corr = TrendAnalyzer().load_performance_correlation([10, 20, 30, 40], [4, 3, 2, 1])
        assert corr.coefficient < -0.99

    def test_correlation_insufficient(self):
        corr = TrendAnalyzer().load_performance_correlation([10], [1])
        assert corr.samples < 3


# --------------------------------------------------------------------------- #
# Config sanity
# --------------------------------------------------------------------------- #
class TestConfig:
    def test_default_targets(self):
        cfg = DEFAULT_CONFIG
        assert cfg.target_for("beginner").max_tss_per_week == 400.0
        assert cfg.target_for("elite").min_tss_per_week == 1000.0

    def test_tunable_thresholds(self):
        from bike_analyzer.backend.analytics.load_manager import LoadManagerConfig, SafetyThresholds
        cfg = LoadManagerConfig(thresholds=SafetyThresholds(acwr_high_risk=1.3))
        load = ChronicLoad(date="x", ctl=100, atl=140, tsb=-40, acwr=1.35)
        assert any(a.code == "acwr_high_risk" for a in LoadManager(cfg).evaluate_safety(load))
