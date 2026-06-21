"""Tests for traffic/overpass_client module."""

from unittest.mock import AsyncMock, patch

import pytest

from bike_analyzer.backend.traffic.overpass_client import (
    _validate_coords,
    get_road_type_summary,
)


class TestValidateCoords:
    def test_valid_coords(self):
        points = [{"lat": 45.0, "lon": 9.0}, {"lat": 46.0, "lon": 10.0}]
        _validate_coords(points)  # Should not raise

    def test_missing_lat(self):
        with pytest.raises(ValueError, match="Missing lat/lon"):
            _validate_coords([{"lat": 45.0}])

    def test_missing_lon(self):
        with pytest.raises(ValueError, match="Missing lat/lon"):
            _validate_coords([{"lon": 9.0}])

    def test_invalid_lat_too_high(self):
        with pytest.raises(ValueError, match="Invalid coordinates"):
            _validate_coords([{"lat": 100.0, "lon": 9.0}])

    def test_invalid_lat_too_low(self):
        with pytest.raises(ValueError, match="Invalid coordinates"):
            _validate_coords([{"lat": -100.0, "lon": 9.0}])

    def test_invalid_lon_too_high(self):
        with pytest.raises(ValueError, match="Invalid coordinates"):
            _validate_coords([{"lat": 45.0, "lon": 200.0}])

    def test_invalid_lon_too_low(self):
        with pytest.raises(ValueError, match="Invalid coordinates"):
            _validate_coords([{"lat": 45.0, "lon": -200.0}])

    def test_empty_list_ok(self):
        _validate_coords([])  # Should not raise

    def test_boundary_values(self):
        _validate_coords([{"lat": 90.0, "lon": 180.0}])  # Max valid
        _validate_coords([{"lat": -90.0, "lon": -180.0}])  # Min valid


class TestGetRoadTypeSummary:
    @pytest.mark.asyncio
    async def test_summary_counts_road_types(self):
        mock_data = {
            "elements": [
                {"tags": {"highway": "primary"}},
                {"tags": {"highway": "primary"}},
                {"tags": {"highway": "secondary"}},
                {"tags": {"highway": "residential"}},
                {"tags": {"highway": "cycleway"}},
            ]
        }
        with patch(
            "bike_analyzer.backend.traffic.overpass_client.fetch_road_data",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = await get_road_type_summary([
                {"lat": 45.0, "lon": 9.0},
                {"lat": 45.1, "lon": 9.1},
            ])
        assert result["primary"] == 2
        assert result["secondary"] == 1
        assert result["residential"] == 1
        assert result["cycleway"] == 1

    @pytest.mark.asyncio
    async def test_summary_empty_data(self):
        with patch(
            "bike_analyzer.backend.traffic.overpass_client.fetch_road_data",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_road_type_summary([
                {"lat": 45.0, "lon": 9.0},
                {"lat": 45.1, "lon": 9.1},
            ])
        assert result == {}

    @pytest.mark.asyncio
    async def test_summary_no_elements_key(self):
        with patch(
            "bike_analyzer.backend.traffic.overpass_client.fetch_road_data",
            new_callable=AsyncMock,
            return_value={"elements": []},
        ):
            result = await get_road_type_summary([
                {"lat": 45.0, "lon": 9.0},
                {"lat": 45.1, "lon": 9.1},
            ])
        assert result == {}

    @pytest.mark.asyncio
    async def test_summary_unknown_highway(self):
        mock_data = {
            "elements": [
                {"tags": {"highway": "unknown_type"}},
                {"tags": {}},  # No highway tag
            ]
        }
        with patch(
            "bike_analyzer.backend.traffic.overpass_client.fetch_road_data",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = await get_road_type_summary([
                {"lat": 45.0, "lon": 9.0},
                {"lat": 45.1, "lon": 9.1},
            ])
        assert result["unknown_type"] == 1
        assert result["unknown"] == 1
