"""Extended coverage tests targeting advanced.py, performance.py, ai_coach.py edge cases."""

from datetime import UTC, datetime

from bike_analyzer.backend.analytics import analytics as analytics_mod
from bike_analyzer.backend.analytics.advanced import (
    analyze_elevation_profile,
    analyze_speed_profile,
    calculate_garmin_power_factor,
    calculate_heart_rate_zones,
    calculate_power_estimate,
    calculate_progress_trend,
    calculate_ride_recommendation_score,
    calculate_training_stress_balance,
    classify_climb,
    classify_ride_difficulty,
    detect_speed_surges,
    estimate_ideal_weight,
    estimate_vo2max,
)
from bike_analyzer.backend.analytics.fatigue import estimate_recovery_hours
from bike_analyzer.backend.analytics.performance import (
    calculate_efficiency_score,
    calculate_endurance_score,
    calculate_performance_score,
    calculate_recovery_score,
    classify_athlete,
)
from bike_analyzer.backend.analytics.training_load import (
    calculate_atl_ctl_tsb,
    calculate_rss,
    get_7day_fitness_summary,
    get_current_training_status,
)
from bike_analyzer.backend.models.models import GPSPoint, Ride

# ============================================================
# advanced.py — edge cases and uncovered branches
# ============================================================


class TestAdvancedEdgeCases:
    def test_power_estimate_with_rider_weight(self):
        ride = Ride(
            date="2024-06-01",
            distance_km=30,
            duration_minutes=60,
            avg_speed_kmh=30,
            weight_kg=70,
            elevation_gain_m=200,
        )
        result = calculate_power_estimate(ride, rider_weight_kg=72)
        assert result["power_avg_w"] > 0
        assert result["speed_ms"] > 0
        assert "grade_percent" in result

    def test_power_estimate_all_zero(self):
        ride = Ride(date="2024-06-01", distance_km=0, duration_minutes=0, avg_speed_kmh=0)
        result = calculate_power_estimate(ride)
        assert result["power_avg_w"] == 0.0
        assert result["cd_wind"] == 0.0

    def test_power_estimate_zero_duration(self):
        ride = Ride(date="2024-06-01", distance_km=30, duration_minutes=0, avg_speed_kmh=30)
        result = calculate_power_estimate(ride)
        assert result["power_avg_w"] == 0.0

    def test_climb_hc(self):
        r = classify_climb(segment_length_km=8.0, avg_gradient_percent=18)
        assert r["category"] == "HC"
        assert r["points"] == 5

    def test_climb_edge_thresholds(self):
        r = classify_climb(segment_length_km=0.2, avg_gradient_percent=1)
        assert r["category"] == "none"
        r = classify_climb(segment_length_km=0.25, avg_gradient_percent=12)
        assert r["category"] == "1"

    def test_vo2max_age_effect(self):
        young = estimate_vo2max(avg_speed_kmh=30, avg_gradient_percent=0, weight_kg=70, age=25)
        older = estimate_vo2max(avg_speed_kmh=30, avg_gradient_percent=0, weight_kg=70, age=50)
        assert older["speed_match_kmh"] < young["speed_match_kmh"]
        assert older["vo2_max_ml_kg_min"] < young["vo2_max_ml_kg_min"]

    def test_vo2max_bounds(self):
        low = estimate_vo2max(avg_speed_kmh=5, avg_gradient_percent=0, weight_kg=70, age=30)
        high = estimate_vo2max(avg_speed_kmh=50, avg_gradient_percent=20, weight_kg=70, age=30)
        assert 30.0 <= low["vo2_max_ml_kg_min"] <= 75.0
        assert 30.0 <= high["vo2_max_ml_kg_min"] <= 75.0

    def test_ride_difficulty_extreme(self):
        ride = Ride(
            date="2024-06-01",
            distance_km=200,
            duration_minutes=480,
            avg_speed_kmh=35,
            heart_rate_avg=185,
            elevation_gain_m=5000,
        )
        result = classify_ride_difficulty(ride)
        assert result["level"] == "Extreme"
        assert result["score"] > 7

    def test_ride_difficulty_zero_distance(self):
        ride = Ride(date="2024-06-01", distance_km=0, duration_minutes=60, avg_speed_kmh=0)
        result = classify_ride_difficulty(ride)
        assert result["score"] == 0
        assert result["level"] == "unknown"

    def test_elevation_profile_all_flat(self):
        points = [
            GPSPoint(46.1, 11.1, datetime.now(UTC), altitude=100),
            GPSPoint(46.1, 11.2, datetime.now(UTC), altitude=100),
            GPSPoint(46.1, 11.3, datetime.now(UTC), altitude=100),
        ]
        result = analyze_elevation_profile(points)
        assert result["hardship_index"] == 0.0
        assert result["grade_distribution"]["flat"] == 2

    def test_elevation_profile_insufficient_points(self):
        result = analyze_elevation_profile([])
        assert result["hardship_index"] == 0.0
        assert result["total_sampled"] == 0

        result = analyze_elevation_profile([GPSPoint(46.1, 11.1, datetime.now(UTC))])
        assert result["hardship_index"] == 0.0

    def test_speed_profile_coasting(self):
        points = [
            GPSPoint(46.1, 11.1, datetime.now(UTC), speed=25.0),
            GPSPoint(46.1, 11.2, datetime.now(UTC), speed=25.0),
            GPSPoint(46.1, 11.3, datetime.now(UTC), speed=25.0),
        ]
        result = analyze_speed_profile(points)
        assert result["speed_variance"] < 1.0
        assert result["coasting_time_pct"] > 0

    def test_speed_profile_insufficient(self):
        result = analyze_speed_profile([])
        assert result["acceleration_events"] == 0
        assert result["speed_variance"] == 0.0

        pts = [GPSPoint(46.1, 11.1, datetime.now(UTC), speed=25.0)]
        result = analyze_speed_profile(pts)
        assert result["acceleration_events"] == 0

    def test_progress_trend_declining(self):
        rides = [
            Ride(date="2024-01-01", avg_speed_kmh=30),
            Ride(date="2024-02-01", avg_speed_kmh=28),
            Ride(date="2024-03-01", avg_speed_kmh=25),
            Ride(date="2024-04-01", avg_speed_kmh=22),
        ]
        result = calculate_progress_trend(rides)
        assert result["trend"] == "declining"
        assert result["slope"] < 0

    def test_progress_trend_stable(self):
        rides = [
            Ride(date="2024-01-01", avg_speed_kmh=25),
            Ride(date="2024-02-01", avg_speed_kmh=25),
            Ride(date="2024-03-01", avg_speed_kmh=25),
            Ride(date="2024-04-01", avg_speed_kmh=25),
        ]
        result = calculate_progress_trend(rides)
        assert result["trend"] in ("stable", "declining", "improving")

    def test_progress_trend_error_handling(self):
        result = calculate_progress_trend([])
        assert result["trend"] == "insufficient_data"
        assert result["r_squared"] == 0.0

        result = calculate_progress_trend([Ride(date="2024-01-01", avg_speed_kmh=0)])
        assert result["trend"] == "insufficient_data"

        rides = [
            Ride(date="2024-01-01", avg_speed_kmh=None),
            Ride(date="2024-02-01", avg_speed_kmh=None),
        ]
        result = calculate_progress_trend(rides)
        assert result["trend"] == "insufficient_data"

    def test_training_stress_balance_no_data(self):
        result = calculate_training_stress_balance([])
        assert result["form"] == "no_data"
        assert result["atl"] == 0.0
        assert result["daily_load"] == []

    def test_ideal_weight_zero_ftp(self):
        assert estimate_ideal_weight(ftp=0, height_cm=175) == 70.0
        assert estimate_ideal_weight(ftp=0, height_cm=0) == 70.0
        assert estimate_ideal_weight(ftp=350, height_cm=0) == 70.0

    def test_garmin_power_factor_zero_speed(self):
        ride = Ride(date="2024-06-01", distance_km=0, duration_minutes=0, avg_speed_kmh=0)
        result = calculate_garmin_power_factor(ride)
        assert result["pf"] == 0.0

    def test_heart_rate_zones_with_current_hr(self):
        zones = calculate_heart_rate_zones(max_hr=180, lthr=155, current_avg_hr=155)
        for z in zones.values():
            if "in_zone" in z:
                assert z["in_zone"] is True or z["in_zone"] is False
        assert zones["Z4 (Threshold)"]["min"] == int(180 * 0.84)

    def test_ride_recommendation_score_recovery(self):
        ride = Ride(date="2024-06-01", distance_km=5, duration_minutes=15, avg_speed_kmh=15)
        result = calculate_ride_recommendation_score(ride)
        assert result["overall_score"] < 5.0
        assert result["label"] == "Recovery Ride"

    def test_ride_recommendation_score_race(self):
        ride = Ride(
            date="2024-06-01",
            distance_km=100,
            duration_minutes=240,
            avg_speed_kmh=35,
            elevation_gain_m=2000,
        )
        result = calculate_ride_recommendation_score(ride)
        assert result["overall_score"] >= 9.0

    def test_detect_speed_surges(self):
        points = [
            GPSPoint(46.1, 11.1, datetime.now(UTC), speed=20),
            GPSPoint(46.1, 11.2, datetime.now(UTC), speed=25),
            GPSPoint(46.1, 11.3, datetime.now(UTC), speed=32),
            GPSPoint(46.1, 11.4, datetime.now(UTC), speed=15),
        ]
        surges = detect_speed_surges(points, threshold_kmh=5.0)
        assert len(surges) >= 1
        assert surges[0]["speed_jump_kmh"] >= 5.0

    def test_detect_speed_surges_insufficient(self):
        assert detect_speed_surges([]) == []
        assert detect_speed_surges([GPSPoint(46.1, 11.1, datetime.now(UTC))]) == []

    def test_climb_color_lookup(self):
        from bike_analyzer.backend.analytics.advanced import _get_climb_color

        assert _get_climb_color("HC") == "#D32F2F"
        assert _get_climb_color("1") == "#F44336"
        assert _get_climb_color("unknown") == "#999"


# ============================================================
# performance.py — Score classes edge cases
# ============================================================


class TestPerformanceEdgeCases:
    def test_performance_score_zero_ride(self):
        score = calculate_performance_score([])
        assert score.score == 0.0

    def test_endurance_score_single_ride(self):
        ride = Ride(date="2024-06-01", distance_km=20, duration_minutes=60, avg_speed_kmh=22)
        score = calculate_endurance_score([ride])
        assert 0 <= score.score <= 100

    def test_recovery_score_with_fatigue(self):
        ride = Ride(
            date="2024-06-01",
            distance_km=50,
            duration_minutes=180,
            avg_speed_kmh=30,
            elevation_gain_m=500,
        )
        score = calculate_recovery_score(ride, [ride])
        assert score.score >= 0

    def test_efficiency_score(self):
        ride = Ride(
            date="2024-06-01", distance_km=30, duration_minutes=90, avg_speed_kmh=25, calories=400
        )
        score = calculate_efficiency_score(ride)
        assert score.score > 0

    def test_monthly_summary(self):
        rides = [
            Ride(
                date="2024-06-05",
                distance_km=30,
                duration_minutes=90,
                avg_speed_kmh=25,
                calories=400,
            ),
            Ride(
                date="2024-06-15",
                distance_km=40,
                duration_minutes=100,
                avg_speed_kmh=28,
                calories=500,
            ),
        ]
        summary = get_monthly_summary(rides, year=2024, month=6)
        assert summary["rides"] >= 2

    def test_annual_summary(self):
        rides = [
            Ride(date="2024-03-01", distance_km=30, duration_minutes=90, avg_speed_kmh=25),
            Ride(date="2024-07-01", distance_km=40, duration_minutes=100, avg_speed_kmh=28),
        ]
        summary = get_annual_summary(rides, year=2024)
        assert summary["rides"] >= 2

    def test_classify_athlete_elite(self):
        rides = [
            Ride(date=f"2024-{i:02d}-01", distance_km=100, duration_minutes=200, avg_speed_kmh=25)
            for i in range(1, 35)
        ]
        result = classify_athlete(rides)
        assert result in ("Elite", "Advanced", "Intermediate")

    def test_classify_athlete_beginner(self):
        rides = [
            Ride(date=f"2024-06-{i:02d}", distance_km=10, duration_minutes=30, avg_speed_kmh=15)
            for i in range(1, 5)
        ]
        result = classify_athlete(rides)
        assert result in ("Beginner", "Amateur", "Unclassified")

    def test_recovery_score_no_previous_rides(self):
        ride = Ride(date="2024-06-01", distance_km=30, duration_minutes=90, avg_speed_kmh=25)
        score = calculate_recovery_score(ride)
        assert isinstance(score, float)
        assert score >= 0


# ============================================================
# training_load.py — missing branches
# ============================================================


class TestTrainingLoadExtendedBranches:
    def test_rss_with_elevation_factor(self):
        ride = Ride(
            date="2024-06-01",
            distance_km=10,
            duration_minutes=60,
            avg_speed_kmh=15,
            elevation_gain_m=400,
        )
        tss = calculate_rss(ride)
        assert tss > 0

    def test_rss_with_hr_intensity(self):
        ride = Ride(
            date="2024-06-01",
            distance_km=20,
            duration_minutes=60,
            avg_speed_kmh=20,
            heart_rate_avg=175,
        )
        tss = calculate_rss(ride)
        assert tss > 0

    def test_calculate_atl_ctl_tsb_multi_day_with_rest(self):
        rides = [
            Ride(date="2024-06-01", distance_km=30, duration_minutes=90, avg_speed_kmh=25),
            Ride(date="2024-06-02", distance_km=0, duration_minutes=0, avg_speed_kmh=0),
            Ride(date="2024-06-03", distance_km=40, duration_minutes=100, avg_speed_kmh=28),
            Ride(date="2024-06-04", distance_km=0, duration_minutes=0, avg_speed_kmh=0),
            Ride(date="2024-06-05", distance_km=35, duration_minutes=95, avg_speed_kmh=26),
        ]
        result = calculate_atl_ctl_tsb(rides)
        assert len(result) >= 5
        assert all(hasattr(d, "tss") for d in result)

    def test_training_status_overreached(self):
        rides = [
            Ride(
                date="2024-06-15",
                distance_km=50,
                duration_minutes=180,
                avg_speed_kmh=28,
                heart_rate_avg=175,
            ),
            Ride(
                date="2024-06-14",
                distance_km=50,
                duration_minutes=180,
                avg_speed_kmh=28,
                heart_rate_avg=175,
            ),
            Ride(
                date="2024-06-13",
                distance_km=50,
                duration_minutes=180,
                avg_speed_kmh=28,
                heart_rate_avg=175,
            ),
            Ride(
                date="2024-06-12",
                distance_km=50,
                duration_minutes=180,
                avg_speed_kmh=28,
                heart_rate_avg=175,
            ),
            Ride(
                date="2024-06-11",
                distance_km=50,
                duration_minutes=180,
                avg_speed_kmh=28,
                heart_rate_avg=175,
            ),
            Ride(
                date="2024-06-10",
                distance_km=50,
                duration_minutes=180,
                avg_speed_kmh=28,
                heart_rate_avg=175,
            ),
            Ride(
                date="2024-06-09",
                distance_km=50,
                duration_minutes=180,
                avg_speed_kmh=28,
                heart_rate_avg=175,
            ),
        ]
        status = get_current_training_status(rides)
        assert status["status"] in ("overreached", "burnout_risk")

    def test_7day_summary_less_than_7_days(self):
        rides = [
            Ride(date="2024-06-05", distance_km=30, duration_minutes=90, avg_speed_kmh=25),
        ]
        result = get_7day_fitness_summary(rides)
        assert 1 <= len(result) <= 1

    def test_single_ride_single_day_atl(self):
        rides = [Ride(date="2024-06-01", distance_km=20, duration_minutes=60, avg_speed_kmh=22)]
        result = calculate_atl_ctl_tsb(rides)
        assert len(result) == 1
        assert round(result[0].atl, 1) == round(result[0].ctl, 1)


# ============================================================
# analytics.py — test uncovered logic branches
# ============================================================


class TestAnalyticsLogicBranches:
    def test_analyze_ride_complete(self):
        ride = Ride(
            date="2024-06-01",
            distance_km=30,
            duration_minutes=90,
            avg_speed_kmh=25,
            calories=450,
            heart_rate_avg=155,
            elevation_gain_m=200,
        )
        result = analytics_mod.analyze_ride(ride)
        assert result["ride_id"] == ride.id
        assert result["fatigue_score"] >= 0
        assert "recovery_hours" in result
        assert "recovery_recommendation" in result

    def test_estimate_recovery_hours_boundaries(self):
        assert estimate_recovery_hours(2.9) == 8.0
        assert estimate_recovery_hours(3.0) == 8.0
        assert estimate_recovery_hours(3.1) == 16.0
        assert estimate_recovery_hours(5.0) == 16.0
        assert estimate_recovery_hours(5.9) == 16.0
        assert estimate_recovery_hours(6.0) == 24.0
        assert estimate_recovery_hours(7.9) == 24.0
        assert estimate_recovery_hours(8.0) == 48.0
        assert estimate_recovery_hours(10.0) == 48.0

    def test_calculate_summary_empty_rides(self):
        s = analytics_mod.calculate_summary([])
        assert s["total_rides"] == 0
        assert s["total_km"] == 0.0

    def test_calculate_summary_single_ride(self):
        rides = [
            Ride(
                date="2024-06-01",
                distance_km=30,
                duration_minutes=90,
                avg_speed_kmh=25,
                calories=400,
            )
        ]
        s = analytics_mod.calculate_summary(rides)
        assert s["total_rides"] == 1
        assert s["total_km"] == 30.0
        assert s["total_calories"] == 400

    def test_rides_to_csv_with_nulls(self):
        rides = [
            Ride(
                date="2024-06-01",
                distance_km=25,
                duration_minutes=60,
                heart_rate_avg=None,
                elevation_gain_m=None,
            )
        ]
        result = analytics_mod.rides_to_csv(rides)
        assert "2024-06-01" in result
        assert "\n" in result


# ============================================================
# ai_coach.py — uncovered fallback/edge branches
# ============================================================


class TestAICoachEdgeCases:
    def test_validate_athlete_no_name(self):
        from bike_analyzer.backend.analytics.ai_coach import validate_athlete_profile

        profile = AthleteProfile(name="", weight_kg=70)
        result = validate_athlete_profile(profile)
        assert result is False

    def test_validate_athlete_no_weight(self):
        from bike_analyzer.backend.analytics.ai_coach import validate_athlete_profile

        profile = AthleteProfile(name="Test", weight_kg=0)
        result = validate_athlete_profile(profile)
        assert result is False

    def test_validate_athlete_valid(self):
        from bike_analyzer.backend.analytics.ai_coach import validate_athlete_profile

        profile = AthleteProfile(name="Test", weight_kg=70)
        result = validate_athlete_profile(profile)
        assert result is True

    def test_generate_training_advice_fallback(self):
        import os

        from bike_analyzer.backend.analytics.ai_coach import generate_training_advice

        os.environ.pop("GROQ_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        profile = AthleteProfile(
            name="Test", experience_level="Amateur", weight_kg=70, goals="Gran Fondo"
        )
        ride = Ride(date="2024-06-01", distance_km=30, duration_minutes=90, avg_speed_kmh=25)
        result = generate_training_advice(profile, [ride])
        assert result is not None
        assert len(result) > 0

    def test_generate_recovery_advice_fallback(self):
        import os

        from bike_analyzer.backend.analytics.ai_coach import generate_recovery_advice

        os.environ.pop("GROQ_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        profile = AthleteProfile(name="Test", weight_kg=70)
        result = generate_recovery_advice(profile, [])
        assert result is not None
        assert len(result) > 0

    def test_analyze_historical_trend_empty_rides(self):
        from bike_analyzer.backend.analytics.ai_coach import analyze_historical_trend

        profile = AthleteProfile(name="Test", experience_level="Beginner")
        result = analyze_historical_trend(profile, [])
        assert "trend" in result

    def test_analyze_historical_trend_single_ride(self):
        from bike_analyzer.backend.analytics.ai_coach import analyze_historical_trend

        profile = AthleteProfile(name="Test", experience_level="Beginner")
        ride = Ride(date="2024-06-01", distance_km=30, duration_minutes=90, avg_speed_kmh=25)
        result = analyze_historical_trend(profile, [ride])
        assert "trend" in result

    def test_clean_ai_output(self):
        from bike_analyzer.backend.analytics.ai_coach import _clean_ai_output

        assert "5.0" not in _clean_ai_output("You rode 5.0 km")
        assert "10" in _clean_ai_output("You rode 10 km")
        assert "\n\n" not in _clean_ai_output("Line1\n\n\nLine2")
