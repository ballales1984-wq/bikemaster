"""Tests for the Athlete State Engine."""

from __future__ import annotations

from datetime import UTC, datetime

from bike_analyzer.backend.analytics.athlete_state.calculators import (
    average_fatigue_score,
    build_daily_tss_series,
    calculate_fatigue_for_ride,
    compute_readiness,
    compute_recommendation,
    compute_risk_level,
    estimate_recovery_hours,
)
from bike_analyzer.backend.analytics.athlete_state.models import AthleteState, PersonalResponseModel
from bike_analyzer.backend.analytics.athlete_state.service import AthleteStateService
from bike_analyzer.backend.models.models import AthleteProfile
from bike_analyzer.core.models import Ride


class TestBuildDailyTssSeries:
    def test_empty_rides(self):
        result = build_daily_tss_series([])
        assert result == []

    def test_single_ride(self):
        rides = [Ride(date="2024-06-15", duration_minutes=60, distance_km=30.0)]
        result = build_daily_tss_series(rides)
        assert len(result) == 1
        assert result[0][0] == "2024-06-15"
        assert result[0][1] > 0

    def test_multiple_rides_same_day(self):
        rides = [
            Ride(date="2024-06-15", duration_minutes=60, distance_km=30.0),
            Ride(date="2024-06-15", duration_minutes=45, distance_km=20.0),
        ]
        result = build_daily_tss_series(rides)
        assert len(result) == 1
        assert result[0][1] > 0

    def test_multiple_days(self):
        rides = [
            Ride(date="2024-06-10", duration_minutes=60, distance_km=30.0),
            Ride(date="2024-06-15", duration_minutes=60, distance_km=30.0),
        ]
        result = build_daily_tss_series(rides)
        assert len(result) == 2
        assert result[0][0] == "2024-06-10"
        assert result[1][0] == "2024-06-15"


class TestCalculateFatigueForRide:
    def test_no_hr(self):
        ride = Ride(date="2024-06-15", duration_minutes=60, distance_km=30.0)
        score = calculate_fatigue_for_ride(ride, rider_age=35)
        assert 0.0 <= score <= 10.0

    def test_with_hr(self):
        ride = Ride(
            date="2024-06-15",
            duration_minutes=120,
            distance_km=60.0,
            avg_speed_kmh=30.0,
            heart_rate_avg=150.0,
            weight_kg=70.0,
            elevation_gain_m=500.0,
        )
        score = calculate_fatigue_for_ride(ride, rider_age=35)
        assert 0.0 <= score <= 10.0


class TestAverageFatigueScore:
    def test_empty(self):
        avg, mx = average_fatigue_score([])
        assert avg == 0.0
        assert mx == 0.0

    def test_single_ride(self):
        rides = [Ride(date="2024-06-15", duration_minutes=60, distance_km=30.0, heart_rate_avg=140.0)]
        avg, mx = average_fatigue_score(rides)
        assert avg == mx
        assert avg > 0

    def test_multiple_rides(self):
        rides = [
            Ride(date="2024-06-15", duration_minutes=60, distance_km=30.0, heart_rate_avg=140.0),
            Ride(date="2024-06-16", duration_minutes=90, distance_km=45.0, heart_rate_avg=160.0),
        ]
        avg, mx = average_fatigue_score(rides)
        assert avg > 0
        assert mx >= avg


class TestEstimateRecoveryHours:
    def test_low_fatigue(self):
        assert estimate_recovery_hours(2.0) == 8.0

    def test_medium_fatigue(self):
        assert estimate_recovery_hours(5.0) == 16.0

    def test_high_fatigue(self):
        assert estimate_recovery_hours(8.0) == 48.0

    def test_tsb_penalty(self):
        base = estimate_recovery_hours(5.0)
        with_penalty = estimate_recovery_hours(5.0, tsb=-20.0)
        assert with_penalty > base


class TestComputeReadiness:
    def test_fresh_athlete(self):
        score = compute_readiness(atl=60, ctl=80, tsb=20, fatigue_score=2, acwr=1.0)
        assert score >= 80

    def test_fatigued_athlete(self):
        score = compute_readiness(atl=100, ctl=80, tsb=-30, fatigue_score=8, acwr=1.6)
        assert score <= 40

    def test_balanced(self):
        score = compute_readiness(atl=70, ctl=75, tsb=5, fatigue_score=3, acwr=1.0)
        assert score >= 70


class TestComputeRiskLevel:
    def test_overtraining_risk(self):
        assert compute_risk_level(atl=120, ctl=85, tsb=-25, acwr=1.0, fatigue_score=3) == "block"

    def test_high_acwr(self):
        assert compute_risk_level(atl=90, ctl=80, tsb=-10, acwr=1.6, fatigue_score=4) == "high"

    def test_warning(self):
        assert compute_risk_level(atl=95, ctl=80, tsb=-25, acwr=1.3, fatigue_score=5) == "warning"

    def test_ok(self):
        assert compute_risk_level(atl=70, ctl=75, tsb=5, acwr=1.0, fatigue_score=2) == "ok"


class TestComputeRecommendation:
    def test_total_rest(self):
        rec = compute_recommendation(atl=100, ctl=80, tsb=-30, fatigue_score=8, readiness=20)
        assert "rest" in rec.lower()

    def test_ready_for_hard(self):
        rec = compute_recommendation(atl=70, ctl=75, tsb=10, fatigue_score=2, readiness=80)
        assert "hard effort" in rec.lower()

    def test_fresh(self):
        rec = compute_recommendation(atl=60, ctl=80, tsb=20, fatigue_score=2, readiness=90)
        assert "freshness" in rec.lower()


class TestAthleteStateModel:
    def test_defaults(self):
        state = AthleteState(athlete_id=1)
        assert state.fatigue_score == 0.0
        assert state.readiness == 100.0
        assert state.acwr == 1.0
        assert state.risk_level == "ok"

    def test_overtraining_risk_property(self):
        state = AthleteState(athlete_id=1, atl=120.0, ctl=85.0, tsb=-25.0)
        assert state.is_overtraining_risk is True

    def test_fresh_property(self):
        state = AthleteState(athlete_id=1, tsb=20.0)
        assert state.is_fresh is True

    def test_ready_for_hard_effort_property(self):
        state = AthleteState(athlete_id=1, tsb=10.0, atl=80.0, ctl=85.0)
        assert state.is_ready_for_hard_effort is True

    def test_to_dict_keys(self):
        state = AthleteState(athlete_id=1, atl=70.0, ctl=80.0, tsb=10.0)
        d = state.to_dict()
        assert d["athlete_id"] == 1
        assert "atl" in d
        assert "ctl" in d
        assert "tsb" in d
        assert "is_overtraining_risk" in d
        assert "is_fresh" in d
        assert "is_ready_for_hard_effort" in d

    def test_to_dataclass(self):
        state = AthleteState(athlete_id=1, fatigue_score=5.0, readiness=80.0, acwr=1.2, tsb=5.0, atl=70.0, ctl=75.0)
        dc = state.to_dataclass()
        assert dc.fatigue_score == 5.0
        assert dc.readiness == 80.0
        assert dc.acwr == 1.2


class TestPersonalResponseModel:
    def test_defaults(self):
        state = AthleteState(athlete_id=1)
        resp = PersonalResponseModel(athlete_id=1, computed_at=datetime.now(UTC), state=state)
        assert resp.athlete_id == 1
        assert resp.state.athlete_id == 1


class TestAthleteStateService:
    def test_calculate_current_state_empty_rides(self):
        service = AthleteStateService(ftp=250.0)
        import asyncio

        state = asyncio.run(
            service.calculate_current_state(athlete_id=1, rides=[])
        )
        assert state.athlete_id == 1
        assert state.atl == 0.0
        assert state.ctl == 0.0
        assert state.tsb == 0.0
        assert state.fatigue_score == 0.0
        assert state.readiness == 100.0
        assert state.risk_level == "ok"

    def test_calculate_current_state_with_rides(self):
        service = AthleteStateService(ftp=250.0)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        yesterday = (datetime.now(UTC).replace(tzinfo=None) - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
        day_before = (datetime.now(UTC).replace(tzinfo=None) - __import__('datetime').timedelta(days=2)).strftime("%Y-%m-%d")
        rides = [
            Ride(date=day_before, duration_minutes=60, distance_km=30.0, avg_speed_kmh=25.0, heart_rate_avg=140.0),
            Ride(date=yesterday, duration_minutes=90, distance_km=45.0, avg_speed_kmh=28.0, heart_rate_avg=155.0),
            Ride(date=today, duration_minutes=45, distance_km=20.0, avg_speed_kmh=22.0, heart_rate_avg=130.0),
        ]
        import asyncio

        state = asyncio.run(
            service.calculate_current_state(athlete_id=1, rides=rides)
        )
        assert state.athlete_id == 1
        assert state.weekly_tss > 0
        assert 0.0 <= state.readiness <= 100.0
        assert state.risk_level in ("ok", "warning", "high", "block")

    def test_calculate_current_state_with_profile(self):
        service = AthleteStateService(ftp=250.0)
        profile = AthleteProfile.__new__(AthleteProfile)
        profile.ftp_watts = 280.0
        profile.age = 40
        profile.id = 1

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        rides = [
            Ride(date=today, duration_minutes=60, distance_km=30.0, avg_speed_kmh=25.0, heart_rate_avg=140.0),
        ]
        import asyncio

        state = asyncio.run(
            service.calculate_current_state(athlete_id=1, rides=rides, athlete_profile=profile)
        )
        assert state.athlete_id == 1
        assert state.fitness > 0 or state.weekly_tss > 0

    def test_calculate_current_state_recent_rides_fatigue(self):
        service = AthleteStateService(ftp=250.0)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        rides = [
            Ride(
                date=today,
                duration_minutes=180,
                distance_km=90.0,
                avg_speed_kmh=30.0,
                heart_rate_avg=170.0,
                elevation_gain_m=2000.0,
                weight_kg=70.0,
            ),
        ]
        import asyncio

        state = asyncio.run(
            service.calculate_current_state(athlete_id=1, rides=rides)
        )
        assert state.fatigue_score > 0
        assert state.recovery_hours_needed > 0
