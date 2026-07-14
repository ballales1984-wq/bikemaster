from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.maps.google_maps import (
    _build_speed_segments,
    _css_to_google_hex,
    _interpolate_color,
    _speed_to_color,
    build_speed_colored_path,
    create_google_elevation_chart,
    create_google_static_map,
    get_google_api_key,
)
from bike_analyzer.backend.models.models import GPSPoint


def _pt(lat=45.0, lon=7.0, speed=25.0):
    return GPSPoint(lat=lat, lon=lon, timestamp=datetime.now(UTC), speed=speed)


def test_interpolate_color_midpoint():
    assert _interpolate_color(50, 0, 100) == "#ffff00"


def test_interpolate_color_equal_min_max():
    assert _interpolate_color(10, 10, 10) == "#FFFF00"


def test_speed_to_color_thresholds():
    assert _speed_to_color(40) == "#00cc44"
    assert _speed_to_color(30) == "#88cc00"
    assert _speed_to_color(20) == "#ddbb00"
    assert _speed_to_color(10) == "#ee8800"
    assert _speed_to_color(3) == "#ee3333"
    assert _speed_to_color(None) == "#4488ff"


def test_build_speed_segments_empty():
    assert _build_speed_segments([]) == []


def test_build_speed_segments_single_point():
    pts = [_pt(45.0, 7.0, 25.0)]
    segs = _build_speed_segments(pts)
    assert len(segs) == 1
    assert segs[0].points == [(45.0, 7.0)]


def test_build_speed_segments_multiple_segments():
    pts = [
        _pt(45.0, 7.0, 10.0),
        _pt(45.1, 7.1, 10.0),
        _pt(45.2, 7.2, 30.0),
        _pt(45.3, 7.3, 30.0),
    ]
    segs = _build_speed_segments(pts, min_segment=2)
    assert len(segs) >= 1


def test_build_speed_colored_path_empty():
    assert build_speed_colored_path([]) == []


def test_build_speed_colored_path_short():
    assert build_speed_colored_path([_pt(45.0, 7.0, 25.0)]) == []


def test_build_speed_colored_path_two_points():
    pts = [_pt(45.0, 7.0, 25.0), _pt(45.1, 7.1, 30.0)]
    segs = build_speed_colored_path(pts)
    assert len(segs) == 1
    assert segs[0]["start"] == [45.0, 7.0]
    assert segs[0]["end"] == [45.1, 7.1]


def test_css_to_google_hex_with_hash():
    assert _css_to_google_hex("#4488ff") == "0x4488FF"


def test_css_to_google_hex_without_hash():
    assert _css_to_google_hex("4488ff") == "0x4488FF"


def test_css_to_google_hex_with_0x_prefix():
    assert _css_to_google_hex("0x4488ff") == "0x4488ff"


def test_create_google_static_map_mock_key(tmp_path):
    pts = [_pt(45.0, 7.0, 25.0), _pt(45.1, 7.1, 30.0)]
    out = tmp_path / "map.png"
    result = create_google_static_map(pts, "test-mock-key", output_path=str(out), colored=True)
    assert result == str(out)
    assert out.exists()


def test_create_google_static_map_no_points():
    with pytest.raises(ValueError, match="No GPS points"):
        create_google_static_map([], "test-key")


def test_create_google_static_map_rate_limit():
    pts = [_pt(45.0, 7.0, 25.0), _pt(45.1, 7.1, 30.0)]
    with patch("bike_analyzer.backend.maps.google_maps.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_client.get.return_value = mock_resp
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            create_google_static_map(pts, "AIzaRealKey", output_path="out.png")


def test_create_google_static_map_403_error():
    pts = [_pt(45.0, 7.0, 25.0), _pt(45.1, 7.1, 30.0)]
    with patch("bike_analyzer.backend.maps.google_maps.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_client.get.return_value = mock_resp
        with pytest.raises(RuntimeError, match="quota exceeded or invalid key"):
            create_google_static_map(pts, "AIzaRealKey", output_path="out.png")


def test_create_google_static_map_success_download():
    pts = [_pt(45.0, 7.0, 25.0), _pt(45.1, 7.1, 30.0)]
    out_path = Path("test_success_map.png")
    try:
        with patch("bike_analyzer.backend.maps.google_maps.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"fake_png_data"
            mock_client.get.return_value = mock_resp
            result = create_google_static_map(pts, "AIzaRealKey", output_path=str(out_path))
            assert result == str(out_path)
            assert out_path.exists()
            assert out_path.read_bytes() == b"fake_png_data"
    finally:
        if out_path.exists():
            out_path.unlink()


def test_create_google_static_map_colored_fallback_long_url():
    pts = [_pt(45.0 + i * 0.001, 7.0 + i * 0.001, speed=float(i % 40)) for i in range(200)]
    out_path = Path("test_long_map.png")
    try:
        with patch("bike_analyzer.backend.maps.google_maps.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"fake_png_data"
            mock_client.get.return_value = mock_resp
            result = create_google_static_map(pts, "AIzaRealKey", output_path=str(out_path), colored=True)
            assert result == str(out_path)
    finally:
        if out_path.exists():
            out_path.unlink()


def test_create_google_elevation_chart_mock():
    pts = [_pt(45.0, 7.0, 25.0)]
    long_key = "AIza" + "a" * 30
    with patch("bike_analyzer.backend.maps.google_maps.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [{"elevation": 100.0}]}
        mock_client.get.return_value = mock_resp
        result = create_google_elevation_chart(pts, long_key)
        assert result == [100.0]


def test_create_google_elevation_chart_invalid_key():
    pts = [_pt(45.0, 7.0, 25.0)]
    result = create_google_elevation_chart(pts, "short-key")
    assert result is None


def test_create_google_elevation_chart_non_200():
    pts = [_pt(45.0, 7.0, 25.0)]
    long_key = "AIza" + "a" * 30
    with patch("bike_analyzer.backend.maps.google_maps.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.get.return_value = mock_resp
        result = create_google_elevation_chart(pts, long_key)
        assert result is None


def test_get_google_api_key_from_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    import bike_analyzer.backend.maps.google_maps as gm

    monkeypatch.setattr(gm._s, "google_maps_api_key", "abc")
    assert get_google_api_key() == "abc"
