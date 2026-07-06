
from bike_analyzer.backend.traffic.safety_analyzer import (
    _ROAD_SAFETY_WEIGHTS,
    compute_risk_score,
)


def test_compute_risk_score_empty_road_types():
    result = compute_risk_score({})
    assert "risk_score" in result
    assert "label" in result


def test_compute_risk_score_residential():
    result = compute_risk_score({"residential": 1})
    assert 0 <= result["risk_score"] <= 1
    assert result["base_score"] == _ROAD_SAFETY_WEIGHTS["residential"]


def test_compute_risk_score_bike_infra_bonus():
    result_without = compute_risk_score({"residential": 1}, has_bike_infra=False)
    result_with = compute_risk_score({"residential": 1}, has_bike_infra=True)
    assert result_with["risk_score"] >= result_without["risk_score"]


def test_compute_risk_score_incident_penalty():
    result = compute_risk_score({"residential": 1}, incident_count=10, route_length_km=1.0)
    assert result["incident_penalty"] > 0


def test_compute_risk_score_motorway_low_score():
    result = compute_risk_score({"motorway": 1})
    assert result["risk_score"] < 0.5


def test_compute_risk_score_cycleway_high_score():
    result = compute_risk_score({"cycleway": 1})
    assert result["risk_score"] > 0.7
