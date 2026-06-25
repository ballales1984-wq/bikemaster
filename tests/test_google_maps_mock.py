"""Test Google Maps API (mock mode)."""

import os
from datetime import UTC, datetime

from bike_analyzer.backend.maps.google_maps import (
    _build_speed_segments,
    _css_to_google_hex,
    _interpolate_color,
    _speed_to_color,
    build_speed_colored_path,
    create_google_static_map,
    get_google_api_key,
)
from bike_analyzer.backend.models.models import GPSPoint


def test_get_google_api_key_no_env():
    key = get_google_api_key()
    assert key is None or isinstance(key, str)


def test_interpolate_color_bounds():
    assert _interpolate_color(0, 0, 35) == "#ff0000"
    assert _interpolate_color(35, 0, 35) == "#00ff00"
    assert _interpolate_color(17.5, 0, 35) == "#ffff00"


def test_interpolate_color_mid_range():
    color = _interpolate_color(10, 0, 35)
    assert color.startswith("#")
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    assert r == 255
    assert g > 0


def test_interpolate_color_high_range():
    color = _interpolate_color(30, 0, 35)
    assert color.startswith("#")
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    assert g == 255
    assert r > 0


def test_interpolate_color_same_bounds():
    assert _interpolate_color(10, 10, 10).lower() == "#ffff00"


def test_css_to_google_hex():
    assert _css_to_google_hex("#FF0000") == "0xFF0000"
    assert _css_to_google_hex("0x00FF00") == "0x00FF00"
    assert _css_to_google_hex("#88cc00") == "0x88CC00"


def test_speed_to_color_none():
    assert _speed_to_color(None) == "#4488ff"


def test_speed_to_color_thresholds():
    assert _speed_to_color(3) == "#ee3333"
    assert _speed_to_color(5) == "#ee8800"
    assert _speed_to_color(15) == "#ddbb00"
    assert _speed_to_color(25) == "#88cc00"
    assert _speed_to_color(35) == "#00cc44"
    assert _speed_to_color(50) == "#00cc44"


def test_build_speed_segments():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC), speed=30),
        GPSPoint(lat=45.02, lon=9.02, timestamp=datetime(2024, 1, 1, 0, 2, tzinfo=UTC), speed=None),
    ]
    segs = _build_speed_segments(points)
    assert len(segs) >= 1
    for seg in segs:
        assert seg.color.startswith("#")


def test_build_speed_segments_empty():
    assert _build_speed_segments([]) == []


def test_build_speed_segments_single_point():
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=10)]
    segs = _build_speed_segments(points)
    assert len(segs) == 1


def test_build_speed_segments_all_same_speed():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC), speed=10),
    ]
    segs = _build_speed_segments(points)
    assert len(segs) == 1
    assert segs[0].color.startswith("#")


def test_build_speed_segments_min_segment_boundary():
    points = [
        GPSPoint(
            lat=45.0 + i * 0.01,
            lon=9.0 + i * 0.01,
            timestamp=datetime(2024, 1, 1, i, 0, tzinfo=UTC),
            speed=10 if i < 3 else 30,
        )
        for i in range(10)
    ]
    segs = _build_speed_segments(points, min_segment=5)
    assert len(segs) >= 1


def test_create_google_static_map_basic():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
    ]
    path = create_google_static_map(points, "test-api-key-mock", "test_map.png")
    assert path == "test_map.png"


def test_create_google_static_map_colored():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC), speed=30),
        GPSPoint(lat=45.02, lon=9.02, timestamp=datetime(2024, 1, 1, 0, 2, tzinfo=UTC), speed=None),
    ]
    path = create_google_static_map(
        points, "test-api-key-mock", "test_map_colored.png", colored=True
    )
    assert path == "test_map_colored.png"


def test_create_google_static_map_colored_url_overflow():
    base = datetime(2024, 1, 1, tzinfo=UTC)
    many_points = [
        GPSPoint(
            lat=45.0 + i * 0.001,
            lon=9.0 + i * 0.001,
            timestamp=base.replace(minute=(i // 60) % 60, second=i % 60),
            speed=10 + i,
        )
        for i in range(200)
    ]
    path = create_google_static_map(
        many_points, "test-api-key-mock", "test_map_overflow.png", colored=True
    )
    assert path == "test_map_overflow.png"


def test_create_google_static_map_empty_points():
    try:
        create_google_static_map([], "test-api-key-mock", "empty_map.png")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "No GPS points" in str(e)


def test_create_google_static_map_colored_branch():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC), speed=10),
    ]
    path = create_google_static_map(
        points, "test-api-key-mock", "test_map_colored2.png", colored=True
    )
    assert path == "test_map_colored2.png"


def test_build_speed_colored_path_empty():
    assert build_speed_colored_path([]) == []


def test_build_speed_colored_path_single():
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=10)]
    segs = build_speed_colored_path(points)
    assert segs == []


def test_build_speed_colored_path_basic():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC), speed=30),
        GPSPoint(lat=45.02, lon=9.02, timestamp=datetime(2024, 1, 1, 0, 2, tzinfo=UTC), speed=25),
    ]
    segs = build_speed_colored_path(points)
    assert len(segs) == 2
    assert segs[0]["start"] == [45.0, 9.0]
    assert segs[0]["end"] == [45.01, 9.01]
    assert segs[0]["color"].startswith("#")
    assert segs[0]["speed_kmh"] == 10
    assert segs[1]["speed_kmh"] == 30


def test_build_speed_colored_path_gradient():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=0),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC), speed=35),
    ]
    segs = build_speed_colored_path(points)
    assert len(segs) == 1
    assert segs[0]["color"] == "#ff0000"
    assert segs[0]["start"] == [45.0, 9.0]
    assert segs[0]["end"] == [45.01, 9.01]


def test_create_google_elevation_chart_no_points():
    from bike_analyzer.backend.maps.google_maps import create_google_elevation_chart

    result = create_google_elevation_chart([], "test-api-key-mock")
    assert result is None


def test_init_chroma_db_error():
    """Test init_chroma_db when chromadb is available but path missing."""
    try:
        from bike_analyzer.backend.analytics.knowledge_base import init_chroma_db

        result = init_chroma_db()
        assert "status" in result
    except ImportError:
        pass


def test_map_renderer_no_folium_import_at_module_level():
    """Verify folium is not imported at module load time (lazy import)."""
    import sys

    before = set(sys.modules.keys())
    import importlib

    importlib.import_module("bike_analyzer.backend.maps.map_renderer")
    after = set(sys.modules.keys())
    new_mods = after - before
    assert "folium" not in new_mods, "folium should be lazily imported, not at module level"


def test_map_renderer_folium_loaded_after_call():
    """Verify folium is imported when create_route_map is called."""
    import sys
    from datetime import UTC, datetime

    from bike_analyzer.backend.maps.map_renderer import create_route_map
    from bike_analyzer.backend.models.models import GPSPoint

    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
    ]
    path = create_route_map(points, output_path="test_lazy_folium.html")
    assert path == "test_lazy_folium.html"
    assert "folium" in sys.modules, "folium should be loaded after create_route_map call"


def teardown_function():
    for f in ["test_map.png", "test_map_colored.png", "test_map_colored2.png", "empty_map.png",
              "test_map_overflow.png", "test_lazy_folium.html"]:
        if os.path.exists(f):
            os.remove(f)
