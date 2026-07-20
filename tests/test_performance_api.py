"""Test API e service di analisi prestazioni (NP/FTP/TSS)."""

from __future__ import annotations

from datetime import datetime

from bike_analyzer.backend.db.database import (
    get_rides_by_athlete,
    save_athlete,
    save_ride,
)
from bike_analyzer.backend.analytics import performance_service as svc


def _make_ride(athlete_id: int, power: list[float], minutes: float = 10.0) -> int:
    gps = [
        {"power": p, "timestamp": datetime(2026, 7, 1, 8, 0, i % 60).isoformat()}
        for i, p in enumerate(power)
    ]
    return save_ride(
        {
            "athlete_id": athlete_id,
            "date": "2026-07-01",
            "distance_km": 20.0,
            "duration_minutes": minutes,
            "avg_speed_kmh": 120.0,
            "gps_points": gps,
        }
    )


def test_compute_ride_power_calculates_np_if_tss(client):
    aid = save_athlete({"name": "Perf API Athlete"})
    ride_id = _make_ride(aid, [200.0] * 300 + [100.0] * 300)
    svc.record_ftp(aid, 250.0, date="2026-07-01", source="test")

    r = client.post(f"/api/v1/performance/ride/{ride_id}/compute?athlete_id={aid}")
    assert r.status_code == 200, r.text
    body = r.json()
    m = body["metrics"]
    # NP > avg per via della finestra mobile 30s (picco a 200W)
    assert m["average_power"] == 150.0
    assert m["normalized_power"] is not None
    assert m["normalized_power"] > m["average_power"]
    assert m["intensity_factor"] is not None
    assert m["tss"] is not None

    # lo storico FTP e' leggibile
    r2 = client.get(f"/api/v1/performance/ftp?athlete_id={aid}")
    assert r2.status_code == 200
    assert r2.json()["latest_ftp"] == 250.0


def test_metrics_endpoint_returns_persisted(client):
    aid = save_athlete({"name": "Perf Metrics Athlete"})
    ride_id = _make_ride(aid, [180.0] * 600)
    svc.record_ftp(aid, 240.0, date="2026-07-01")
    client.post(f"/api/v1/performance/ride/{ride_id}/compute?athlete_id={aid}")

    r = client.get(f"/api/v1/performance/metrics?athlete_id={aid}")
    assert r.status_code == 200
    rows = r.json()["metrics"]
    assert len(rows) == 1
    assert rows[0]["normalized_power"] is not None


def test_estimate_ftp_from_test(client):
    r = client.post(
        "/api/v1/performance/ftp/estimate",
        json={"test_power": 260, "test_duration_min": 20, "ftp_fraction": 0.95},
    )
    assert r.status_code == 200
    assert r.json()["estimated_ftp"] == 247.0


def test_compute_from_stream_no_ftp(client):
    r = client.post(
        "/api/v1/performance/compute",
        json={"power_stream": [200.0] * 300 + [100.0] * 300, "duration_seconds": 600},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["normalized_power"] is not None
    # senza FTP, IF/TSS non calcolabili
    assert body["intensity_factor"] is None
    assert body["tss"] is None


def test_record_ftp_upsert(client):
    aid = save_athlete({"name": "Perf FTP Upsert"})
    r1 = client.post(
        f"/api/v1/performance/ftp?athlete_id={aid}",
        json={"ftp_watts": 230, "date": "2026-07-02", "source": "test"},
    )
    assert r1.status_code == 200
    r2 = client.post(
        f"/api/v1/performance/ftp?athlete_id={aid}",
        json={"ftp_watts": 245, "date": "2026-07-02", "source": "test"},
    )
    assert r2.status_code == 200
    history = client.get(f"/api/v1/performance/ftp?athlete_id={aid}").json()["history"]
    same_day = [h for h in history if h["date"] == "2026-07-02"]
    assert len(same_day) == 1
    assert same_day[0]["ftp_watts"] == 245


def test_recompute_all(client):
    aid = save_athlete({"name": "Perf Recompute Athlete"})
    _make_ride(aid, [200.0] * 300 + [100.0] * 300)
    _make_ride(aid, [150.0] * 600)
    svc.record_ftp(aid, 250.0, date="2026-07-01")

    r = client.post(f"/api/v1/performance/recompute?athlete_id={aid}")
    assert r.status_code == 200
    assert r.json()["processed"] == 2


def test_ride_without_power_returns_422(client):
    aid = save_athlete({"name": "Perf No Power"})
    ride_id = save_ride(
        {"athlete_id": aid, "date": "2026-07-03", "distance_km": 10.0, "gps_points": []}
    )
    r = client.post(f"/api/v1/performance/ride/{ride_id}/compute")
    assert r.status_code == 422


def test_service_calculators_direct():
    """Verifica unitaria dei calcolatori sullo stream noto."""
    from bike_analyzer.backend.analytics.performance import (
        calculate_normalized_power,
        calculate_intensity_factor,
        calculate_tss,
    )

    stream = [200.0] * 300 + [100.0] * 300
    np_value = calculate_normalized_power(stream)
    assert np_value is not None
    assert np_value > 150.0  # > avg
    if_count = calculate_intensity_factor(np_value, 250)
    assert abs(if_count - round(np_value / 250, 3)) < 1e-6
    tss = calculate_tss(np_value, 250, 600, if_count)
    assert tss is not None and tss > 0
    # stream troppo corto -> None
    assert calculate_normalized_power([100.0] * 5) is None
