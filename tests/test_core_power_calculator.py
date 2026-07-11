"""Tests for core power calculator edge cases."""

from bike_analyzer.core.calculators.power import (
    intensity_factor,
    normalized_power_approx,
    training_stress_score,
)
from bike_analyzer.core.models import GPSPoint, Ride


def _ride(**kwargs):
    defaults = dict(  # noqa: C408
        id=1, athlete_id=1, date="2024-06-15",
        distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0,
        weight_kg=70.0, calories=600.0, heart_rate_avg=150.0,
        elevation_gain_m=200.0, gps_points=[],
    )
    defaults.update(kwargs)
    return Ride(**defaults)


class TestNormalizedPowerApprox:
    def test_no_data_returns_zero(self):
        r = _ride(gps_points=[], heart_rate_avg=None, avg_speed_kmh=None)
        assert normalized_power_approx(r) == 0.0

    def test_hr_speed_fallback(self):
        r = _ride(heart_rate_avg=160.0, avg_speed_kmh=28.0)
        np = normalized_power_approx(r)
        assert np > 0.0

    def test_high_hr_high_speed(self):
        r = _ride(heart_rate_avg=190.0, avg_speed_kmh=40.0)
        np = normalized_power_approx(r)
        assert np > 0.0

    def test_with_gps_power_data(self):
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp="2024-06-15T10:00:00+00:00", power=200.0),
            GPSPoint(lat=45.01, lon=9.01, timestamp="2024-06-15T10:01:00+00:00", power=210.0),
            GPSPoint(lat=45.02, lon=9.02, timestamp="2024-06-15T10:02:00+00:00", power=190.0),
        ]
        r = _ride(gps_points=points)
        np = normalized_power_approx(r)
        assert np >= 0.0

    def test_too_few_gps_power_points_falls_back(self):
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp="2024-06-15T10:00:00+00:00", power=200.0),
        ]
        r = _ride(gps_points=points, heart_rate_avg=150.0, avg_speed_kmh=25.0)
        np = normalized_power_approx(r)
        assert np > 0.0


class TestIntensityFactor:
    def test_basic(self):
        r = _ride(avg_speed_kmh=25.0, heart_rate_avg=150.0)
        if_ = intensity_factor(r, ftp=250.0)
        assert if_ >= 0.0

    def test_zero_ftp(self):
        r = _ride(avg_speed_kmh=25.0, heart_rate_avg=150.0)
        assert intensity_factor(r, ftp=0.0) == 0.0

    def test_high_intensity(self):
        r = _ride(avg_speed_kmh=40.0, heart_rate_avg=190.0)
        if_ = intensity_factor(r, ftp=250.0)
        assert 0.0 <= if_ <= 1.0


class TestTrainingStressScore:
    def test_zero_duration(self):
        r = _ride(duration_minutes=0.0)
        assert training_stress_score(r, ftp=250.0) == 0.0

    def test_basic(self):
        r = _ride(duration_minutes=60.0, avg_speed_kmh=25.0, heart_rate_avg=150.0)
        tss = training_stress_score(r, ftp=250.0)
        assert tss >= 0.0

    def test_capped_at_500(self):
        r = _ride(duration_minutes=300.0, avg_speed_kmh=50.0, heart_rate_avg=200.0)
        tss = training_stress_score(r, ftp=250.0)
        assert tss <= 500.0
