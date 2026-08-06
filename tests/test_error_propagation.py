"""Tests for analytics error propagation module."""

from __future__ import annotations

import math

import pytest

from bike_analyzer.backend.analytics.error_propagation import (
    ErrorValue,
    combine_errors_quadrature,
    compute_coverage,
    conservative_default,
    coverage_weight,
    cross_source_correction,
    cross_validate_gps,
    elastic_missing_data_weight,
    is_trend_certain,
    propagate_division,
    propagate_multiplication,
)


class TestErrorValue:
    def test_total_error_quadrature(self):
        ev = ErrorValue(value=10.0, stat_error=3.0, resolution_error=4.0)
        assert ev.total_error == 5.0

    def test_margin_pct(self):
        ev = ErrorValue(value=100.0, stat_error=5.0, resolution_error=0.0)
        assert ev.margin_pct == 5.0

    def test_lower_and_upper_bound(self):
        ev = ErrorValue(value=10.0, stat_error=1.0, resolution_error=0.0)
        assert ev.lower_bound == 9.0
        assert ev.upper_bound == 11.0

    def test_zero_value_margin_pct(self):
        ev = ErrorValue(value=0.0, stat_error=5.0)
        assert ev.margin_pct == 0.0

    def test_to_dict_rounds(self):
        ev = ErrorValue(value=1.23456, stat_error=0.12345, resolution_error=0.2, coverage=0.8)
        d = ev.to_dict()
        assert d["value"] == 1.2346
        assert d["total_error"] == round(math.sqrt(0.12345**2 + 0.2**2), 4)
        assert d["margin_pct"] == round(d["total_error"] / 1.23456 * 100, 2)


class TestCombineErrorsQuadrature:
    def test_single_error(self):
        assert combine_errors_quadrature([3.0]) == 3.0

    def test_multiple_errors(self):
        assert combine_errors_quadrature([3.0, 4.0]) == 5.0

    def test_empty_errors(self):
        assert combine_errors_quadrature([]) == 0.0


class TestPropagateMultiplication:
    def test_basic(self):
        ev = propagate_multiplication(10.0, 1.0, 5.0, 0.5)
        assert ev.value == 50.0
        assert ev.stat_error == pytest.approx(7.0710678118654755)

    def test_zero_value(self):
        ev = propagate_multiplication(0.0, 1.0, 5.0, 0.5)
        assert ev.value == 0.0
        assert ev.stat_error == pytest.approx(1.118033988749895)


class TestPropagateDivision:
    def test_basic(self):
        ev = propagate_division(10.0, 1.0, 5.0, 0.5)
        assert ev.value == 2.0
        assert ev.stat_error == pytest.approx(0.282842712474619)

    def test_zero_denominator(self):
        ev = propagate_division(10.0, 1.0, 0.0, 0.5)
        assert ev.value == 0.0
        assert ev.stat_error == pytest.approx(1.118033988749895)


class TestIsTrendCertain:
    def test_certain_positive(self):
        ev = ErrorValue(value=10.0, stat_error=1.0, resolution_error=0.0)
        assert is_trend_certain(ev) is True

    def test_certain_negative(self):
        ev = ErrorValue(value=-10.0, stat_error=1.0, resolution_error=0.0)
        assert is_trend_certain(ev) is True

    def test_uncertain_crosses_zero(self):
        ev = ErrorValue(value=1.0, stat_error=2.0, resolution_error=0.0)
        assert is_trend_certain(ev) is False

    def test_certain_near_zero(self):
        ev = ErrorValue(value=0.1, stat_error=0.05, resolution_error=0.0)
        assert is_trend_certain(ev) is True


class TestComputeCoverage:
    def test_full_coverage(self):
        assert compute_coverage(10, 10) == 1.0

    def test_partial_coverage(self):
        assert compute_coverage(5, 10) == 0.5

    def test_zero_total(self):
        assert compute_coverage(0, 0) == 0.0


class TestCoverageWeight:
    def test_above_threshold(self):
        assert coverage_weight(0.8, 0.5) == 1.0

    def test_below_threshold(self):
        assert coverage_weight(0.25, 0.5) == 0.5

    def test_zero_coverage(self):
        assert coverage_weight(0.0, 0.5) == 0.0


class TestElasticMissingDataWeight:
    def test_mostly_reliable(self):
        assert elastic_missing_data_weight(90, 100) == pytest.approx(0.1)

    def test_half_reliable(self):
        assert elastic_missing_data_weight(50, 100) == pytest.approx(0.6)

    def test_few_reliable(self):
        assert elastic_missing_data_weight(10, 100) == 1.0

    def test_zero_total(self):
        assert elastic_missing_data_weight(0, 0) == 0.0


class TestConservativeDefault:
    def test_no_signal(self):
        assert conservative_default(False) == 0.0

    def test_has_signal(self):
        assert conservative_default(True) == 1.0


class TestCrossSourceCorrection:
    def test_single_secondary(self):
        ev = cross_source_correction(10.0, [12.0])
        assert ev.value == pytest.approx(11.0)
        assert ev.stat_error == pytest.approx(1.0)

    def test_no_secondary(self):
        ev = cross_source_correction(10.0, [])
        assert ev.value == 10.0
        assert ev.stat_error == 0.0


class TestCrossValidateGps:
    def test_matching_sources(self):
        primary = [
            {"timestamp": "2026-01-01T00:00:00", "lat": 45.0, "lon": 7.0},
            {"timestamp": "2026-01-01T00:00:01", "lat": 45.0001, "lon": 7.0001},
        ]
        secondary = [
            {"timestamp": "2026-01-01T00:00:00", "lat": 45.0, "lon": 7.0},
            {"timestamp": "2026-01-01T00:00:01", "lat": 45.0001, "lon": 7.0001},
        ]
        result = cross_validate_gps(primary, secondary, max_divergence_m=5.0)
        assert result["match"] is True
        assert result["stat_error_adjustment"] == 0.8
        assert result["coverage"] == 1.0

    def test_diverging_sources(self):
        primary = [
            {"timestamp": "2026-01-01T00:00:00", "lat": 45.0, "lon": 7.0},
        ]
        secondary = [
            {"timestamp": "2026-01-01T00:00:00", "lat": 45.01, "lon": 7.01},
        ]
        result = cross_validate_gps(primary, secondary, max_divergence_m=5.0)
        assert result["match"] is False
        assert result["stat_error_adjustment"] > 1.0

    def test_empty_inputs(self):
        result = cross_validate_gps([], [])
        assert result["match"] is True
        assert result["coverage"] == 0.0
