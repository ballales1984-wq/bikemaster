"""Tests for serpapi_maps module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from bike_analyzer.backend.maps.serpapi_maps import (
    _wait_for_rate_limit,
    get_local_results,
    search_nearby,
    search_places,
)
import bike_analyzer.backend.maps.serpapi_maps as sm


class TestWaitForRateLimit:
    def test_no_sleep_needed(self, monkeypatch):
        monkeypatch.setattr("bike_analyzer.backend.maps.serpapi_maps._serpapi_last_request_ts", 0.0)
        with patch("time.sleep") as mock_sleep:
            _wait_for_rate_limit()
            mock_sleep.assert_not_called()

    def test_sleep_needed(self, monkeypatch):
        monkeypatch.setattr(
            "bike_analyzer.backend.maps.serpapi_maps._serpapi_last_request_ts",
            time.time() - 0.5,
        )
        with patch("time.sleep") as mock_sleep:
            _wait_for_rate_limit()
            mock_sleep.assert_called_once()


class TestSearchPlaces:
    def test_no_api_key(self, monkeypatch):
        monkeypatch.setattr(sm._s, "serpapi_api_key", "")
        result = search_places("cafe")
        assert result is None

    def test_no_coords(self, monkeypatch):
        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        with patch("bike_analyzer.backend.maps.serpapi_maps.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"local_results": []}
            mock_get.return_value = mock_resp
            with patch("bike_analyzer.backend.maps.serpapi_maps._wait_for_rate_limit"):
                result = search_places("cafe")
            assert result is not None

    def test_with_coords(self, monkeypatch):
        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        with patch("bike_analyzer.backend.maps.serpapi_maps.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"local_results": [{"name": "Cafe"}]}
            mock_get.return_value = mock_resp
            with patch("bike_analyzer.backend.maps.serpapi_maps._wait_for_rate_limit"):
                result = search_places("cafe", lat=45.0, lon=9.0)
            assert result is not None
            call_kwargs = mock_get.call_args.kwargs
            assert "ll" in call_kwargs["params"]
            assert "nearby" in call_kwargs["params"]

    def test_rate_limit_429(self, monkeypatch):
        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        with patch("bike_analyzer.backend.maps.serpapi_maps.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_get.return_value = mock_resp
            with patch("bike_analyzer.backend.maps.serpapi_maps._wait_for_rate_limit"):
                result = search_places("cafe")
            assert result is None

    def test_forbidden_403(self, monkeypatch):
        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        with patch("bike_analyzer.backend.maps.serpapi_maps.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_get.return_value = mock_resp
            with patch("bike_analyzer.backend.maps.serpapi_maps._wait_for_rate_limit"):
                result = search_places("cafe")
            assert result is None

    def test_request_exception(self, monkeypatch):
        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        import requests

        with patch(
            "bike_analyzer.backend.maps.serpapi_maps.requests.get",
            side_effect=requests.ConnectionError("Network error"),
        ):
            with patch("bike_analyzer.backend.maps.serpapi_maps._wait_for_rate_limit"):
                result = search_places("cafe")
            assert result is None

    def test_error_status_code(self, monkeypatch):
        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        with patch("bike_analyzer.backend.maps.serpapi_maps.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = False
            mock_resp.status_code = 500
            mock_get.return_value = mock_resp
            with patch("bike_analyzer.backend.maps.serpapi_maps._wait_for_rate_limit"):
                result = search_places("cafe")
            assert result is None


class TestGetLocalResults:
    def test_no_points(self):
        result = get_local_results([])
        assert result is None

    def test_with_points_no_data(self, monkeypatch):
        from bike_analyzer.backend.models.models import GPSPoint

        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        points = [GPSPoint(lat=45.0, lon=9.0, timestamp=None)]
        with patch("bike_analyzer.backend.maps.serpapi_maps.search_places", return_value=None):
            result = get_local_results(points)
            assert result is None

    def test_with_points_returns_local_results(self, monkeypatch):
        from bike_analyzer.backend.models.models import GPSPoint

        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        points = [GPSPoint(lat=45.0, lon=9.0, timestamp=None)]
        mock_data = {"local_results": [{"name": "Cafe"}]}
        with patch("bike_analyzer.backend.maps.serpapi_maps.search_places", return_value=mock_data):
            result = get_local_results(points, query="cafe")
            assert len(result) == 1

    def test_falls_back_to_places_results(self, monkeypatch):
        from bike_analyzer.backend.models.models import GPSPoint

        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        points = [GPSPoint(lat=45.0, lon=9.0, timestamp=None)]
        mock_data = {"places_results": [{"name": "Cafe"}]}
        with patch("bike_analyzer.backend.maps.serpapi_maps.search_places", return_value=mock_data):
            result = get_local_results(points, query="cafe")
            assert len(result) == 1

    def test_empty_local_results(self, monkeypatch):
        from bike_analyzer.backend.models.models import GPSPoint

        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        points = [GPSPoint(lat=45.0, lon=9.0, timestamp=None)]
        mock_data = {"local_results": []}
        with patch("bike_analyzer.backend.maps.serpapi_maps.search_places", return_value=mock_data):
            result = get_local_results(points)
            assert result == []


class TestSearchNearby:
    def test_no_points(self):
        result = search_nearby([], "cafe")
        assert result is None

    def test_with_points(self, monkeypatch):
        from bike_analyzer.backend.models.models import GPSPoint

        monkeypatch.setattr(sm._s, "serpapi_api_key", "key_abc")
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp=None),
            GPSPoint(lat=45.1, lon=9.1, timestamp=None),
        ]
        mock_data = {"local_results": []}
        with patch("bike_analyzer.backend.maps.serpapi_maps.search_places", return_value=mock_data):
            result = search_nearby(points, "cafe")
            assert result == mock_data
