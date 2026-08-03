from __future__ import annotations

from datetime import datetime, timezone

import pytest

from bike_analyzer.analytics.terrain_enrichment import TerrainEnricher
from bike_analyzer.core.models import GPSPoint


def _point(lat: float, lon: float, altitude: float | None = None) -> GPSPoint:
    return GPSPoint(
        lat=lat,
        lon=lon,
        altitude=altitude,
        timestamp=datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_enrich_ride_empty_returns_empty() -> None:
    enricher = TerrainEnricher()
    result = enricher.enrich_ride([])
    assert result == []


def test_enrich_ride_preserves_coordinates() -> None:
    enricher = TerrainEnricher()
    points = [_point(45.0, 9.0, 100.0), _point(45.001, 9.001, 110.0)]
    result = enricher.enrich_ride(points)
    assert len(result) == 2
    assert result[0].lat == 45.0
    assert result[0].lon == 9.0
    assert result[0].altitude == 100.0
    assert result[1].lat == 45.001
    assert result[1].lon == 9.001
    assert result[1].altitude == 110.0


def test_enrich_ride_slope_calculation() -> None:
    enricher = TerrainEnricher()
    points = [
        _point(45.0, 9.0, 100.0),
        _point(45.0, 9.001, 110.0),
    ]
    result = enricher.enrich_ride(points)
    assert result[1].slope_pct == pytest.approx(result[0].slope_pct, abs=0.01)
    assert result[0].slope_pct > 0.0


def test_enrich_ride_attributes_types() -> None:
    enricher = TerrainEnricher()
    points = [
        _point(45.0, 9.0, 100.0),
        _point(45.001, 9.001, 110.0),
    ]
    result = enricher.enrich_ride(points)
    for item in result:
        assert isinstance(item.surface_type, str)
        assert isinstance(item.shade, bool)
        assert isinstance(item.traffic_level, float)
        assert isinstance(item.terrain_confidence, float)


def test_enricher_snapshot_returns_list() -> None:
    enricher = TerrainEnricher()
    points = [_point(45.0, 9.0, 100.0), _point(45.001, 9.001, 110.0)]
    enricher.enrich_ride(points)
    snap = enricher.snapshot()
    assert isinstance(snap, list)


def test_enricher_h3_summary_returns_dict() -> None:
    enricher = TerrainEnricher()
    points = [_point(45.0, 9.0, 100.0), _point(45.001, 9.001, 110.0)]
    enricher.enrich_ride(points)
    summary = enricher.h3_summary()
    assert isinstance(summary, dict)
