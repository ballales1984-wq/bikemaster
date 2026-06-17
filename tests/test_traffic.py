"""Tests for traffic modules: overpass_client, incident_fetcher, safety_analyzer."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# overpass_client tests
# =============================================================================


class TestValidateCoords:
    def test_valid_coords(self):
        from bike_analyzer.backend.traffic.overpass_client import _validate_coords

        points = [{"lat": 45.0, "lon": 9.0}, {"lat": 45.1, "lon": 9.1}]
        _validate_coords(points)

    def test_missing_lat_raises(self):
        from bike_analyzer.backend.traffic.overpass_client import _validate_coords

        with pytest.raises(ValueError, match="Missing lat/lon"):
            _validate_coords([{"lat": 45.0}])

    def test_missing_lon_raises(self):
        from bike_analyzer.backend.traffic.overpass_client import _validate_coords

        with pytest.raises(ValueError, match="Missing lat/lon"):
            _validate_coords([{"lon": 9.0}])

    def test_invalid_lat_raises(self):
        from bike_analyzer.backend.traffic.overpass_client import _validate_coords

        with pytest.raises(ValueError, match="Invalid coordinates"):
            _validate_coords([{"lat": 91.0, "lon": 9.0}])

    def test_invalid_lon_raises(self):
        from bike_analyzer.backend.traffic.overpass_client import _validate_coords

        with pytest.raises(ValueError, match="Invalid coordinates"):
            _validate_coords([{"lat": 45.0, "lon": -181.0}])


class TestOverpassQuery:
    @pytest.mark.asyncio
    async def test_returns_json_on_success(self):
        from bike_analyzer.backend.traffic.overpass_client import _overpass_query

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"elements": []}
        with patch("requests.post", return_value=mock_resp):
            result = await _overpass_query("[out:json];")
            assert result == {"elements": []}

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        from bike_analyzer.backend.traffic.overpass_client import _overpass_query

        mock_resp = MagicMock()
        mock_resp.ok = False
        with patch("requests.post", return_value=mock_resp):
            result = await _overpass_query("[out:json];")
            assert result is None


class TestFetchRoadData:
    @pytest.mark.asyncio
    async def test_returns_none_empty(self):
        from bike_analyzer.backend.traffic.overpass_client import fetch_road_data

        assert await fetch_road_data([]) is None
        assert await fetch_road_data([{"lat": 45.0, "lon": 9.0}]) is None

    @pytest.mark.asyncio
    async def test_builds_correct_query(self):
        from bike_analyzer.backend.traffic.overpass_client import fetch_road_data

        mock_data = {"elements": [{"type": "way", "tags": {"highway": "residential"}}]}
        with patch(
            "bike_analyzer.backend.traffic.overpass_client._overpass_query",
            return_value=mock_data,
        ):
            result = await fetch_road_data(
                [{"lat": 45.0, "lon": 9.0}, {"lat": 45.1, "lon": 9.1}]
            )
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_include_geometry_flag(self):
        from bike_analyzer.backend.traffic.overpass_client import fetch_road_data

        with patch(
            "bike_analyzer.backend.traffic.overpass_client._overpass_query",
            return_value={"elements": []},
        ):
            await fetch_road_data(
                [{"lat": 45.0, "lon": 9.0}, {"lat": 45.1, "lon": 9.1}],
                include_geometry=True,
            )


class TestFetchBikeLanes:
    @pytest.mark.asyncio
    async def test_returns_none_empty(self):
        from bike_analyzer.backend.traffic.overpass_client import fetch_bike_lanes

        assert await fetch_bike_lanes([]) is None

    @pytest.mark.asyncio
    async def test_builds_bike_query(self):
        from bike_analyzer.backend.traffic.overpass_client import fetch_bike_lanes

        with patch(
            "bike_analyzer.backend.traffic.overpass_client._overpass_query",
            return_value={"elements": []},
        ):
            await fetch_bike_lanes(
                [{"lat": 45.0, "lon": 9.0}, {"lat": 45.1, "lon": 9.1}]
            )


class TestGetRoadTypeSummary:
    @pytest.mark.asyncio
    async def test_no_elements_returns_empty(self):
        from bike_analyzer.backend.traffic.overpass_client import get_road_type_summary

        with patch(
            "bike_analyzer.backend.traffic.overpass_client.fetch_road_data",
            return_value=None,
        ):
            result = await get_road_type_summary(
                [{"lat": 45.0, "lon": 9.0}]
            )
            assert result == {}

    @pytest.mark.asyncio
    async def test_counts_road_types(self):
        from bike_analyzer.backend.traffic.overpass_client import get_road_type_summary

        mock_data = {
            "elements": [
                {"tags": {"highway": "residential"}},
                {"tags": {"highway": "residential"}},
                {"tags": {"highway": "primary"}},
                {"tags": {}},
            ]
        }
        with patch(
            "bike_analyzer.backend.traffic.overpass_client.fetch_road_data",
            return_value=mock_data,
        ):
            result = await get_road_type_summary(
                [{"lat": 45.0, "lon": 9.0}]
            )
            assert result["residential"] == 2
            assert result["primary"] == 1
            assert result.get("unknown") == 1


# =============================================================================
# incident_fetcher tests
# =============================================================================


class TestLoadLocalIncidents:
    def test_no_path_returns_empty(self, monkeypatch):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        monkeypatch.setattr(inc_mod, "_INCIDENT_DATA_PATH", "/nonexistent/path.json")
        assert inc_mod._load_local_incidents() == []

    def test_loads_json_list(self, tmp_path):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        data = [
            {"id": "1", "lat": 45.0, "lon": 9.0, "severity": "medium"},
            {"id": "2", "lat": 45.1, "lon": 9.1, "severity": "high"},
        ]
        p = tmp_path / "incidents.json"
        p.write_text(json.dumps(data))
        with patch.object(inc_mod, "_INCIDENT_DATA_PATH", str(p)):
            result = inc_mod._load_local_incidents()
            assert len(result) == 2

    def test_loads_dict_with_incidents_key(self, tmp_path):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        p = tmp_path / "incidents.json"
        p.write_text(json.dumps({"incidents": [{"id": "1"}]}))
        with patch.object(inc_mod, "_INCIDENT_DATA_PATH", str(p)):
            result = inc_mod._load_local_incidents()
            assert len(result) == 1

    def test_loads_dict_with_features_key(self, tmp_path):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        p = tmp_path / "incidents.json"
        p.write_text(
            json.dumps({"features": [{"id": "1", "properties": {}}]})
        )
        with patch.object(inc_mod, "_INCIDENT_DATA_PATH", str(p)):
            result = inc_mod._load_local_incidents()
            assert len(result) == 1

    def test_invalid_json_returns_empty(self, tmp_path):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        p = tmp_path / "bad.json"
        p.write_text("not json")
        with patch.object(inc_mod, "_INCIDENT_DATA_PATH", str(p)):
            assert inc_mod._load_local_incidents() == []


class TestFetchFromApi:
    def test_no_url_returns_empty(self, monkeypatch):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        monkeypatch.setattr(inc_mod, "_INCIDENT_API_URL", "")
        assert inc_mod._fetch_from_api(45.0, 9.0) == []

    def test_request_error_returns_empty(self, monkeypatch):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        monkeypatch.setattr(inc_mod, "_INCIDENT_API_URL", "https://example.com/api")
        with patch("requests.get", side_effect=Exception("Connection error")):
            assert inc_mod._fetch_from_api(45.0, 9.0) == []

    def test_successful_api_returns_list(self, monkeypatch):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        monkeypatch.setattr(inc_mod, "_INCIDENT_API_URL", "https://example.com/api")
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "api1", "lat": 45.0}]
        mock_resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=mock_resp):
            result = inc_mod._fetch_from_api(45.0, 9.0)
            assert len(result) == 1

    def test_api_with_api_key_header(self, monkeypatch):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        monkeypatch.setattr(inc_mod, "_INCIDENT_API_URL", "https://example.com/api")
        monkeypatch.setattr(inc_mod, "_INCIDENT_API_KEY", "secret-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=mock_resp) as mock_get:
            inc_mod._fetch_from_api(45.0, 9.0)
            headers = mock_get.call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer secret-key"


class TestNormalizeIncident:
    def test_basic_normalization(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        raw = {
            "id": "inc1",
            "lat": 45.123,
            "lon": 9.456,
            "date": "2024-06-15",
            "severity": "high",
            "description": "Road closed",
            "road_type": "secondary",
        }
        result = inc_mod._normalize_incident(raw, "test")
        assert result is not None
        assert result["id"] == "inc1"
        assert result["lat"] == 45.123
        assert result["severity"] == "high"
        assert result["source"] == "test"
        assert result["description"] == "Road closed"

    def test_generates_id_if_missing(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        raw = {"lat": 45.0, "lon": 9.0, "date": "2024-06-15"}
        result = inc_mod._normalize_incident(raw, "src")
        assert result is not None
        assert result["id"].startswith("src_")

    def test_zero_coords_returns_none(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        assert inc_mod._normalize_incident(
            {"id": "1", "lat": 0.0, "lon": 0.0}, "test"
        ) is None

    def test_invalid_severity_defaults_to_medium(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        raw = {"lat": 45.0, "lon": 9.0, "date": "2024-06-15", "severity": "extreme"}
        result = inc_mod._normalize_incident(raw, "test")
        assert result["severity"] == "medium"

    def test_datetime_date_conversion(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        raw = {"lat": 45.0, "lon": 9.0, "date": datetime(2024, 6, 15, tzinfo=UTC)}
        result = inc_mod._normalize_incident(raw, "test")
        assert result["date"] == "2024-06-15"

    def test_alternative_field_names(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        raw = {
            "codice": "X123",
            "latitude": 45.0,
            "longitude": 9.1,
            "gravita": "low",
            "descrizione": "Test incident",
        }
        result = inc_mod._normalize_incident(raw, "test")
        assert result is not None
        assert result["severity"] == "low"
        assert result["description"] == "Test incident"
        assert result["id"] == "X123"

    def test_description_truncated_to_200(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        raw = {"lat": 45.0, "lon": 9.0, "description": "x" * 500}
        result = inc_mod._normalize_incident(raw, "test")
        assert len(result["description"]) <= 200


class TestFetchIncidents:
    def test_no_sources_returns_empty(self, monkeypatch):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        monkeypatch.setattr(inc_mod, "_INCIDENT_DATA_PATH", "/nonexistent")
        monkeypatch.setattr(inc_mod, "_INCIDENT_API_URL", "")
        assert inc_mod.fetch_incidents(45.0, 9.0) == []


class TestFetchIncidentsByBbox:
    def test_delegates_to_fetch_incidents(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        with patch.object(inc_mod, "fetch_incidents", return_value=[]) as mock_fetch:
            result = inc_mod.fetch_incidents_by_bbox(45.0, 9.0, 45.1, 9.1)
            mock_fetch.assert_called_once()
            assert result == []

    def test_computes_radius_from_bbox(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        with patch.object(inc_mod, "fetch_incidents") as mock_fetch:
            inc_mod.fetch_incidents_by_bbox(45.0, 9.0, 45.1, 9.1)
            call_kwargs = mock_fetch.call_args[1]
            assert "radius_km" in call_kwargs
            assert call_kwargs["radius_km"] > 0


class TestGetIncidentStats:
    def test_empty_returns_zero(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        result = inc_mod.get_incident_stats([])
        assert result["total"] == 0
        assert result["by_severity"] == {}
        assert result["by_date"] == {}

    def test_aggregates_by_severity(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        incidents = [
            {"severity": "high", "date": "2024-06-15"},
            {"severity": "high", "date": "2024-06-15"},
            {"severity": "low", "date": "2024-06-14"},
        ]
        result = inc_mod.get_incident_stats(incidents)
        assert result["total"] == 3
        assert result["by_severity"]["high"] == 2
        assert result["by_severity"]["low"] == 1

    def test_by_date_sorted_reverse(self):
        import bike_analyzer.backend.traffic.incident_fetcher as inc_mod

        incidents = [
            {"severity": "low", "date": "2024-06-10"},
            {"severity": "medium", "date": "2024-06-15"},
            {"severity": "high", "date": "2024-06-12"},
        ]
        result = inc_mod.get_incident_stats(incidents)
        dates = list(result["by_date"].keys())
        assert dates == sorted(dates, reverse=True)


# =============================================================================
# safety_analyzer tests
# =============================================================================


class TestComputeRiskScore:
    def test_empty_road_types_defaults(self):
        from bike_analyzer.backend.traffic.safety_analyzer import compute_risk_score

        result = compute_risk_score({})
        assert 0.0 <= result["risk_score"] <= 1.0
        assert result["label"] in ("low_risk", "medium_risk", "high_risk")
        assert "advice" in result

    def test_cycleway_high_score(self):
        from bike_analyzer.backend.traffic.safety_analyzer import compute_risk_score

        result = compute_risk_score({"cycleway": 5}, has_bike_infra=True)
        assert result["risk_score"] >= 0.7
        assert result["label"] == "low_risk"

    def test_motorway_low_score(self):
        from bike_analyzer.backend.traffic.safety_analyzer import compute_risk_score

        result = compute_risk_score(
            {"motorway": 3}, incident_count=5, route_length_km=1.0
        )
        assert result["label"] == "high_risk"

    def test_bike_infra_bonus(self):
        from bike_analyzer.backend.traffic.safety_analyzer import compute_risk_score

        base = compute_risk_score({"residential": 2}, has_bike_infra=False)
        with_bonus = compute_risk_score({"residential": 2}, has_bike_infra=True)
        assert with_bonus["risk_score"] > base["risk_score"]

    def test_incident_penalty(self):
        from bike_analyzer.backend.traffic.safety_analyzer import compute_risk_score

        base = compute_risk_score(
            {"residential": 2}, incident_count=0, route_length_km=10.0
        )
        with_incidents = compute_risk_score(
            {"residential": 2}, incident_count=10, route_length_km=10.0
        )
        assert with_incidents["risk_score"] < base["risk_score"]

    def test_score_clamped(self):
        from bike_analyzer.backend.traffic.safety_analyzer import compute_risk_score

        result = compute_risk_score({"cycleway": 100}, has_bike_infra=True)
        assert 0.0 <= result["risk_score"] <= 1.0

    def test_dominant_road_types_sorted(self):
        from bike_analyzer.backend.traffic.safety_analyzer import compute_risk_score

        result = compute_risk_score(
            {"residential": 5, "primary": 2, "secondary": 3, "cycleway": 1}
        )
        types = [t[0] for t in result["dominant_road_types"]]
        assert types.index("residential") < types.index("primary")

    def test_all_expected_keys(self):
        from bike_analyzer.backend.traffic.safety_analyzer import compute_risk_score

        result = compute_risk_score({"residential": 3})
        expected_keys = {
            "risk_score",
            "label",
            "advice",
            "base_score",
            "incident_penalty",
            "dominant_road_types",
        }
        assert expected_keys.issubset(result.keys())


class TestAnalyzeRouteSafety:
    @pytest.mark.asyncio
    async def test_full_analysis(self):
        from bike_analyzer.backend.traffic.safety_analyzer import analyze_route_safety

        points = [
            {"lat": 45.0, "lon": 9.0},
            {"lat": 45.01, "lon": 9.01},
            {"lat": 45.02, "lon": 9.02},
        ]
        with patch(
            "bike_analyzer.backend.traffic.overpass_client.fetch_bike_lanes",
            return_value={"elements": []},
        ), patch(
            "bike_analyzer.backend.traffic.overpass_client.get_road_type_summary",
            return_value={"residential": 2},
        ):
            result = await analyze_route_safety(points)
            assert "risk_score" in result
