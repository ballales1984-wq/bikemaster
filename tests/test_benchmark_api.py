"""Test benchmark comparison API."""

import pytest
pytestmark = pytest.mark.slow

from bike_analyzer.backend.analytics.benchmark import (
    compare_athlete_to_benchmark,
    get_age_category,
    get_weight_category,
)
from bike_analyzer.backend.models.models import AthleteProfile


def test_compare_athlete_to_benchmark_beginner():
    athlete = AthleteProfile(name="Test", experience_level="Beginner")
    result = compare_athlete_to_benchmark(athlete, 50.0, 15.0, 2.0)
    assert "percentile_km" in result
    assert "percentile_speed" in result
    assert "overall_percentile" in result


def test_compare_athlete_to_benchmark_elite():
    athlete = AthleteProfile(name="Test", experience_level="Elite")
    result = compare_athlete_to_benchmark(athlete, 5000.0, 35.0, 20.0)
    assert result["overall_percentile"] >= 0


def test_get_age_category_under25():
    assert get_age_category(20) == "Under25"
    assert get_age_category(24) == "Under25"


def test_get_age_category_over55():
    assert get_age_category(60) == "Over55"
    assert get_age_category(70) == "Over55"


def test_get_weight_category_boundaries():
    assert get_weight_category(64) == "Lightweight"
    assert get_weight_category(65) == "Medium"
    assert get_weight_category(79) == "Medium"
    assert get_weight_category(80) == "Heavy"
