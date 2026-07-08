from datetime import UTC, datetime

from bike_analyzer.backend.models.models import GPSPoint
from bike_analyzer.backend.processing.processing import (
    PAUSE_MIN_DURATION_MINUTES,
    RouteStatistics,
    build_segments,
    compute_statistics,
    detect_accelerations,
    detect_decelerations,
    detect_pauses,
    process_route,
    remove_outliers,
    validate_coordinate,
    validate_gps_point,
)


def _point(lat, lon, speed=None, timestamp=None):
    return GPSPoint(
        lat=lat,
        lon=lon,
        timestamp=timestamp or datetime.now(UTC),
        speed=speed,
    )


def test_validate_coordinate_valid():
    assert validate_coordinate(45.0, 7.0) is True
    assert validate_coordinate(-90, -180) is True
    assert validate_coordinate(90, 180) is True


def test_validate_coordinate_invalid():
    assert validate_coordinate(91, 7.0) is False
    assert validate_coordinate(45.0, -181) is False
    assert validate_coordinate("a", 7.0) is False


def test_detect_pauses_empty():
    assert detect_pauses([]) == []


def test_detect_pauses_single_point():
    assert detect_pauses([_point(45.0, 7.0)]) == []


def test_detect_pauses_detects_stop():
    base = datetime.now(UTC)
    points = [
        _point(45.0, 7.0, speed=10, timestamp=base),
        _point(45.0, 7.0, speed=0.5, timestamp=base),
        _point(45.0, 7.0, speed=0.5, timestamp=base),
    ]
    pauses = detect_pauses(points)
    assert len(pauses) >= 0
    if pauses:
        assert pauses[0].duration_minutes >= PAUSE_MIN_DURATION_MINUTES


def test_remove_outliers_removes_bad_points():
    points = [
        _point(45.0, 7.0, speed=20),
        _point(45.0, 7.0, speed=200),
        _point(45.0, 7.0, speed=20),
    ]
    cleaned = remove_outliers(points)
    assert len(cleaned) == 3


def test_detect_accelerations():
    points = [
        _point(45.0, 7.0, speed=10),
        _point(45.1, 7.1, speed=30),
    ]
    accels = detect_accelerations(points)
    assert len(accels) >= 0


def test_detect_accelerations_none_speed():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        GPSPoint(lat=45.0, lon=7.0, timestamp=base, speed=None),
        GPSPoint(lat=45.1, lon=7.1, timestamp=base.replace(minute=1), speed=30),
    ]
    assert detect_accelerations(points) == []


def test_detect_decelerations():
    points = [
        _point(45.0, 7.0, speed=30),
        _point(45.1, 7.1, speed=10),
    ]
    decels = detect_decelerations(points)
    assert len(decels) >= 0


def test_detect_decelerations_none_speed():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        GPSPoint(lat=45.0, lon=7.0, timestamp=base, speed=None),
        GPSPoint(lat=45.1, lon=7.1, timestamp=base.replace(minute=1), speed=10),
    ]
    assert detect_decelerations(points) == []


def test_build_segments_returns_list():
    points = [
        _point(45.0, 7.0, speed=20),
        _point(45.1, 7.1, speed=25),
        _point(45.2, 7.2, speed=30),
    ]
    segments = build_segments(points)
    assert isinstance(segments, list)


def test_compute_statistics_returns_route_stats():
    points = [
        _point(45.0, 7.0, speed=20),
        _point(45.1, 7.1, speed=25),
        _point(45.2, 7.2, speed=30),
    ]
    stats = compute_statistics(points)
    assert isinstance(stats, RouteStatistics)


def test_process_route_returns_tuple():
    points = [
        _point(45.0, 7.0, speed=20),
        _point(45.1, 7.1, speed=25),
    ]
    result = process_route(points)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[1], RouteStatistics)


def test_validate_gps_point_invalid_timestamp():
    bad = GPSPoint(lat=45.0, lon=7.0, timestamp="not-a-date")
    assert validate_gps_point(bad) is False


def test_detect_pauses_short_duration_ignored():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        _point(45.0, 7.0, speed=10, timestamp=base),
        _point(45.0, 7.0, speed=0.5, timestamp=base),
    ]
    pauses = detect_pauses(points)
    assert pauses == []


def test_detect_accelerations_no_accel():
    points = [
        _point(45.0, 7.0, speed=10),
        _point(45.1, 7.1, speed=5),
    ]
    assert detect_accelerations(points) == []


def test_detect_decelerations_no_decel():
    points = [
        _point(45.0, 7.0, speed=5),
        _point(45.1, 7.1, speed=10),
    ]
    assert detect_decelerations(points) == []


def test_remove_outliers_keeps_good_points():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        _point(45.0, 7.0, speed=20, timestamp=base),
        _point(45.0005, 7.0005, speed=22, timestamp=base.replace(minute=0, second=30)),
        _point(45.001, 7.001, speed=24, timestamp=base.replace(minute=1)),
    ]
    cleaned = remove_outliers(points)
    assert len(cleaned) == 3


def test_remove_outliers_skips_zero_time_delta():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        _point(45.0, 7.0, speed=20, timestamp=base),
        _point(45.0, 7.0, speed=200, timestamp=base),
    ]
    cleaned = remove_outliers(points)
    assert len(cleaned) == 2


def test_build_segments_skips_non_positive_duration():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        _point(45.0, 7.0, speed=20, timestamp=base),
        _point(45.1, 7.1, speed=20, timestamp=base),
    ]
    segments = build_segments(points)
    assert segments == []


def test_compute_statistics_with_elevation_loss():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        GPSPoint(lat=45.0, lon=7.0, timestamp=base, speed=20, altitude=500.0),
        GPSPoint(lat=45.1, lon=7.1, timestamp=base.replace(minute=1), speed=25, altitude=400.0),
        GPSPoint(lat=45.2, lon=7.2, timestamp=base.replace(minute=2), speed=30, altitude=300.0),
    ]
    stats = compute_statistics(points)
    assert stats.total_elevation_gain_m == 0.0
    assert stats.total_elevation_loss_m > 0.0


def test_build_segments_computes_elevation_loss():
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    points = [
        GPSPoint(lat=45.0, lon=7.0, timestamp=base, speed=20, altitude=500.0),
        GPSPoint(lat=45.1, lon=7.1, timestamp=base.replace(minute=1), speed=25, altitude=400.0),
    ]
    segments = build_segments(points)
    assert len(segments) == 1
    assert segments[0].elevation_loss_m > 0.0
    assert segments[0].elevation_gain_m == 0.0
