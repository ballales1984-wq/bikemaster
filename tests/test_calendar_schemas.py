"""Extended schema validation tests for calendar and itinerary schemas.

Covers edge cases, boundary values, and constraint validation for
CalendarEventCreate, CalendarEventUpdate, ItineraryCreate, StageCreate,
and GranfondoPlanWorkout.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bike_analyzer.backend.api.schemas import (
    CalendarEventCreate,
    CalendarEventUpdate,
    GranfondoPlanWorkout,
    ItineraryCreate,
    StageCreate,
)


class TestCalendarEventCreateSchema:
    def test_valid_minimal(self):
        c = CalendarEventCreate(athlete_id=1, title="Ride", event_type="training", date="2024-06-15")
        assert c.athlete_id == 1
        assert c.title == "Ride"
        assert c.completed is False

    def test_valid_all_fields(self):
        c = CalendarEventCreate(
            athlete_id=1,
            title="Full Event",
            event_type="race",
            date="2024-06-15",
            duration_minutes=180,
            description="Gran Fondo prep",
            completed=True,
            lat=45.5,
            lon=7.2,
        )
        assert c.duration_minutes == 180
        assert c.description == "Gran Fondo prep"
        assert c.completed is True

    def test_event_type_pattern_allows_valid(self):
        for etype in ("training", "race", "recovery", "goal_deadline", "test", "other"):
            c = CalendarEventCreate(athlete_id=1, title="T", event_type=etype, date="2024-06-15")
            assert c.event_type == etype

    def test_event_type_rejects_invalid(self):
        with pytest.raises(ValidationError, match="event_type"):
            CalendarEventCreate(athlete_id=1, title="T", event_type="invalid", date="2024-06-15")

    def test_date_pattern_accepts_iso(self):
        c = CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-06-15")
        assert c.date == "2024-06-15"

    def test_date_pattern_rejects_bad_format(self):
        with pytest.raises(ValidationError, match="date"):
            CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024/06/15")

    def test_date_pattern_rejects_partial(self):
        with pytest.raises(ValidationError, match="date"):
            CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-6-5")

    def test_athlete_id_must_be_positive(self):
        with pytest.raises(ValidationError, match="athlete_id"):
            CalendarEventCreate(athlete_id=0, title="T", event_type="training", date="2024-06-15")

    def test_title_min_length(self):
        with pytest.raises(ValidationError, match="title"):
            CalendarEventCreate(athlete_id=1, title="", event_type="training", date="2024-06-15")

    def test_title_max_length(self):
        with pytest.raises(ValidationError, match="title"):
            CalendarEventCreate(athlete_id=1, title="X" * 201, event_type="training", date="2024-06-15")

    def test_duration_min_zero(self):
        c = CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-06-15", duration_minutes=0)
        assert c.duration_minutes == 0

    def test_duration_max_1440(self):
        c = CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-06-15", duration_minutes=1440)
        assert c.duration_minutes == 1440

    def test_duration_exceeds_max(self):
        with pytest.raises(ValidationError, match="duration_minutes"):
            CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-06-15", duration_minutes=1441)

    def test_lat_boundaries(self):
        c = CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-06-15", lat=90.0)
        assert c.lat == 90.0
        c = CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-06-15", lat=-90.0)
        assert c.lat == -90.0

    def test_lon_boundaries(self):
        c = CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-06-15", lon=180.0)
        assert c.lon == 180.0
        c = CalendarEventCreate(athlete_id=1, title="T", event_type="training", date="2024-06-15", lon=-180.0)
        assert c.lon == -180.0

    def test_description_max_length(self):
        with pytest.raises(ValidationError, match="description"):
            CalendarEventCreate(
                athlete_id=1, title="T", event_type="training", date="2024-06-15",
                description="X" * 1001,
            )


class TestCalendarEventUpdateSchema:
    def test_all_fields_optional(self):
        c = CalendarEventUpdate()
        assert c.title is None
        assert c.event_type is None
        assert c.date is None
        assert c.duration_minutes is None
        assert c.description is None
        assert c.completed is None

    def test_partial_update(self):
        c = CalendarEventUpdate(title="New Title")
        assert c.title == "New Title"
        assert c.event_type is None

    def test_update_event_type_valid(self):
        c = CalendarEventUpdate(event_type="race")
        assert c.event_type == "race"

    def test_update_event_type_invalid(self):
        with pytest.raises(ValidationError, match="event_type"):
            CalendarEventUpdate(event_type="invalid")

    def test_update_date_pattern(self):
        with pytest.raises(ValidationError, match="date"):
            CalendarEventUpdate(date="2024/06/15")


class TestItineraryCreateSchema:
    def test_valid_minimal(self):
        i = ItineraryCreate(name="Trip")
        assert i.name == "Trip"
        assert i.total_km is None

    def test_valid_full(self):
        i = ItineraryCreate(
            name="Alps",
            description="Mountain tour",
            start_date="2024-07-01",
            end_date="2024-07-05",
            total_km=300.0,
            total_elevation_m=5000.0,
        )
        assert i.total_km == 300.0

    def test_name_min_length(self):
        with pytest.raises(ValidationError, match="name"):
            ItineraryCreate(name="A")

    def test_name_max_length(self):
        with pytest.raises(ValidationError, match="name"):
            ItineraryCreate(name="X" * 151)

    def test_date_pattern_valid(self):
        i = ItineraryCreate(name="Trip", start_date="2024-07-01")
        assert i.start_date == "2024-07-01"

    def test_date_pattern_invalid(self):
        with pytest.raises(ValidationError, match="start_date"):
            ItineraryCreate(name="Trip", start_date="2024/07/01")

    def test_total_km_min_zero(self):
        i = ItineraryCreate(name="Trip", total_km=0)
        assert i.total_km == 0

    def test_total_km_exceeds_max(self):
        with pytest.raises(ValidationError, match="total_km"):
            ItineraryCreate(name="Trip", total_km=200000.0)

    def test_total_elevation_exceeds_max(self):
        with pytest.raises(ValidationError, match="total_elevation_m"):
            ItineraryCreate(name="Trip", total_elevation_m=200000.0)


class TestStageCreateSchema:
    def test_valid_minimal(self):
        s = StageCreate(stage_day=1)
        assert s.stage_day == 1
        assert s.title is None

    def test_valid_full(self):
        s = StageCreate(stage_day=2, title="Day 2", distance_km=100.0, elevation_gain_m=1500.0)
        assert s.title == "Day 2"
        assert s.distance_km == 100.0

    def test_stage_day_min(self):
        s = StageCreate(stage_day=1)
        assert s.stage_day == 1

    def test_stage_day_max(self):
        s = StageCreate(stage_day=366)
        assert s.stage_day == 366

    def test_stage_day_below_min(self):
        with pytest.raises(ValidationError, match="stage_day"):
            StageCreate(stage_day=0)

    def test_stage_day_above_max(self):
        with pytest.raises(ValidationError, match="stage_day"):
            StageCreate(stage_day=367)

    def test_distance_min_zero(self):
        s = StageCreate(stage_day=1, distance_km=0)
        assert s.distance_km == 0

    def test_distance_exceeds_max(self):
        with pytest.raises(ValidationError, match="distance_km"):
            StageCreate(stage_day=1, distance_km=200000.0)

    def test_elevation_exceeds_max(self):
        with pytest.raises(ValidationError, match="elevation_gain_m"):
            StageCreate(stage_day=1, elevation_gain_m=200000.0)


class TestGranfondoPlanWorkoutSchema:
    def test_valid_minimal(self):
        w = GranfondoPlanWorkout(date="2024-08-05", title="Ride", workout_type="training", duration_minutes=60)
        assert w.title == "Ride"
        assert w.target_intensity == 0.0

    def test_valid_full(self):
        w = GranfondoPlanWorkout(
            date="2024-08-05",
            title="Intervals",
            workout_type="interval",
            duration_minutes=90,
            target_intensity=0.8,
            description="VO2 max intervals",
        )
        assert w.target_intensity == 0.8

    def test_date_pattern_valid(self):
        w = GranfondoPlanWorkout(date="2024-08-05", title="R", workout_type="training")
        assert w.date == "2024-08-05"

    def test_date_pattern_invalid(self):
        with pytest.raises(ValidationError, match="date"):
            GranfondoPlanWorkout(date="2024/08/05", title="R", workout_type="training")

    def test_title_min_length(self):
        with pytest.raises(ValidationError, match="title"):
            GranfondoPlanWorkout(date="2024-08-05", title="", workout_type="training")

    def test_title_max_length(self):
        with pytest.raises(ValidationError, match="title"):
            GranfondoPlanWorkout(date="2024-08-05", title="X" * 201, workout_type="training")

    def test_duration_min(self):
        w = GranfondoPlanWorkout(date="2024-08-05", title="R", workout_type="training", duration_minutes=0)
        assert w.duration_minutes == 0

    def test_duration_max(self):
        w = GranfondoPlanWorkout(date="2024-08-05", title="R", workout_type="training", duration_minutes=1440)
        assert w.duration_minutes == 1440

    def test_duration_exceeds_max(self):
        with pytest.raises(ValidationError, match="duration_minutes"):
            GranfondoPlanWorkout(date="2024-08-05", title="R", workout_type="training", duration_minutes=1441)

    def test_target_intensity_range(self):
        w = GranfondoPlanWorkout(date="2024-08-05", title="R", workout_type="training", target_intensity=1.0)
        assert w.target_intensity == 1.0

    def test_target_intensity_exceeds_max(self):
        with pytest.raises(ValidationError, match="target_intensity"):
            GranfondoPlanWorkout(date="2024-08-05", title="R", workout_type="training", target_intensity=1.1)
