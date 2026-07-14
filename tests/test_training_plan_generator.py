"""Tests for training plan generator."""

from __future__ import annotations

from datetime import datetime

import pytest

from bike_analyzer.backend.analytics.training_plan_generator import (
    WorkoutDay,
    _plan_summary,
    _weekday_name,
)


class TestWeekdayName:
    def test_monday(self):
        dt = datetime(2024, 6, 10)
        assert _weekday_name(dt) == "Monday"

    def test_sunday(self):
        dt = datetime(2024, 6, 16)
        assert _weekday_name(dt) == "Sunday"


class TestPlanSummary:
    def test_empty_rides(self):
        from bike_analyzer.backend.models.models import AthleteProfile
        athlete = AthleteProfile()
        summary = _plan_summary(athlete, [])
        assert summary["total_rides"] == 0
        assert summary["avg_distance_km"] == 0

    def test_with_rides(self):
        from bike_analyzer.backend.models.models import AthleteProfile, Ride
        athlete = AthleteProfile(experience_level="Intermediate")
        rides = [Ride(distance_km=30.0, duration_minutes=60.0) for _ in range(5)]
        summary = _plan_summary(athlete, rides)
        assert summary["total_rides"] == 5
        assert summary["recent_rides"] == 4
        assert summary["avg_distance_km"] == 30.0
