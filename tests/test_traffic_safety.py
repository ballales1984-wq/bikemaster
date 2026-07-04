"""Tests for traffic/safety_analyzer.py — route safety analysis."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from bike_analyzer.backend.traffic.safety_analyzer import (
    analyze_route_safety,
    compute_risk_score,
)


class TestComputeRiskScore:
    def test_empty_road_types_defaults(self):
        result = compute_risk_score({})
        assert "risk_score" in result
        assert result["label"] in ("low_risk", "medium_risk", "high_risk")

    def test_safe_cycleway(self):
        road_types = {"cycleway": 5}
        result = compute_risk_score(road_types)
        assert result["risk_score"] >= 0.7
        assert result["label"] == "low_risk"

    def test_dangerous_motorway(self):
        road_types = {"motorway": 5}
        result = compute_risk_score(road_types)
        assert result["risk_score"] < 0.5

    def test_bike_infrastructure_bonus(self):
        road_types = {"residential": 3}
        result_no_bonus = compute_risk_score(road_types, has_bike_infra=False)
        result_bonus = compute_risk_score(road_types, has_bike_infra=True)
        assert result_bonus["risk_score"] >= result_no_bonus["risk_score"]

    def test_incident_penalty(self):
        road_types = {"residential": 3}
        result_no_inc = compute_risk_score(road_types, incident_count=0, route_length_km=5.0)
        result_inc = compute_risk_score(road_types, incident_count=10, route_length_km=5.0)
        assert result_no_inc["risk_score"] > result_inc["risk_score"]

    def test_returns_expected_keys(self):
        result = compute_risk_score({"residential": 3})
        assert "risk_score" in result
        assert "label" in result
        assert "advice" in result
        assert "base_score" in result
        assert "incident_penalty" in result
        assert "dominant_road_types" in result

    def test_score_range(self):
        result = compute_risk_score({"motorway": 10}, incident_count=50, route_length_km=1.0)
        assert 0.0 <= result["risk_score"] <= 1.0

    def test_dominant_road_types_limited(self):
        road_types = {"residential": 3, "primary": 2, "secondary": 1}
        result = compute_risk_score(road_types)
        assert len(result["dominant_road_types"]) <= 5

    def test_low_risk_label(self):
        result = compute_risk_score({"cycleway": 10, "pedestrian": 5}, has_bike_infra=True)
        assert result["label"] == "low_risk"

    def test_medium_risk_label(self):
        result = compute_risk_score({"primary": 5, "secondary": 3})
        assert result["label"] in ("medium_risk", "low_risk", "high_risk")

    def test_high_risk_label(self):
        road_types = {"motorway": 5}
        result = compute_risk_score(road_types, incident_count=20, route_length_km=1.0)
        assert result["label"] == "high_risk"

    def test_short_route_penalty_scaling(self):
        road_types = {"residential": 2}
        result_long = compute_risk_score(road_types, incident_count=5, route_length_km=50.0)
        result_short = compute_risk_score(road_types, incident_count=5, route_length_km=1.0)
        assert result_short["incident_penalty"] >= result_long["incident_penalty"]

    def test_advice_matches_label(self):
        result = compute_risk_score({"residential": 3})
        valid_advice = {
            "low_risk": "Percorso sicuro",
            "medium_risk": "Attenzione: alcune strade pericolose",
            "high_risk": "Rischio elevato: evita se possibile",
        }
        assert result["advice"] == valid_advice.get(result["label"], "")

    def test_unknown_road_type_defaults(self):
        road_types = {"mystery_road": 3}
        result = compute_risk_score(road_types)
        assert result["risk_score"] > 0.0

    def test_mixed_road_types(self):
        road_types = {"primary": 2, "residential": 3, "cycleway": 1}
        result = compute_risk_score(road_types)
        assert 0.0 < result["risk_score"] < 1.0


class TestAnalyzeRouteSafety:
    @pytest.mark.asyncio
    async def test_empty_points(self):
        result = await analyze_route_safety([])
        assert "risk_score" in result
        assert "has_bike_infrastructure" in result

    @pytest.mark.asyncio
    async def test_no_incidents(self):
        points = [{"lat": 45.0 + i * 0.001, "lon": 9.0 + i * 0.001} for i in range(5)]
        with (
            patch(
                "bike_analyzer.backend.traffic.overpass_client.get_road_type_summary",
                new_callable=AsyncMock,
                return_value={"residential": 3},
            ),
            patch(
                "bike_analyzer.backend.traffic.overpass_client.fetch_bike_lanes",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await analyze_route_safety(points, incidents=[])
            assert "risk_score" in result
            assert result["incident_count"] == 0

    @pytest.mark.asyncio
    async def test_with_incidents(self):
        points = [{"lat": 45.0 + i * 0.001, "lon": 9.0 + i * 0.001} for i in range(5)]
        incidents = [{"id": 1, "severity": "high"}]
        with (
            patch(
                "bike_analyzer.backend.traffic.overpass_client.get_road_type_summary",
                new_callable=AsyncMock,
                return_value={"residential": 3},
            ),
            patch(
                "bike_analyzer.backend.traffic.overpass_client.fetch_bike_lanes",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await analyze_route_safety(points, incidents=incidents)
            assert result["incident_count"] == 1

    @pytest.mark.asyncio
    async def test_returns_route_length(self):
        points = [{"lat": 45.0 + i * 0.01, "lon": 9.0 + i * 0.01} for i in range(5)]
        with (
            patch(
                "bike_analyzer.backend.traffic.overpass_client.get_road_type_summary",
                new_callable=AsyncMock,
                return_value={"residential": 3},
            ),
            patch(
                "bike_analyzer.backend.traffic.overpass_client.fetch_bike_lanes",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await analyze_route_safety(points)
            assert "route_length_km" in result
            assert result["route_length_km"] > 0
