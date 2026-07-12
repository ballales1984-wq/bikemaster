"""Tests for the core physics engine (point-wise models)."""

import pytest
from datetime import datetime

from bike_analyzer.core.models import GPSPoint
from bike_analyzer.core.physics import (
    RiderBikeParams,
    cycling_forces,
    grade_between,
    instantaneous_power,
    required_speed_for_power,
)


def _pt(lat=45.0, lon=9.0, alt=None, ts=None, **kw):
    return GPSPoint(lat=lat, lon=lon, altitude=alt, timestamp=ts or datetime(2024, 6, 15), **kw)


class TestGradeBetween:
    def test_flat(self):
        p1 = _pt(alt=100.0)
        p2 = _pt(lat=45.001, alt=100.0)
        assert grade_between(p1, p2) == 0.0

    def test_uphill(self):
        p1 = _pt(alt=100.0)
        p2 = _pt(lat=45.001, alt=110.0)
        assert grade_between(p1, p2) > 0.0

    def test_downhill(self):
        p1 = _pt(alt=110.0)
        p2 = _pt(lat=45.001, alt=100.0)
        assert grade_between(p1, p2) < 0.0

    def test_missing_altitude(self):
        p1 = _pt(alt=None)
        p2 = _pt(alt=110.0)
        assert grade_between(p1, p2) == 0.0

    def test_negligible_distance(self):
        p1 = _pt(alt=100.0)
        p2 = _pt(alt=110.0)
        assert grade_between(p1, p2) == 0.0


class TestInstantaneousPower:
    def test_zero_speed(self):
        assert instantaneous_power(0.0, 0.0) == 0.0

    def test_positive_power_on_flat(self):
        p = instantaneous_power(8.0, 0.0)
        assert p > 0.0

    def test_headwind_increases_power(self):
        calm = instantaneous_power(8.0, 0.0, wind_ms=0.0)
        wind = instantaneous_power(8.0, 0.0, wind_ms=5.0)
        assert wind > calm

    def test_uphill_costs_more(self):
        flat = instantaneous_power(8.0, 0.0)
        climb = instantaneous_power(8.0, 0.08)
        assert climb > flat

    def test_downhill_costs_less(self):
        flat = instantaneous_power(8.0, 0.0)
        descend = instantaneous_power(8.0, -0.08)
        assert descend < flat

    def test_consistent_with_calories_constants(self):
        # bike_mass=0 + flat + eta=1 must match calories_physics coefficients.
        params = RiderBikeParams(rider_mass_kg=70.0, bike_mass_kg=0.0, drivetrain_efficiency=1.0)
        p = instantaneous_power(10.0, 0.0, params)
        expected = (0.005 * 70.0 * 9.81 + 0.5 * 1.225 * 0.4 * 10.0**2) * 10.0
        assert p == pytest.approx(expected)


class TestRequiredSpeedForPower:
    def test_zero_target(self):
        assert required_speed_for_power(0.0, 0.0) == 0.0

    def test_round_trip_flat(self):
        target = 250.0
        v = required_speed_for_power(target, 0.0)
        assert instantaneous_power(v, 0.0) == pytest.approx(target, rel=1e-2)

    def test_round_trip_climb(self):
        target = 300.0
        v = required_speed_for_power(target, 0.06)
        assert instantaneous_power(v, 0.06) == pytest.approx(target, rel=1e-2)

    def test_higher_power_needs_higher_speed(self):
        v_low = required_speed_for_power(150.0, 0.0)
        v_high = required_speed_for_power(350.0, 0.0)
        assert v_high > v_low


class TestCyclingForces:
    def test_breakdown_is_positive_on_flat(self):
        f = cycling_forces(8.0, 78.0, 0.0, 0.005, 0.4)
        assert f["roll"] > 0
        assert f["grav"] == 0.0
        assert f["air"] > 0
        assert f["power_w"] > 0

    def test_power_equals_sum_times_velocity(self):
        f = cycling_forces(10.0, 78.0, 0.02, 0.005, 0.4)
        expected = (f["roll"] + f["grav"] + f["air"]) * 10.0
        assert f["power_w"] == pytest.approx(expected)

    def test_drivetrain_efficiency_divides_power(self):
        no_eff = cycling_forces(10.0, 78.0, 0.0, 0.005, 0.4, drivetrain_efficiency=1.0)["power_w"]
        with_eff = cycling_forces(10.0, 78.0, 0.0, 0.005, 0.4, drivetrain_efficiency=0.25)["power_w"]
        assert with_eff == pytest.approx(no_eff / 0.25)

    def test_matches_instantaneous_power(self):
        params = RiderBikeParams(rider_mass_kg=78.0, bike_mass_kg=0.0, cda=0.4, crr=0.005, drivetrain_efficiency=0.25)
        p = instantaneous_power(10.0, 0.02, params)
        f = cycling_forces(10.0, 78.0, 0.02, 0.005, 0.4, drivetrain_efficiency=0.25)["power_w"]
        assert p == pytest.approx(f)
