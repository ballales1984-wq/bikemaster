import os

os.environ["GROQ_API_KEY"] = "test-key"

from bike_analyzer.backend.analytics.ai_coach import validate_athlete_profile
from bike_analyzer.backend.models.models import AthleteProfile, Ride


def test_validate_athlete_profile_rejects_empty():
    profile = AthleteProfile(name="", weight_kg=70.0, experience_level="Beginner")
    valid, msg = validate_athlete_profile(profile)
    assert valid is False
    assert "nome" in msg


def test_validate_athlete_profile_accepts_complete():
    profile = AthleteProfile(name="Marco", weight_kg=72.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(profile)
    assert valid is True
    assert msg == ""

