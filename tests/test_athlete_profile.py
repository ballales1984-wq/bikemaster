"""Test athlete profile API."""

from bike_analyzer.backend.db.database import (
    get_athlete,
    init_db,
    save_athlete,
    update_athlete,
)
from bike_analyzer.backend.models.models import AthleteProfile


def test_save_athlete_with_all_fields():
    init_db()
    athlete_id = save_athlete({
        "name": "Full Profile Athlete",
        "age": 35,
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "fat_percentage": 15.0,
        "years_active": 5,
        "weekly_sessions": 4,
        "monthly_hours": 20.0,
        "annual_hours": 240.0,
        "experience_level": "Intermediate",
        "goals": "Completo",
        "preferred_terrain": "Collina",
        "weekly_volume_km": 100.0,
        "best_segments": "Segmento A",
        "medical_notes": "Nessuna",
        "equipment": "Bici X"
    })
    assert athlete_id > 0


def test_update_athlete():
    init_db()
    athlete_id = save_athlete({"name": "Update Test", "age": 30})
    updated = update_athlete(athlete_id, {"name": "Updated Name", "age": 31})
    assert updated == True
    athlete = get_athlete(athlete_id)
    assert athlete["name"] == "Updated Name"
    assert athlete["age"] == 31


def test_get_athlete_not_found():
    athlete = get_athlete(99999)
    assert athlete is None


def test_athlete_profile_classification():
    athlete = AthleteProfile(name="Test", experience_level="Advanced", age=40, weight_kg=85)
    from bike_analyzer.backend.analytics.performance import get_experience_level
    assert get_experience_level(athlete) == "Advanced"
