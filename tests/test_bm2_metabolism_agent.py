"""Tests for bm2.metabolism_agent."""

import pytest
from bike_analyzer.bm2.metabolism_agent import MetabolismAgent
from bike_analyzer.bm2.transformer import TransformerEngine


@pytest.fixture()
def agent():
    return MetabolismAgent(TransformerEngine())


def test_collect_profile_basic(agent):
    raw = {
        "weight": 70.0,
        "weight_unit": "kg",
        "height": 1.75,
        "height_unit": "m",
        "age": 30,
        "sex": "male",
        "bmr_formula": "mifflin",
        "activity_level": "moderate",
    }
    profile = agent.collect_profile(raw)
    assert profile.bmr_kcal > 0
    assert profile.tdee_kcal > 0
    assert profile.sex == "male"
    assert profile.age == 30


def test_collect_profile_with_fat_percentage(agent):
    raw = {
        "weight": 70.0,
        "weight_unit": "kg",
        "height": 1.75,
        "height_unit": "m",
        "age": 30,
        "sex": "female",
        "bmr_formula": "cunningham",
        "activity_level": "active",
        "fat_percentage": 18.5,
    }
    profile = agent.collect_profile(raw)
    assert profile.fat_percentage == 18.5
    assert profile.bmr_formula == "cunningham"


def test_collect_daily_summary_basic(agent):
    raw = {
        "athlete": {
            "weight": 70.0,
            "weight_unit": "kg",
            "height": 1.75,
            "height_unit": "m",
            "age": 30,
            "sex": "male",
            "bmr_formula": "mifflin",
            "activity_level": "moderate",
        },
        "intake_kcal": 2200.0,
        "carbs_g": 250.0,
        "protein_g": 120.0,
        "fat_g": 70.0,
        "fiber_g": 25.0,
        "water_ml": 2000.0,
    }
    summary = agent.collect_daily_summary(raw, date="2025-01-15")
    assert summary.date == "2025-01-15"
    assert summary.intake_kcal == 2200.0
    assert summary.carbs_g == 250.0
    assert summary.protein_g == 120.0
    assert summary.fat_g == 70.0
    assert summary.fiber_g == 25.0
    assert summary.water_ml == 2000.0


def test_collect_daily_summary_with_metabolic_profile(agent):
    raw = {
        "athlete": {
            "weight": 70.0,
            "weight_unit": "kg",
            "height": 1.75,
            "height_unit": "m",
            "age": 30,
            "sex": "male",
            "bmr_formula": "mifflin",
            "activity_level": "moderate",
        },
        "metabolic_profile": {
            "bmr_kcal": 1700.0,
            "tdee_kcal": 2600.0,
            "neat_kcal": 400.0,
            "eat_kcal": 500.0,
            "climb_bonus_kcal": 0.0,
            "sensor_bmr_conf": 0.8,
            "sensor_tdee_conf": 0.8,
            "activity_multiplier_w": 1.0,
            "neat_w": 1.0,
            "climb_bonus_w": 1.0,
            "n_calibrations": 0,
        },
    }
    summary = agent.collect_daily_summary(raw, date="2025-01-15")
    assert summary.metabolic_flexibility_score == 0.0


def test_from_ride_with_iso_timestamp(agent):
    ride = {
        "elevation_gain_m": 120.0,
        "gps_points": [
            {
                "timestamp": "2025-01-15T10:00:00+00:00",
                "lat": 45.0,
                "lon": 9.0,
                "altitude": 200.0,
                "speed": 5.0,
            }
        ],
        "calories": 600.0,
        "date": "2025-01-15",
    }
    athlete_raw = {
        "weight": 70.0,
        "weight_unit": "kg",
        "age": 30,
        "sex": "male",
        "bmr_formula": "mifflin",
        "activity_level": "moderate",
    }
    summary = agent.from_ride(ride, athlete_raw)
    assert summary.date == "2025-01-15"
    assert summary.rides_count == 1
    assert summary.elevation_gain_estimated_m == 120.0


def test_from_ride_with_integer_unix_timestamp(agent):
    ride = {
        "elevation_gain_m": 50.0,
        "gps_points": [
            {
                "timestamp": 1700000000,
                "lat": 45.0,
                "lon": 9.0,
                "altitude": 200.0,
                "speed": 5.0,
            }
        ],
        "calories": 400.0,
    }
    athlete_raw = {
        "weight": 70.0,
        "weight_unit": "kg",
        "age": 30,
        "sex": "male",
        "bmr_formula": "mifflin",
        "activity_level": "moderate",
    }
    summary = agent.from_ride(ride, athlete_raw)
    assert summary.date == "2023-11-14"


def test_from_ride_with_float_unix_timestamp(agent):
    ride = {
        "elevation_gain_m": 50.0,
        "gps_points": [
            {
                "timestamp": 1700000000.0,
                "lat": 45.0,
                "lon": 9.0,
                "altitude": 200.0,
                "speed": 5.0,
            }
        ],
        "calories": 400.0,
    }
    athlete_raw = {
        "weight": 70.0,
        "weight_unit": "kg",
        "age": 30,
        "sex": "male",
        "bmr_formula": "mifflin",
        "activity_level": "moderate",
    }
    summary = agent.from_ride(ride, athlete_raw)
    assert summary.date == "2023-11-14"


def test_from_ride_with_invalid_timestamp_fallback_to_date(agent):
    ride = {
        "elevation_gain_m": 50.0,
        "gps_points": [
            {
                "timestamp": "not-a-date",
                "lat": 45.0,
                "lon": 9.0,
                "altitude": 200.0,
                "speed": 5.0,
            }
        ],
        "calories": 400.0,
        "date": "2025-02-01",
    }
    athlete_raw = {
        "weight": 70.0,
        "weight_unit": "kg",
        "age": 30,
        "sex": "male",
        "bmr_formula": "mifflin",
        "activity_level": "moderate",
    }
    summary = agent.from_ride(ride, athlete_raw)
    assert summary.date == "2025-02-01"


def test_from_ride_without_gps_points_uses_points_key(agent):
    ride = {
        "elevation_gain_m": 50.0,
        "points": [
            {
                "timestamp": "2025-03-01T12:00:00+00:00",
                "lat": 45.0,
                "lon": 9.0,
            }
        ],
        "calories": 300.0,
    }
    athlete_raw = {
        "weight": 70.0,
        "weight_unit": "kg",
        "age": 30,
        "sex": "male",
        "bmr_formula": "mifflin",
        "activity_level": "moderate",
    }
    summary = agent.from_ride(ride, athlete_raw)
    assert summary.date == "2025-03-01"


def test_from_ride_with_no_points_or_gps_points(agent):
    ride = {
        "calories": 100.0,
        "date": "2025-04-01",
    }
    athlete_raw = {
        "weight": 70.0,
        "weight_unit": "kg",
        "age": 30,
        "sex": "male",
        "bmr_formula": "mifflin",
        "activity_level": "moderate",
    }
    summary = agent.from_ride(ride, athlete_raw)
    assert summary.date == "2025-04-01"
    assert summary.rides_count == 0
