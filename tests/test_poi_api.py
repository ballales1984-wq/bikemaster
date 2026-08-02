"""Tests for the Points of Interest (POI) API endpoints."""

import os

from starlette.testclient import TestClient

from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


def _make_client(db_path: str, subject: str = "0", is_admin: bool = True):
    from bike_analyzer.backend.api.app_factory import create_app

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    app = create_app()
    client = TestClient(app)
    token = create_access_token(subject=subject, is_admin=is_admin)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def _sample_poi(lat=45.4642, lon=9.19):
    return {
        "name": "Fontana di Test",
        "description": "Acqua fresca per i ciclisti",
        "lat": lat,
        "lon": lon,
        "type": "fontana",
        "photos": ["https://example.com/a.jpg"],
        "tags": ["utile", "acqua"],
    }


def test_create_and_list_pois(db_path):
    client = _make_client(db_path)
    resp = client.post("/api/v1/maps/pois", json=_sample_poi())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Fontana di Test"
    assert data["created_by"] == 0
    poi_id = data["id"]

    listing = client.get("/api/v1/maps/pois").json()
    assert any(p["id"] == poi_id for p in listing["pois"])

    single = client.get(f"/api/v1/maps/pois/{poi_id}").json()
    assert single["id"] == poi_id
    assert single["tags"] == ["utile", "acqua"]


def test_create_requires_auth(db_path):
    from bike_analyzer.backend.api.app_factory import create_app

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    client = TestClient(create_app())
    resp = client.post("/api/v1/maps/pois", json=_sample_poi())
    assert resp.status_code == 401


def test_invalid_poi_type_rejected(db_path):
    client = _make_client(db_path)
    payload = _sample_poi()
    payload["type"] = "not_a_real_type"
    resp = client.post("/api/v1/maps/pois", json=payload)
    assert resp.status_code == 422


def test_nearby_pois(db_path):
    client = _make_client(db_path)
    client.post("/api/v1/maps/pois", json=_sample_poi(lat=45.4642, lon=9.19))
    near = client.get("/api/v1/maps/pois/nearby", params={"lat": 45.4642, "lon": 9.19, "radius": 5})
    assert near.status_code == 200
    assert len(near.json()["pois"]) == 1

    far = client.get("/api/v1/maps/pois/nearby", params={"lat": 41.9, "lon": 12.5, "radius": 5})
    assert len(far.json()["pois"]) == 0


def test_nearby_requires_auth(db_path):
    from bike_analyzer.backend.api.app_factory import create_app

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    anon = TestClient(create_app())
    resp = anon.get(
        "/api/v1/maps/pois/nearby",
        params={"lat": 45.4642, "lon": 9.19, "radius": 5},
    )
    assert resp.status_code == 401


def test_delete_poi_owner_or_admin(db_path):
    owner = _make_client(db_path, subject="42", is_admin=False)
    create = owner.post("/api/v1/maps/pois", json=_sample_poi())
    assert create.status_code == 200
    poi_id = create.json()["id"]

    # Another non-admin cannot delete it.
    other = _make_client(db_path, subject="99", is_admin=False)
    forbidden = other.delete(f"/api/v1/maps/pois/{poi_id}")
    assert forbidden.status_code == 403

    # Owner can delete it.
    ok = owner.delete(f"/api/v1/maps/pois/{poi_id}")
    assert ok.status_code == 200
    assert ok.json()["deleted"] is True

    gone = owner.get(f"/api/v1/maps/pois/{poi_id}")
    assert gone.status_code == 404


def test_itinerary_crud(db_path):
    client = _make_client(db_path)
    from bike_analyzer.backend.db import database as db_mod

    db_mod.save_athlete(
        {"username": "itest", "email": "a@b.c", "name": "I Test", "age": 30, "weight_kg": 75, "goals": "x"},
        athlete_id=0,
    )
    created = client.post(
        "/api/v1/itineraries",
        json={"name": "Tour Test", "start_date": "2026-07-20", "end_date": "2026-07-22"},
    )
    assert created.status_code == 200, created.text
    it_id = created.json()["id"]
    assert created.json()["name"] == "Tour Test"

    one = client.get(f"/api/v1/itineraries/{it_id}").json()
    assert one["itinerary"]["id"] == it_id
    assert one["stages"] == []

    stage = client.post(
        f"/api/v1/itineraries/{it_id}/stages",
        json={"stage_day": 1, "title": "Tappa 1", "distance_km": 40, "elevation_gain_m": 500},
    )
    assert stage.status_code == 200, stage.text
    one2 = client.get(f"/api/v1/itineraries/{it_id}").json()
    assert len(one2["stages"]) == 1
    assert one2["stages"][0]["title"] == "Tappa 1"

    lst = client.get("/api/v1/itineraries").json()
    assert any(i["id"] == it_id for i in lst["itineraries"])


def test_stage_poi_link(db_path):
    """A stage can be linked to a POI; the link (and estimated fields) round-trip."""
    from bike_analyzer.backend.db import database as db_mod

    client = _make_client(db_path)
    db_mod.save_athlete(
        {"username": "poilink", "email": "p@b.c", "name": "POI Link", "age": 30, "weight_kg": 75, "goals": "x"},
        athlete_id=0,
    )

    it = client.post(
        "/api/v1/itineraries",
        json={"name": "Tour POI Link", "start_date": "2026-07-20", "end_date": "2026-07-22"},
    )
    assert it.status_code == 200, it.text
    it_id = it.json()["id"]

    poi = client.post("/api/v1/maps/pois", json=_sample_poi())
    assert poi.status_code == 200, poi.text
    poi_id = poi.json()["id"]

    stage = client.post(
        f"/api/v1/itineraries/{it_id}/stages",
        json={
            "stage_day": 1,
            "title": "Tappa POI",
            "distance_km": 30,
            "elevation_gain_m": 200,
            "estimated_km": 35,
            "estimated_elevation_m": 180,
            "poi_id": poi_id,
            "notes": "legge collinare",
        },
    )
    assert stage.status_code == 200, stage.text
    assert stage.json()["poi_id"] == poi_id

    read = client.get(f"/api/v1/itineraries/{it_id}").json()
    stage_read = read["stages"][0]
    assert stage_read["poi_id"] == poi_id
    assert stage_read["estimated_km"] == 35
    assert stage_read["elevation_gain_m"] == 200
    assert stage_read["title"] == "Tappa POI"


def test_list_by_itinerary(db_path):
    client = _make_client(db_path)
    from bike_analyzer.backend.db import database as db_mod

    db_mod.save_athlete(
        {"username": "itest2", "email": "b@c.d", "name": "I2", "age": 30, "weight_kg": 75, "goals": "x"},
        athlete_id=0,
    )
    it = client.post(
        "/api/v1/itineraries",
        json={"name": "Tour POI", "start_date": "2026-07-20", "end_date": "2026-07-22"},
    )
    it_id = it.json()["id"]
    client.post("/api/v1/maps/pois", json={**_sample_poi(), "itinerary_id": it_id})
    client.post(
        "/api/v1/maps/pois",
        json={**_sample_poi(), "name": "Altro POI", "type": "vista"},
    )
    filtered = client.get("/api/v1/maps/pois", params={"itinerary_id": it_id}).json()
    assert len(filtered["pois"]) == 1
    assert filtered["pois"][0]["itinerary_id"] == it_id
