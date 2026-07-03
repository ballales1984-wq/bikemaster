"""Tests for core validation layer (Pydantic models + business validators)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from bike_analyzer.core.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.core.validators import (
    BusinessValidationError,
    validate_athlete_profile,
    validate_athlete_profile_partial,
    validate_gps_points,
    validate_ride_for_analysis,
    validate_ride_for_import,
)

# ============================================================
# ValidatedGPSPoint
# ============================================================


class TestValidatedGPSPoint:
    def test_valid_point(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        p = ValidatedGPSPoint(
            lat=45.0,
            lon=9.0,
            timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC),
        )
        assert p.lat == 45.0
        assert p.lon == 9.0

    def test_lat_too_high(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        with pytest.raises(ValidationError):
            ValidatedGPSPoint(
                lat=91, lon=0, timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC)
            )

    def test_lat_too_low(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        with pytest.raises(ValidationError):
            ValidatedGPSPoint(
                lat=-91, lon=0, timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC)
            )

    def test_lon_too_high(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        with pytest.raises(ValidationError):
            ValidatedGPSPoint(
                lat=45.0, lon=181, timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC)
            )

    def test_lon_too_low(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        with pytest.raises(ValidationError):
            ValidatedGPSPoint(
                lat=45.0, lon=-181, timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC)
            )

    def test_timestamp_in_future(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        future = datetime(2030, 1, 1, tzinfo=UTC)
        with pytest.raises(ValidationError):
            ValidatedGPSPoint(lat=45.0, lon=9.0, timestamp=future)

    def test_speed_limits(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        with pytest.raises(ValidationError):
            ValidatedGPSPoint(
                lat=45.0, lon=9.0, timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC),
                speed=150.0,
            )

    def test_heart_rate_limits(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        with pytest.raises(ValidationError):
            ValidatedGPSPoint(
                lat=45.0, lon=9.0, timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC),
                heart_rate=300,
            )

    def test_power_limits(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        with pytest.raises(ValidationError):
            ValidatedGPSPoint(
                lat=45.0, lon=9.0, timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC),
                power=3000.0,
            )

    def test_optional_fields_default_none(self):
        from bike_analyzer.core.validation import ValidatedGPSPoint

        p = ValidatedGPSPoint(
            lat=45.0, lon=9.0, timestamp=datetime(2025, 6, 24, 10, 0, 0, tzinfo=UTC)
        )
        assert p.altitude is None
        assert p.speed is None
        assert p.power is None
        assert p.heart_rate is None
        assert p.cadence is None


# ============================================================
# ValidatedRide
# ============================================================


class TestValidatedRide:
    def _valid_ride_data(self):
        return {
            "athlete_id": 1,
            "date": "2025-06-24",
            "distance_km": 45.0,
            "duration_minutes": 120,
            "avg_speed_kmh": 22.5,
            "elevation_gain_m": 500,
            "calories": 600,
            "gps_points": [
                {
                    "lat": 45.0,
                    "lon": 9.0,
                    "timestamp": "2025-06-24T10:00:00+00:00",
                },
                {
                    "lat": 45.01,
                    "lon": 9.01,
                    "timestamp": "2025-06-24T11:00:00+00:00",
                },
            ],
        }

    def test_valid_ride(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        ride = ValidatedRide.model_validate(data)
        assert ride.distance_km == 45.0
        assert ride.duration_minutes == 120

    def test_distance_above_max(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["distance_km"] = 600
        with pytest.raises(ValidationError, match="distance_km"):
            ValidatedRide.model_validate(data)

    def test_duration_above_max(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["duration_minutes"] = 1500
        with pytest.raises(ValidationError, match="duration_minutes"):
            ValidatedRide.model_validate(data)

    def test_zero_distance(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["distance_km"] = 0
        with pytest.raises(ValidationError, match="distance_km"):
            ValidatedRide.model_validate(data)

    def test_zero_duration(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["duration_minutes"] = 0
        with pytest.raises(ValidationError, match="duration_minutes"):
            ValidatedRide.model_validate(data)

    def test_athlete_id_zero(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["athlete_id"] = 0
        with pytest.raises(ValidationError, match="athlete_id"):
            ValidatedRide.model_validate(data)

    def test_athlete_id_negative(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["athlete_id"] = -1
        with pytest.raises(ValidationError):
            ValidatedRide.model_validate(data)

    def test_speed_incoherent(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["avg_speed_kmh"] = 75.0
        with pytest.raises(ValidationError, match="incoerente"):
            ValidatedRide.model_validate(data)

    def test_single_gps_point_rejected(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["gps_points"] = [
            {
                "lat": 45.0,
                "lon": 9.0,
                "timestamp": "2025-06-24T10:00:00+00:00",
            }
        ]
        with pytest.raises(ValidationError, match="almeno 2"):
            ValidatedRide.model_validate(data)

    def test_title_max_length(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["title"] = "x" * 151
        with pytest.raises(ValidationError, match="title"):
            ValidatedRide.model_validate(data)

    def test_empty_gps_points_ok(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        data["gps_points"] = []
        ride = ValidatedRide.model_validate(data)
        assert ride.gps_points == []

    def test_optional_fields_defaults(self):
        from bike_analyzer.core.validation import ValidatedRide

        data = self._valid_ride_data()
        del data["avg_speed_kmh"]
        del data["elevation_gain_m"]
        del data["calories"]
        if "title" in data:
            del data["title"]
        if "external_source" in data:
            del data["external_source"]
        if "external_id" in data:
            del data["external_id"]
        ride = ValidatedRide.model_validate(data)
        assert ride.avg_speed_kmh is None
        assert ride.elevation_gain_m is None
        assert ride.calories is None
        assert ride.title is None


# ============================================================
# ValidatedAthleteProfile
# ============================================================


class TestValidatedAthleteProfile:
    def test_valid_profile(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        p = ValidatedAthleteProfile(
            name="Mario Rossi",
            age=35,
            weight_kg=72.5,
            experience_level="Intermediate",
        )
        assert p.name == "Mario Rossi"
        assert p.age == 35
        assert p.experience_level == "Intermediate"

    def test_name_too_short(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        with pytest.raises(ValidationError, match="name"):
            ValidatedAthleteProfile(
                name="A", age=30, weight_kg=70, experience_level="Beginner"
            )

    def test_name_too_long(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        with pytest.raises(ValidationError):
            ValidatedAthleteProfile(
                name="x" * 101, age=30, weight_kg=70, experience_level="Beginner"
            )

    def test_age_too_low(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        with pytest.raises(ValidationError):
            ValidatedAthleteProfile(
                name="Test", age=9, weight_kg=70, experience_level="Beginner"
            )

    def test_age_too_high(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        with pytest.raises(ValidationError):
            ValidatedAthleteProfile(
                name="Test", age=101, weight_kg=70, experience_level="Beginner"
            )

    def test_weight_too_low(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        with pytest.raises(ValidationError, match="realistico"):
            ValidatedAthleteProfile(
                name="Test", age=30, weight_kg=31, experience_level="Beginner"
            )

    def test_weight_too_high(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        with pytest.raises(ValidationError, match="realistico"):
            ValidatedAthleteProfile(
                name="Test", age=30, weight_kg=200, experience_level="Beginner"
            )

    def test_invalid_experience_level(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        with pytest.raises(ValidationError, match="experience_level"):
            ValidatedAthleteProfile(
                name="Test", age=30, weight_kg=70, experience_level="SuperPro"
            )

    def test_all_experience_levels(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        for level in ("Beginner", "Intermediate", "Advanced", "Elite"):
            p = ValidatedAthleteProfile(
                name="Test", age=30, weight_kg=70, experience_level=level
            )
            assert p.experience_level == level

    def test_optional_fields_defaults(self):
        from bike_analyzer.core.validation import ValidatedAthleteProfile

        p = ValidatedAthleteProfile(
            name="Test", age=30, weight_kg=70, experience_level="Beginner"
        )
        assert p.id is None
        assert p.height_cm is None
        assert p.ftp_watts is None


# ============================================================
# Business validators (validators.py)
# ============================================================


class TestValidateRideForAnalysis:
    def test_valid_ride(self):
        data = {
            "athlete_id": 1,
            "date": "2025-06-24",
            "distance_km": 45.0,
            "duration_minutes": 120,
            "gps_points": [
                {"lat": 45.0, "lon": 9.0, "timestamp": "2025-06-24T10:00:00+00:00"},
                {"lat": 45.01, "lon": 9.01, "timestamp": "2025-06-24T11:00:00+00:00"},
            ],
        }
        ride = validate_ride_for_analysis(data)
        assert isinstance(ride, Ride)
        assert ride.distance_km == 45.0

    def test_invalid_data_raises(self):
        with pytest.raises(BusinessValidationError):
            validate_ride_for_analysis(
                {"athlete_id": 0, "date": "2025-06-24", "distance_km": 10, "duration_minutes": 30}
            )

    def test_incoherent_speed_raises(self):
        with pytest.raises(BusinessValidationError):
            validate_ride_for_analysis(
                {
                    "athlete_id": 1,
                    "date": "2025-06-24",
                    "distance_km": 10,
                    "duration_minutes": 30,
                    "avg_speed_kmh": 200,
                }
            )


class TestValidateRideForImport:
    def test_valid_import(self):
        data = {
            "athlete_id": 1,
            "date": "2025-06-24",
            "distance_km": 45.0,
            "duration_minutes": 120,
        }
        ride = validate_ride_for_import(data)
        assert isinstance(ride, Ride)

    def test_invalid_import_raises(self):
        with pytest.raises(BusinessValidationError):
            validate_ride_for_import(
                {"athlete_id": 0, "date": "2025-06-24", "distance_km": 0, "duration_minutes": 0}
            )


class TestValidateGPSPoints:
    def test_valid_points(self):
        points_data = [
            {"lat": 45.0, "lon": 9.0, "timestamp": "2025-06-24T10:00:00+00:00"},
            {"lat": 45.01, "lon": 9.01, "timestamp": "2025-06-24T10:05:00+00:00"},
        ]
        points = validate_gps_points(points_data)
        assert len(points) == 2
        assert isinstance(points[0], GPSPoint)

    def test_single_point_raises(self):
        with pytest.raises(BusinessValidationError, match="almeno 2"):
            validate_gps_points(
                [{"lat": 45.0, "lon": 9.0, "timestamp": "2025-06-24T10:00:00+00:00"}]
            )

    def test_empty_list_raises(self):
        with pytest.raises(BusinessValidationError, match="almeno 2"):
            validate_gps_points([])

    def test_invalid_coordinate_raises(self):
        with pytest.raises(BusinessValidationError):
            validate_gps_points(
                [
                    {"lat": 91, "lon": 9.0, "timestamp": "2025-06-24T10:00:00+00:00"},
                    {"lat": 45.0, "lon": 9.0, "timestamp": "2025-06-24T10:00:00+00:00"},
                ]
            )

    def test_future_timestamp_raises(self):
        with pytest.raises(BusinessValidationError):
            validate_gps_points(
                [
                    {"lat": 45.0, "lon": 9.0, "timestamp": "2030-01-01T10:00:00+00:00"},
                    {"lat": 45.01, "lon": 9.01, "timestamp": "2030-01-01T10:05:00+00:00"},
                ]
            )


class TestValidateAthleteProfile:
    def test_valid_profile(self):
        data = {"name": "Mario Rossi", "age": 35, "weight_kg": 72.5, "experience_level": "Intermediate"}
        profile = validate_athlete_profile(data)
        assert isinstance(profile, AthleteProfile)
        assert profile.name == "Mario Rossi"

    def test_invalid_name_raises(self):
        with pytest.raises(BusinessValidationError):
            validate_athlete_profile(
                {"name": "A", "age": 30, "weight_kg": 70, "experience_level": "Beginner"}
            )

    def test_invalid_level_raises(self):
        with pytest.raises(BusinessValidationError):
            validate_athlete_profile(
                {"name": "Test", "age": 30, "weight_kg": 70, "experience_level": "Pro"}
            )


class TestValidateAthleteProfilePartial:
    def test_partial_data(self):
        data = {"name": "Test", "age": 30, "weight_kg": 70, "experience_level": "Beginner"}
        profile = validate_athlete_profile_partial(data)
        assert isinstance(profile, AthleteProfile)
        assert profile.name == "Test"
