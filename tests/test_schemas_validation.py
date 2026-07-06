"""Tests for API Pydantic schemas validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bike_analyzer.backend.api.schemas import (
    AthleteCreate,
    AthleteUpdate,
    BenchmarkCompareRequest,
    CalendarEventCreate,
    CalendarEventUpdate,
    CoachChatRequest,
    GarminCallbackRequest,
    GoogleFitImportPayload,
    GoogleFitTokenRequest,
    GoogleHealthImportPayload,
    GranfondoPlanRequest,
    ProfileUpdate,
    RideCreate,
    RideUpdate,
    StravaCallbackRequest,
    TrainingGoalCreate,
)


class TestRideSchemas:
    def test_valid_ride_create(self):
        r = RideCreate(date="2024-06-15", distance_km=35.0, duration_minutes=90)
        assert r.date == "2024-06-15"
        assert r.distance_km == 35.0

    def test_invalid_date_pattern(self):
        with pytest.raises(ValidationError, match="date"):
            RideCreate(date="not-a-date", distance_km=35.0, duration_minutes=90)

    def test_distance_exceeds_max(self):
        with pytest.raises(ValidationError, match="distance_km"):
            RideCreate(date="2024-06-15", distance_km=600.0, duration_minutes=90)

    def test_zero_duration_rejected(self):
        with pytest.raises(ValidationError, match="duration_minutes"):
            RideCreate(date="2024-06-15", distance_km=35.0, duration_minutes=0)

    def test_valid_ride_update(self):
        r = RideUpdate(date="2024-06-15", distance_km=35.0)
        assert r.distance_km == 35.0

    def test_ride_update_all_optional(self):
        r = RideUpdate()
        assert r.date is None

    def test_benachmark_compare_requires_date(self):
        with pytest.raises(ValidationError, match="date"):
            BenchmarkCompareRequest(distance_km=50.0, duration_minutes=120)

    def test_valid_benchmark_compare(self):
        r = BenchmarkCompareRequest(date="2024-06-15", distance_km=50.0, duration_minutes=120)
        assert r.distance_km == 50.0


class TestAthleteSchemas:
    def test_valid_athlete_create(self):
        a = AthleteCreate(name="Mario Rossi", age=35, weight_kg=72.0, experience_level="Intermediate")
        assert a.experience_level == "Intermediate"

    def test_invalid_experience_level(self):
        with pytest.raises(ValidationError, match="experience_level"):
            AthleteCreate(name="Test", age=30, weight_kg=70.0, experience_level="SuperPro")

    def test_valid_experience_levels(self):
        for level in ("Beginner", "Amateur", "Intermediate", "Advanced", "Elite"):
            a = AthleteCreate(name="Test", age=30, weight_kg=70.0, experience_level=level)
            assert a.experience_level == level

    def test_invalid_email_format(self):
        with pytest.raises(ValidationError, match="email"):
            AthleteCreate(name="Test", age=30, weight_kg=70.0, email="bad-email")

    def test_valid_email(self):
        a = AthleteCreate(name="Test", age=30, weight_kg=70.0, email="test@example.com")
        assert a.email == "test@example.com"

    def test_name_too_short(self):
        with pytest.raises(ValidationError, match="name"):
            AthleteCreate(name="A", age=30, weight_kg=70.0)

    def test_age_out_of_range(self):
        with pytest.raises(ValidationError, match="age"):
            AthleteCreate(name="Test", age=9, weight_kg=70.0)

    def test_valid_athlete_update(self):
        a = AthleteUpdate(name="Mario", experience_level="Advanced", email="mario@example.com")
        assert a.experience_level == "Advanced"

    def test_profile_update_valid(self):
        p = ProfileUpdate(name="Test", weekly_volume_km=100.0, ftp_watts=250)
        assert p.name == "Test"

    def test_profile_update_invalid_email(self):
        with pytest.raises(ValidationError, match="email"):
            ProfileUpdate(email="bad")


class TestCalendarSchemas:
    def test_valid_calendar_event(self):
        c = CalendarEventCreate(athlete_id=1, title="Gran Fondo", event_type="race", date="2024-06-15")
        assert c.event_type == "race"

    def test_invalid_event_type(self):
        with pytest.raises(ValidationError, match="event_type"):
            CalendarEventCreate(athlete_id=1, title="Test", event_type="invalid")

    def test_invalid_lat_lon(self):
        with pytest.raises(ValidationError, match="lat"):
            CalendarEventCreate(athlete_id=1, title="Test", event_type="training", date="2024-06-15", lat=91)

    def test_calendar_event_update(self):
        c = CalendarEventUpdate(title="Updated", completed=True)
        assert c.title == "Updated"


class TestOAuthSchemas:
    def test_valid_strava_callback(self):
        s = StravaCallbackRequest(code="abc123", code_verifier="xyz789")
        assert s.code == "abc123"

    def test_missing_code_verifier(self):
        with pytest.raises(ValidationError, match="code_verifier"):
            StravaCallbackRequest(code="abc123")

    def test_valid_garmin_callback(self):
        g = GarminCallbackRequest(code="abc123")
        assert g.code == "abc123"

    def test_valid_google_fit_token_request(self):
        g = GoogleFitTokenRequest(client_id="id", client_secret="secret", code="code")
        assert g.client_id == "id"

    def test_valid_google_fit_import(self):
        g = GoogleFitImportPayload(access_token="token123")
        assert g.access_token == "token123"

    def test_valid_google_health_import(self):
        g = GoogleHealthImportPayload(access_token="token123")
        assert g.access_token == "token123"


class TestOtherSchemas:
    def test_valid_coach_chat(self):
        c = CoachChatRequest(message="test message")
        assert c.message == "test message"

    def test_coach_chat_empty_message(self):
        with pytest.raises(ValidationError, match="message"):
            CoachChatRequest(message="   ")

    def test_valid_granfondo_request(self):
        g = GranfondoPlanRequest(athlete_id=1, start_date="2024-06-15", target_weeks=10)
        assert g.target_weeks == 10

    def test_granfondo_invalid_weeks(self):
        with pytest.raises(ValidationError, match="target_weeks"):
            GranfondoPlanRequest(athlete_id=1, start_date="2024-06-15", target_weeks=7)

    def test_valid_training_goal(self):
        t = TrainingGoalCreate(title="Gran Fondo", goal_type="granfondo", target_date="2024-09-15")
        assert t.goal_type == "granfondo"

    def test_training_goal_invalid_type(self):
        with pytest.raises(ValidationError, match="goal_type"):
            TrainingGoalCreate(title="Test", goal_type="invalid")
