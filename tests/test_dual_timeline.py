"""Tests for the dual_timeline (TempoTrack) module."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from itertools import combinations

import numpy as np
import pytest

utc = timezone.utc

from bike_analyzer.backend.analytics.dual_timeline import (
    ClockTrack,
    DataPoint,
    PhiConfig,
    SignalKind,
    SyncIndex,
    Track,
    aggregate_events,
    apply_gap_policy,
    build_phase_track,
    build_sync_index,
    classify_gap,
    composite_score,
    compute_drift,
    coverage_fraction,
    estimate_tau_from_response,
    instantaneous_tau,
    resample_continuous,
    update_phase,
    velocity,
    velocity_correlation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(seconds_offset: float) -> datetime:
    """Return a naive UTC datetime offset from a fixed origin."""
    return datetime(2026, 1, 1, 8, 0, 0) + timedelta(seconds=seconds_offset)


def _dp(seconds_offset: float, value: float | None, metric: str = "weight_kg",
        kind: SignalKind = SignalKind.CONTINUOUS) -> DataPoint:
    return DataPoint(
        timestamp=_ts(seconds_offset),
        source="test",
        metric=metric,
        value=value,
        unit="kg" if metric == "weight_kg" else "kcal",
        kind=kind,
        confidence=1.0,
    )


# ---------------------------------------------------------------------------
# DataPoint / Track / SignalKind
# ---------------------------------------------------------------------------

class TestDataPoint:
    def test_creation(self):
        dp = _dp(0, 70.5)
        assert dp.value == 70.5
        assert dp.kind == SignalKind.CONTINUOUS
        assert dp.is_interpolated is False

    def test_none_value(self):
        dp = _dp(0, None)
        assert dp.value is None

    def test_signal_kind_values(self):
        assert SignalKind.CONTINUOUS.value == "continuous"
        assert SignalKind.EVENT.value == "event"
        assert SignalKind.RATE.value == "rate"


class TestTrack:
    def test_sorted(self):
        points = [
            _dp(86400, 71.0),
            _dp(0, 70.0),
            _dp(43200, 70.5),
        ]
        t = Track(metric="weight_kg", kind=SignalKind.CONTINUOUS, points=points)
        sorted_pts = t.sorted()
        assert sorted_pts[0].value == 70.0
        assert sorted_pts[-1].value == 71.0

    def test_count(self):
        points = [_dp(i * 86400, 70.0 + i) for i in range(5)]
        t = Track(metric="weight_kg", kind=SignalKind.CONTINUOUS, points=points)
        assert t.count() == 5


# ---------------------------------------------------------------------------
# Gap policy
# ---------------------------------------------------------------------------

class TestGapPolicy:
    def test_continuous_short_gap(self):
        policy = classify_gap(SignalKind.CONTINUOUS, 86400.0)  # 1 day
        assert policy == "interpolate"

    def test_continuous_long_gap(self):
        policy = classify_gap(SignalKind.CONTINUOUS, 4 * 86400.0)  # 4 days
        assert policy == "null"

    def test_event_never_interpolated(self):
        policy = classify_gap(SignalKind.EVENT, 3600.0)
        assert policy == "aggregate"

    def test_rate_short_gap(self):
        policy = classify_gap(SignalKind.RATE, 86400.0)
        assert policy == "interpolate"

    def test_rate_long_gap(self):
        policy = classify_gap(SignalKind.RATE, 8 * 86400.0)
        assert policy == "null"

    def test_apply_gap_policy_marks_interpolated(self):
        points = [
            _dp(0, 70.0),
            _dp(86400, 70.5),
            _dp(2 * 86400, 71.0),
        ]
        result = apply_gap_policy(points)
        assert result[1].is_interpolated is True
        assert result[1].confidence < 1.0

    def test_apply_gap_policy_preserves_none(self):
        points = [
            _dp(0, 70.0),
            _dp(86400, None),
            _dp(2 * 86400, 71.0),
        ]
        result = apply_gap_policy(points)
        assert result[1].value is None


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------

class TestResampleContinuous:
    def test_basic_resample(self):
        points = [_dp(i * 86400, 70.0 + i * 0.5) for i in range(5)]
        ts, vals, conf = resample_continuous(points, grid_spacing="1D")
        assert len(ts) == 5
        assert len(vals) == 5
        assert len(conf) == 5
        assert all(c > 0 for c in conf)

    def test_time_weighted_interpolation(self):
        points = [
            _dp(0, 70.0),
            _dp(2 * 86400, 69.0),
            _dp(12 * 86400, 68.0),
        ]
        ts, vals, conf = resample_continuous(points, grid_spacing="1D")
        day1 = datetime(2026, 1, 2, 8, 0, 0)
        day1_idx = next((i for i, t in enumerate(ts) if t == day1), None)
        assert day1_idx is not None
        day1_val = vals[day1_idx]
        assert 69.0 < day1_val < 70.0

    def test_empty_input(self):
        ts, vals, conf = resample_continuous([])
        assert ts == []
        assert vals == []
        assert conf == []

    def test_none_values_break_chain_large_gap(self):
        points = [
            _dp(0, 70.0),
            _dp(86400, None),
            _dp(3 * 86400, None),
            _dp(6 * 86400, 71.0),
        ]
        ts, vals, conf = resample_continuous(points, grid_spacing="1D")
        day3 = datetime(2026, 1, 4, 8, 0, 0)
        day3_idx = next((i for i, t in enumerate(ts) if t == day3), None)
        assert day3_idx is not None
        assert vals[day3_idx] is None

    def test_none_values_small_gap_interpolated(self):
        # 2-day gap is within 3-day threshold -> should be interpolated
        points = [
            _dp(0, 70.0),
            _dp(86400, None),
            _dp(2 * 86400, 72.0),
        ]
        ts, vals, conf = resample_continuous(points, grid_spacing="1D")
        # The None at day 1 should be interpolated since gap is small
        assert vals[1] is not None

    def test_confidence_at_measured_point(self):
        points = [_dp(i * 86400, 70.0 + i) for i in range(3)]
        ts, vals, conf = resample_continuous(points, grid_spacing="1D")
        # Points at original timestamps should have confidence 1.0
        assert conf[0] == 1.0
        assert conf[-1] == 1.0

    def test_single_point(self):
        points = [_dp(0, 70.0)]
        ts, vals, conf = resample_continuous(points, grid_spacing="1D")
        assert len(ts) == 1
        assert vals[0] == 70.0


class TestAggregateEvents:
    def test_basic_count(self):
        points = [
            DataPoint(
                timestamp=_ts(0),
                source="test",
                metric="meal",
                value=1.0,
                unit="event",
                kind=SignalKind.EVENT,
            ),
            DataPoint(
                timestamp=_ts(43200),
                source="test",
                metric="meal",
                value=1.0,
                unit="event",
                kind=SignalKind.EVENT,
            ),
            DataPoint(
                timestamp=_ts(90000),
                source="test",
                metric="meal",
                value=1.0,
                unit="event",
                kind=SignalKind.EVENT,
            ),
        ]
        starts, counts, conf = aggregate_events(points, window="1D")
        assert counts[0] == 2.0
        assert counts[1] == 1.0


# ---------------------------------------------------------------------------
# Phase clock
# ---------------------------------------------------------------------------

class TestUpdatePhase:
    def test_no_stimulus_no_change(self):
        result = update_phase(phi_prev=5.0, delta_t=86400.0, tau=604800.0, stimulus=None)
        assert result == 5.0

    def test_approach_stimulus(self):
        phi = update_phase(phi_prev=0.0, delta_t=86400.0, tau=86400.0, stimulus=10.0)
        alpha = 1.0 - math.exp(-1.0)
        expected = alpha * 10.0
        assert abs(phi - expected) < 1e-6

    def test_fast_tau_chases_quickly(self):
        phi_slow = update_phase(0.0, 86400.0, 604800.0, 100.0)
        phi_fast = update_phase(0.0, 86400.0, 86400.0, 100.0)
        assert phi_fast > phi_slow

    def test_slow_tau_lags(self):
        phi_slow = update_phase(0.0, 86400.0, 604800.0, 100.0)
        phi_fast = update_phase(0.0, 86400.0, 86400.0, 100.0)
        assert phi_slow < phi_fast

    def test_nan_stimulus(self):
        result = update_phase(phi_prev=5.0, delta_t=86400.0, tau=604800.0, stimulus=float("nan"))
        assert result == 5.0


class TestBuildPhaseTrack:
    def test_basic_track(self):
        t_real = [_ts(i * 86400) for i in range(5)]
        stimulus = [70.0, 70.5, 71.0, 71.5, 72.0]
        track = build_phase_track(t_real, stimulus)
        assert len(track.phi) == 5
        assert len(track.alpha) == 5
        assert len(track.tau) == 5
        assert track.phi[0] == 0.0
        assert track.phi[-1] > track.phi[0]

    def test_phi_monotone(self):
        t_real = [_ts(i * 86400) for i in range(10)]
        stimulus = [70.0 + i * 0.1 for i in range(10)]
        track = build_phase_track(t_real, stimulus)
        for i in range(1, len(track.phi)):
            assert track.phi[i] >= track.phi[i - 1] - 1e-9

    def test_none_stimulus_pauses_phi(self):
        t_real = [_ts(i * 86400) for i in range(5)]
        stimulus = [70.0, None, 72.0, None, 74.0]
        track = build_phase_track(t_real, stimulus)
        assert all(math.isfinite(p) for p in track.phi)

    def test_empty_input(self):
        track = build_phase_track([], [])
        assert track.phi == []
        assert track.t_real == []

    def test_custom_tau(self):
        t_real = [_ts(i * 86400) for i in range(5)]
        stimulus = [70.0, 70.5, 71.0, 71.5, 72.0]
        tau_values = [86400.0] * 5
        track = build_phase_track(t_real, stimulus, tau_values=tau_values)
        assert all(abs(t - 86400.0) < 1e-6 for t in track.tau)

    def test_confidence_drops_on_none(self):
        t_real = [_ts(0), _ts(86400), _ts(2 * 86400)]
        stimulus = [70.0, None, 72.0]
        track = build_phase_track(t_real, stimulus)
        assert track.confidence[1] < track.confidence[0]


class TestVelocity:
    def test_basic(self):
        t_real = [_ts(i * 86400) for i in range(3)]
        phi = [0.0, 10.0, 25.0]
        track = ClockTrack(
            subsystem="test", t_real=t_real, phi=phi,
            alpha=[0.0, 0.5, 0.7], tau=[604800.0, 604800.0, 604800.0],
            confidence=[1.0, 1.0, 1.0],
        )
        v = velocity(track)
        assert len(v) == 2
        assert v[0] == pytest.approx(10.0 / 86400.0, rel=1e-5)
        assert v[1] == pytest.approx(15.0 / 86400.0, rel=1e-5)

    def test_empty(self):
        track = ClockTrack(
            subsystem="test", t_real=[], phi=[], alpha=[], tau=[], confidence=[],
        )
        assert velocity(track) == []


# ---------------------------------------------------------------------------
# Tau estimation
# ---------------------------------------------------------------------------

class TestTauEstimation:
    def test_curve_fit(self):
        t_days = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        tau_true = 3.5
        amp_true = 5.0
        response = [amp_true * (1.0 - math.exp(-t / tau_true)) for t in t_days]
        result = estimate_tau_from_response(t_days, response, initial_guess=(3.0, 4.0))
        assert result is not None
        tau_est, amp_est = result
        assert abs(tau_est - tau_true) < 0.5
        assert abs(amp_est - amp_true) < 0.5

    def test_insufficient_data(self):
        result = estimate_tau_from_response([0.0, 1.0], [0.0, 1.0])
        assert result is None

    def test_instantaneous_tau_baseline(self):
        tau = instantaneous_tau(tau_baseline=7.0)
        assert abs(tau - 7.0) < 1e-6

    def test_instantaneous_tau_stress(self):
        tau = instantaneous_tau(tau_baseline=7.0, stress_score=1.0)
        assert tau < 7.0

    def test_instantaneous_tau_sick(self):
        tau = instantaneous_tau(tau_baseline=7.0, is_sick=True)
        assert tau < 7.0

    def test_instantaneous_tau_combined(self):
        tau = instantaneous_tau(tau_baseline=7.0, stress_score=0.5, sleep_debt_h=2.0)
        assert tau < 7.0


# ---------------------------------------------------------------------------
# Sync / drift
# ---------------------------------------------------------------------------

class TestSyncDrift:
    def _make_track(self, name: str, phi_values: list[float]) -> ClockTrack:
        n = len(phi_values)
        t_real = [_ts(i * 86400) for i in range(n)]
        return ClockTrack(
            subsystem=name,
            t_real=t_real,
            phi=phi_values,
            alpha=[0.0] * n,
            tau=[604800.0] * n,
            confidence=[1.0] * n,
        )

    def test_drift_identical_tracks(self):
        a = self._make_track("metabolic", [0.0, 5.0, 10.0])
        b = self._make_track("stress", [0.0, 5.0, 10.0])
        drift = compute_drift(a, b)
        assert all(abs(d) < 1e-9 for d in drift)

    def test_drift_divergent(self):
        a = self._make_track("metabolic", [0.0, 10.0, 20.0])
        b = self._make_track("stress", [0.0, 2.0, 4.0])
        drift = compute_drift(a, b)
        assert drift[-1] > 0

    def test_velocity_correlation_identical(self):
        # Use non-constant velocities to get meaningful correlation
        a = self._make_track("a", [0.0, 3.0, 8.0])
        b = self._make_track("b", [0.0, 3.0, 8.0])
        corr = velocity_correlation(a, b)
        assert abs(corr - 1.0) < 0.01

    def test_velocity_correlation_opposite(self):
        a = self._make_track("a", [0.0, 3.0, 8.0])
        b = self._make_track("b", [0.0, -3.0, -8.0])
        corr = velocity_correlation(a, b)
        assert corr < -0.9

    def test_velocity_correlation_constant_identical(self):
        a = self._make_track("a", [0.0, 5.0, 10.0])
        b = self._make_track("b", [0.0, 5.0, 10.0])
        corr = velocity_correlation(a, b)
        assert abs(corr - 1.0) < 0.01

    def test_velocity_correlation_constant_opposite(self):
        a = self._make_track("a", [0.0, 10.0, 20.0])
        b = self._make_track("b", [0.0, -10.0, -20.0])
        corr = velocity_correlation(a, b)
        assert corr < -0.9

    def test_build_sync_index(self):
        a = self._make_track("metabolic", [0.0, 5.0, 10.0, 15.0, 20.0])
        b = self._make_track("stress", [0.0, 2.0, 4.0, 6.0, 8.0])
        idx = build_sync_index(a, b)
        assert isinstance(idx, SyncIndex)
        assert idx.subsystem_a == "metabolic"
        assert idx.subsystem_b == "stress"
        assert len(idx.drift) == 5
        assert idx.computed_at is not None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class TestScoring:
    def test_composite_score_all_present(self):
        available = {"weight": 70.0, "hr": 60.0, "sleep": 7.5}
        weights = {"weight": 1.0, "hr": 0.5, "sleep": 1.0}
        score, cov = composite_score(available, weights)
        assert cov == pytest.approx(1.0)
        assert score is not None

    def test_composite_score_partial(self):
        available = {"weight": 70.0, "sleep": 7.5}
        weights = {"weight": 1.0, "hr": 0.5, "sleep": 1.0}
        score, cov = composite_score(available, weights)
        present_weight = 1.0 + 1.0
        total_weight = 1.0 + 0.5 + 1.0
        assert cov == pytest.approx(present_weight / total_weight)
        assert score is not None

    def test_composite_score_none_missing(self):
        available = {"weight": None}
        weights = {"weight": 1.0, "hr": 0.5}
        score, cov = composite_score(available, weights)
        assert cov == 0.0
        assert score is None

    def test_composite_score_empty(self):
        score, cov = composite_score({}, {"weight": 1.0})
        assert cov == 0.0
        assert score is None

    def test_coverage_fraction(self):
        available = {"weight": 70.0}
        weights = {"weight": 1.0, "hr": 0.5}
        cov = coverage_fraction(available, weights)
        assert cov == pytest.approx(1.0 / 1.5, rel=1e-3)


# ---------------------------------------------------------------------------
# End-to-end: two tracks from raw DataPoints
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_dual_track_workflow(self):
        weight_pts = [_dp(i * 86400, 70.0 + 0.05 * i) for i in range(14)]
        load_pts = [
            _dp(0, 100.0, metric="tss", kind=SignalKind.CONTINUOUS),
            _dp(2 * 86400, 150.0, metric="tss", kind=SignalKind.CONTINUOUS),
            _dp(3 * 86400, 80.0, metric="tss", kind=SignalKind.CONTINUOUS),
            _dp(5 * 86400, 120.0, metric="tss", kind=SignalKind.CONTINUOUS),
            _dp(7 * 86400, 60.0, metric="tss", kind=SignalKind.CONTINUOUS),
            _dp(10 * 86400, 130.0, metric="tss", kind=SignalKind.CONTINUOUS),
            _dp(12 * 86400, 70.0, metric="tss", kind=SignalKind.CONTINUOUS),
        ]

        w_ts, w_vals, w_conf = resample_continuous(weight_pts, grid_spacing="1D")
        l_ts, l_vals, l_conf = resample_continuous(load_pts, grid_spacing="1D")

        assert len(w_ts) == 14

        w_stimulus = [v if c > 0.1 else None for v, c in zip(w_vals, w_conf)]
        l_stimulus = [v if c > 0.1 else None for v, c in zip(l_vals, l_conf)]

        weight_clock = build_phase_track(w_ts, w_stimulus)
        load_clock = build_phase_track(l_ts, l_stimulus)
        load_clock.subsystem = "training_load"

        assert len(weight_clock.phi) > 0
        assert len(load_clock.phi) > 0

        idx = build_sync_index(weight_clock, load_clock)
        assert isinstance(idx, SyncIndex)
        assert idx.confidence >= 0.0
