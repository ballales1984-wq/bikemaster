from datetime import UTC, datetime

from bike_analyzer.backend.analytics.inactivity_estimator import estimate_inactivity


def _ride(date_str):
    return type("Ride", (), {"date": date_str, "duration_minutes": 60, "distance_km": 25, "avg_speed_kmh": 25})()


def test_no_rides_high_inactivity():
    result = estimate_inactivity([])
    assert result.current_streak_days == 999
    assert result.estimated_ftp_loss_pct > 0
    assert "easy" in result.advice.lower()


def test_recent_ride_no_loss():
    today = datetime.now(UTC).strftime("%Y-%m-%dT10:00:00+00:00")
    result = estimate_inactivity([_ride(today)])
    assert result.current_streak_days <= 3
    assert result.estimated_ftp_loss_pct == 0.0


def test_week_break_moderate_loss():
    base = datetime.now(UTC)
    last_ride = base.replace(day=base.day - 5).isoformat()
    result = estimate_inactivity([_ride(last_ride)])
    assert 2.0 <= result.estimated_ftp_loss_pct <= 5.0
    assert result.recovery_plan_days > 0


def test_long_inactivity_significant_loss():
    base = datetime.now(UTC)
    last_ride = base.replace(month=1).isoformat()
    result = estimate_inactivity([_ride(last_ride)])
    assert result.estimated_ftp_loss_pct >= 10.0
    assert result.estimated_endurance_loss_pct >= 15.0
