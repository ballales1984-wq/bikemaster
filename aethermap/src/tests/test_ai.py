"""Tests for aethermap.ai (Phase 3 AI researcher pipeline)."""
from __future__ import annotations

from datetime import UTC
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from aethermap.ai.ingest import (
    RawFeature,
    RawPoint,
    ingest_gpx,
    ingest_public_stub,
    ingest_satellite_stub,
    ingest_sensor_stream_stub,
)
from aethermap.ai.models import (
    Confidenza,
    Geometria,
    Oggetto,
    Posizione,
    Proposta,
    Stato,
)
from aethermap.ai.models_ml import (
    RoadPlausibilityEstimator,
    SimpleNN,
    estimate_gpx,
    extract_gpx_features,
    load_model,
    save_model,
)
from aethermap.ai.pipeline import Pipeline, WorldStore
from aethermap.ai.researcher import Researcher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_GPX = Path(__file__).resolve().parent.parent / "aethermap" / "ai" / "sample.gpx"


def _make_points(n: int = 5, lat0: float = 45.0, lon0: float = 9.0) -> list[RawPoint]:
    """Generate evenly spaced RawPoints for testing."""
    return [
        RawPoint(lat=lat0 + i * 0.001, lon=lon0 + i * 0.001, ele=100.0 + i)
        for i in range(n)
    ]


# ===========================================================================
# ai.ingest
# ===========================================================================


class TestIngestGpx:
    def test_returns_list_of_rawpoints(self):
        points = ingest_gpx(str(SAMPLE_GPX))
        assert isinstance(points, list)
        assert all(isinstance(p, RawPoint) for p in points)

    def test_correct_number_of_points(self):
        points = ingest_gpx(str(SAMPLE_GPX))
        assert len(points) == 6

    def test_point_coordinates(self):
        points = ingest_gpx(str(SAMPLE_GPX))
        assert points[0].lat == pytest.approx(45.0)
        assert points[0].lon == pytest.approx(9.0)
        assert points[-1].lat == pytest.approx(45.0025)
        assert points[-1].lon == pytest.approx(9.0030)

    def test_elevation_parsed(self):
        points = ingest_gpx(str(SAMPLE_GPX))
        assert points[0].ele == pytest.approx(120.0)
        assert points[1].ele == pytest.approx(122.0)

    def test_timestamp_parsed(self):
        points = ingest_gpx(str(SAMPLE_GPX))
        assert points[0].t is not None
        from datetime import datetime
        assert points[0].t == datetime(2026, 7, 11, 10, 0, 0, tzinfo=UTC)

    def test_empty_gpx_returns_empty_list(self, tmp_path):
        gpx = tmp_path / "empty.gpx"
        gpx.write_text(
            '<?xml version="1.0"?>'
            '<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk/></gpx>'
        )
        assert ingest_gpx(str(gpx)) == []


class TestIngestSatelliteStub:
    def test_returns_list_of_rawfeatures(self):
        feats = ingest_satellite_stub((45.0, 9.0, 46.0, 10.0))
        assert isinstance(feats, list)
        assert all(isinstance(f, RawFeature) for f in feats)

    def test_single_feature_in_bbox(self):
        feats = ingest_satellite_stub((0.0, 0.0, 1.0, 1.0))
        assert len(feats) == 1
        assert feats[0].tipo == "edificio"

    def test_centroid_in_bbox(self):
        lat0, lon0, lat1, lon1 = 10.0, 20.0, 30.0, 40.0
        feats = ingest_satellite_stub((lat0, lon0, lat1, lon1))
        lat, lon = feats[0].posizione
        assert lat0 < lat < lat1
        assert lon0 < lon < lon1

    def test_payload_contains_expected_keys(self):
        feats = ingest_satellite_stub((0.0, 0.0, 1.0, 1.0))
        assert "piani_stimati" in feats[0].payload
        assert "confidenza_sorgente" in feats[0].payload


class TestIngestPublicStub:
    def test_returns_feature_with_region_name(self):
        feats = ingest_public_stub("Lombardia")
        assert len(feats) == 1
        assert "Lombardia" in feats[0].payload["nome"]
        assert feats[0].payload["pubblico"] is True


class TestIngestSensorStreamStub:
    def test_yields_n_features(self):
        feats = list(ingest_sensor_stream_stub(3))
        assert len(feats) == 3

    def test_default_5_features(self):
        feats = list(ingest_sensor_stream_stub())
        assert len(feats) == 5

    def test_feature_type_and_payload(self):
        feats = list(ingest_sensor_stream_stub(2))
        assert all(f.tipo == "sensore_traffico" for f in feats)
        assert "traffico" in feats[0].payload

    def test_traffico_increments(self):
        feats = list(ingest_sensor_stream_stub(5))
        values = [f.payload["traffico"] for f in feats]
        # (i*20) % 100 => 0, 20, 40, 60, 80
        assert values == [0, 20, 40, 60, 80]

    def test_positions_increment(self):
        feats = list(ingest_sensor_stream_stub(3))
        for i, f in enumerate(feats):
            lat, lon = f.posizione
            assert lat == pytest.approx(45.0 + i * 0.001)
            assert lon == pytest.approx(9.0 + i * 0.001)


# ===========================================================================
# ai.models
# ===========================================================================


class TestConfidenza:
    def test_default_values(self):
        c = Confidenza()
        assert c.valore == 1.0
        assert c.incertezza_spaziale_m == 0.0
        assert c.incertezza_temporale_s == 0.0

    def test_custom_values(self):
        c = Confidenza(valore=0.75, incertezza_spaziale_m=5.0)
        assert c.valore == 0.75
        assert c.incertezza_spaziale_m == 5.0

    def test_valore_clamped_high(self):
        with pytest.raises(ValidationError):
            Confidenza(valore=1.5)

    def test_valore_clamped_low(self):
        with pytest.raises(ValidationError):
            Confidenza(valore=-0.1)


class TestPosizione:
    def test_from_latlon_populates_fields(self):
        p = Posizione.from_latlon(45.0, 9.0, 100.0)
        assert p.lat == 45.0
        assert p.lon == 9.0
        assert p.alt == 100.0
        # cube_face and s2 are derived
        assert p.cube_face is not None
        assert p.s2 is not None

    def test_s2_id_is_string(self):
        p = Posizione.from_latlon(45.0, 9.0)
        assert isinstance(p.s2, str)
        assert len(p.s2) > 0


class TestGeometria:
    def test_default(self):
        g = Geometria()
        assert g.tipo == "punto"
        assert g.dati == {}

    def test_custom_tipo(self):
        g = Geometria(tipo="linea", dati={"punti": []})
        assert g.tipo == "linea"


class TestStato:
    def test_default_timestamp(self):
        s = Stato()
        assert 0.0 <= s.confidence <= 1.0


class TestProposta:
    def test_minimal_creation(self):
        pos = Posizione.from_latlon(45.0, 9.0)
        p = Proposta(campo="traffico", valore=50, confidence=0.8, posizione=pos)
        assert p.campo == "traffico"
        assert p.valore == 50
        assert p.confidence == 0.8
        assert p.nuovo is False

    def test_nuovo_flag(self):
        pos = Posizione.from_latlon(45.0, 9.0)
        p = Proposta(campo="geometria", valore={}, confidence=0.9,
                     posizione=pos, nuovo=True)
        assert p.nuovo is True

    def test_confidence_clamped(self):
        with pytest.raises(ValidationError):
            Proposta(campo="x", valore=1, confidence=1.5, posizione=Posizione.from_latlon(0, 0))


class TestOggetto:
    def test_create_oggetto(self):
        pos = Posizione.from_latlon(45.0, 9.0)
        o = Oggetto(id="obj_001", tipo="strada", posizione=pos)
        assert o.id == "obj_001"
        assert o.tipo == "strada"
        assert o.proprieta == {}
        assert o.cronologia == []

    def test_stale_after_default_none(self):
        pos = Posizione.from_latlon(0.0, 0.0)
        o = Oggetto(id="x", tipo="x", posizione=pos)
        assert o.stale_after_s is None


# ===========================================================================
# ai.models_ml
# ===========================================================================


class TestExtractGpxFeatures:
    def test_empty_points(self):
        f = extract_gpx_features([])
        assert f.n_points == 0
        assert f.spanning_deg == 0.0

    def test_single_point(self):
        f = extract_gpx_features([RawPoint(lat=45.0, lon=9.0, ele=100.0)])
        assert f.n_points == 1
        assert f.spanning_deg == 0.0

    def test_multiple_points_span(self):
        pts = _make_points(5, lat0=45.0, lon0=9.0)
        f = extract_gpx_features(pts)
        assert f.n_points == 5
        assert f.spanning_deg > 0.0

    def test_to_vector_shape(self):
        pts = _make_points(10)
        f = extract_gpx_features(pts)
        v = f.to_vector()
        assert v.shape == (4,)

    def test_elevation_variance_nonzero(self):
        pts = [RawPoint(lat=45.0, lon=9.0, ele=float(i)) for i in range(10)]
        f = extract_gpx_features(pts)
        assert f.elevation_variance > 0.0

    def test_spatial_regularity_bounds(self):
        pts = _make_points(10)
        f = extract_gpx_features(pts)
        assert 0.0 <= f.spatial_regularity <= 1.0


class TestRoadPlausibilityEstimator:
    def test_from_synthetic_returns_fitted(self):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=40)
        assert est._fitted is True

    def test_weights_shape(self):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=40)
        assert est._w.shape == (5,)  # bias + 4 features

    def test_road_score_range(self):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=40)
        pts = _make_points(20)
        score = est.road_score(pts)
        assert 0.0 <= score <= 1.0

    def test_road_score_very_few_points(self):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=40)
        score = est.road_score([RawPoint(lat=45.0, lon=9.0)])
        assert score == 0.0

    def test_confidence_range(self):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=40)
        pts = _make_points(20)
        conf = est.confidence(pts)
        assert 0.0 <= conf <= 1.0

    def test_confidence_capped_at_0_98(self):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=40)
        pts = _make_points(200)
        conf = est.confidence(pts)
        assert conf <= 0.98

    def test_estimate_gpx_interface(self):
        plaus, conf = estimate_gpx(_make_points(15))
        assert 0.0 <= plaus <= 1.0
        assert 0.0 <= conf <= 1.0

    def test_unfitted_returns_zero_road_score(self):
        est = RoadPlausibilityEstimator(
            weights=np.zeros(5, dtype=np.float32),
            mean=np.zeros(4, dtype=np.float32),
            std=np.ones(4, dtype=np.float32),
            fitted=False,
        )
        assert est.road_score(_make_points(5)) == 0.0


class TestSimpleNN:
    def test_predict_shape(self):
        nn = SimpleNN(input_size=4)
        x = np.random.randn(3, 4).astype(np.float64)
        out = nn.predict(x)
        assert out.shape == (3, 1)

    def test_predict_range(self):
        nn = SimpleNN(input_size=4, seed=0)
        x = np.random.randn(10, 4).astype(np.float64)
        out = nn.predict(x)
        assert np.all(out >= 0.0) and np.all(out <= 1.0)

    def test_train_reduces_loss(self):
        nn = SimpleNN(input_size=4, seed=0)
        rng = np.random.default_rng(0)
        X = rng.standard_normal((32, 4)).astype(np.float64)
        y = (X[:, 0] > 0).astype(np.float64).reshape(-1, 1)
        hist = nn.fit(X, y, epochs=50, batch_size=8, lr=0.05, val_split=0.25)
        assert hist["train_loss"][-1] <= hist["train_loss"][0]

    def test_weights_serialization(self):
        nn = SimpleNN(input_size=4, seed=7)
        w = nn.weights
        assert "W1" in w and "b1" in w and "W2" in w and "b2" in w


class TestModelPersistence:
    def test_save_and_load_linear(self, tmp_path):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=40)
        p = tmp_path / "model.json"
        save_model(est, p)
        loaded = load_model(p)
        pts = _make_points(20)
        assert loaded.road_score(pts) == pytest.approx(est.road_score(pts))

    def test_loaded_model_type_linear(self, tmp_path):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=40)
        p = tmp_path / "model.json"
        save_model(est, p)
        loaded = load_model(p)
        assert loaded.model_type == "linear"


class TestEstimatorNNMode:
    def test_from_synthetic_nn_returns_fitted(self):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=80, use_nn=True)
        assert est.model_type == "nn"
        assert est._fitted is True

    def test_nn_road_score_range(self):
        est = RoadPlausibilityEstimator.from_synthetic(n_samples=80, use_nn=True)
        pts = _make_points(20)
        score = est.road_score(pts)
        assert 0.0 <= score <= 1.0


# ===========================================================================
# ai.researcher
# ===========================================================================


class TestResearcher:
    def test_propose_from_gpx_returns_list(self):
        r = Researcher()
        pts = _make_points(10)
        proposals = r.propose_from_gpx(pts)
        assert isinstance(proposals, list)
        assert len(proposals) == 1

    def test_propose_from_gpx_fields(self):
        r = Researcher()
        pts = _make_points(10)
        p = r.propose_from_gpx(pts)[0]
        assert isinstance(p, Proposta)
        assert p.tipo == "strada"
        assert p.campo == "geometria"
        assert p.nuovo is True
        assert "punti" in p.valore
        assert len(p.valore["punti"]) == 10
        assert 0.0 <= p.confidence <= 1.0
        assert "GPX" in p.motivazione

    def test_propose_from_gpx_empty_returns_empty(self):
        r = Researcher()
        assert r.propose_from_gpx([]) == []

    def test_propose_from_gpx_has_posizione(self):
        r = Researcher()
        pts = _make_points(5)
        p = r.propose_from_gpx(pts)[0]
        assert p.posizione is not None
        assert p.posizione.lat == pytest.approx(45.0)
        assert p.posizione.lon == pytest.approx(9.0)

    def test_propose_from_sensor_returns_proposta(self):
        r = Researcher()
        feat = RawFeature("sensore_traffico", (45.0, 9.0), {"traffico": 42})
        p = r.propose_from_sensor(feat)
        assert isinstance(p, Proposta)
        assert p.campo == "traffico"
        assert p.valore == 42
        assert p.confidence == 0.7

    def test_propose_from_sensor_target_id_from_world(self):
        r = Researcher()
        # Build a minimal world with a strada
        pos = Posizione.from_latlon(45.001, 9.001)
        strada = Oggetto(id="strada_1", tipo="strada", posizione=pos)
        world = {"strada_1": strada}
        feat = RawFeature("sensore_traffico", (45.0, 9.0), {"traffico": 10})
        p = r.propose_from_sensor(feat, world=world)
        assert p.target_id == "strada_1"

    def test_propose_from_sensor_no_target_without_world(self):
        r = Researcher()
        feat = RawFeature("sensore_traffico", (45.0, 9.0), {"traffico": 10})
        p = r.propose_from_sensor(feat)
        assert p.target_id is None

    def test_nearest_strada_returns_none_for_empty_world(self):
        result = Researcher._nearest_strada(45.0, 9.0, {})
        assert result is None

    def test_nearest_strada_ignores_non_strada(self):
        pos = Posizione.from_latlon(45.0, 9.0)
        tree = Oggetto(id="tree_1", tipo="albero", posizione=pos)
        world = {"tree_1": tree}
        result = Researcher._nearest_strada(45.0, 9.0, world)
        assert result is None


# ===========================================================================
# ai.pipeline
# ===========================================================================


class TestWorldStore:
    def test_add_and_get(self):
        store = WorldStore()
        pos = Posizione.from_latlon(0.0, 0.0)
        obj = Oggetto(id="o1", tipo="strada", posizione=pos)
        store.add(obj)
        assert store.get("o1") is obj

    def test_get_missing_returns_none(self):
        store = WorldStore()
        assert store.get("nonexistent") is None

    def test_to_json_returns_string(self):
        store = WorldStore()
        pos = Posizione.from_latlon(0.0, 0.0)
        store.add(Oggetto(id="o1", tipo="strada", posizione=pos))
        json_str = store.to_json()
        assert isinstance(json_str, str)
        import json
        data = json.loads(json_str)
        assert len(data) == 1


class TestPipelineResearchGpx:
    def test_research_gpx_returns_proposals(self):
        store = WorldStore()
        pipe = Pipeline(store)
        pts = _make_points(10)
        proposals = pipe.research_gpx(pts)
        assert len(proposals) == 1
        assert proposals[0].tipo == "strada"

    def test_research_gpx_empty_points(self):
        store = WorldStore()
        pipe = Pipeline(store)
        assert pipe.research_gpx([]) == []


class TestPipelineResearchSensor:
    def test_research_sensor_returns_proposta(self):
        store = WorldStore()
        pipe = Pipeline(store)
        feat = RawFeature("sensore_traffico", (45.0, 9.0), {"traffico": 50})
        p = pipe.research_sensor(feat)
        assert isinstance(p, Proposta)

    def test_research_sensor_with_world_target(self):
        store = WorldStore()
        pipe = Pipeline(store)
        pos = Posizione.from_latlon(45.001, 9.001)
        strada = Oggetto(id="s1", tipo="strada", posizione=pos)
        store.add(strada)
        feat = RawFeature("sensore_traffico", (45.0, 9.0), {"traffico": 50})
        p = pipe.research_sensor(feat)
        assert p.target_id == "s1"


class TestPipelineSubmitAndFlush:
    def test_submit_adds_to_buffer(self):
        store = WorldStore()
        pipe = Pipeline(store)
        pos = Posizione.from_latlon(0.0, 0.0)
        p = Proposta(campo="geometria", valore={}, confidence=0.8,
                     posizione=pos, nuovo=True, tipo="strada")
        pipe.submit(p)
        assert len(pipe.buffer) == 1

    def test_flush_creates_object(self):
        store = WorldStore()
        pipe = Pipeline(store)
        pos = Posizione.from_latlon(0.0, 0.0)
        p = Proposta(campo="geometria", valore={"tipo": "linea"}, confidence=0.9,
                     posizione=pos, nuovo=True, tipo="strada")
        pipe.submit(p)
        applied = pipe.flush()
        assert applied == 1
        assert len(pipe.buffer) == 0
        assert len(store.objects) == 1

    def test_flush_returns_count(self):
        store = WorldStore()
        pipe = Pipeline(store)
        pos = Posizione.from_latlon(0.0, 0.0)
        for _ in range(3):
            p = Proposta(campo="geometria", valore={}, confidence=0.8,
                         posizione=pos, nuovo=True, tipo="strada")
            pipe.submit(p)
        assert pipe.flush() == 3

    def test_flush_creates_incremental_ids(self):
        store = WorldStore()
        pipe = Pipeline(store)
        pos = Posizione.from_latlon(0.0, 0.0)
        for _ in range(3):
            p = Proposta(campo="geometria", valore={}, confidence=0.8,
                         posizione=pos, nuovo=True, tipo="strada")
            pipe.submit(p)
        pipe.flush()
        ids = list(store.objects.keys())
        assert ids == ["obj_000001", "obj_000002", "obj_000003"]


class TestPipelineUpdate:
    def test_update_appends_stato(self):
        store = WorldStore()
        pipe = Pipeline(store)
        # First create an object
        pos = Posizione.from_latlon(0.0, 0.0)
        create_p = Proposta(campo="geometria", valore={}, confidence=0.8,
                            posizione=pos, nuovo=True, tipo="strada")
        pipe.submit(create_p)
        pipe.flush()
        obj_id = list(store.objects.keys())[0]

        # Now update it
        update_p = Proposta(target_id=obj_id, campo="traffico", valore=55,
                            confidence=0.7)
        pipe.submit(update_p)
        pipe.flush()

        obj = store.get(obj_id)
        assert obj.proprieta["traffico"] == 55
        assert len(obj.cronologia) == 1
        assert obj.cronologia[0].campi["traffico"] == 55

    def test_update_missing_target_returns_false(self):
        store = WorldStore()
        pipe = Pipeline(store)
        update_p = Proposta(target_id="nonexistent", campo="x", valore=1,
                            confidence=0.5)
        pipe.submit(update_p)
        # flush returns 0 because _update returned False
        assert pipe.flush() == 0


class TestPipelineTrim:
    def test_trim_removes_old_stati(self):
        store = WorldStore()
        pipe = Pipeline(store)
        pos = Posizione.from_latlon(0.0, 0.0)
        obj = Oggetto(id="o1", tipo="strada", posizione=pos,
                      stale_after_s=0.1)  # 100ms retention
        store.add(obj)

        # Manually add an old stato and a fresh one
        from datetime import datetime, timedelta
        old_ts = datetime.now(UTC) - timedelta(seconds=10)
        obj.cronologia.append(Stato(campi={"traffico": 1}, confidence=0.5, t=old_ts))
        obj.cronologia.append(Stato(campi={"traffico": 2}, confidence=0.5))
        assert len(obj.cronologia) == 2

        # Small sleep to ensure the new stato is older than the retention window
        import time as _time
        _time.sleep(0.15)

        # Submit an update to trigger _trim
        update_p = Proposta(target_id="o1", campo="traffico", valore=3,
                            confidence=0.5)
        pipe.submit(update_p)
        pipe.flush()

        # Old stato should be trimmed; fresh one may also be trimmed if
        # retention window passed, so we just verify trim ran and storia
        # is not longer than it was
        assert len(obj.cronologia) <= 2
        # The most recent stato should have the updated value
        for s in obj.cronologia:
            if s.campi.get("traffico") == 3:
                break
        else:
            pytest.fail("Updated traffico not found in cronologia")

    def test_no_trim_when_stale_after_none(self):
        store = WorldStore()
        pipe = Pipeline(store)
        pos = Posizione.from_latlon(0.0, 0.0)
        obj = Oggetto(id="o1", tipo="strada", posizione=pos,
                      stale_after_s=None)
        store.add(obj)
        from datetime import datetime, timedelta
        old_ts = datetime.now(UTC) - timedelta(days=365)
        obj.cronologia.append(Stato(campi={"x": 1}, confidence=0.5, t=old_ts))

        update_p = Proposta(target_id="o1", campo="x", valore=2, confidence=0.5)
        pipe.submit(update_p)
        pipe.flush()
        # Nothing trimmed
        assert len(obj.cronologia) == 2


# ===========================================================================
# End-to-end: ingest -> pipeline -> store
# ===========================================================================


class TestEndToEnd:
    def test_gpx_to_store(self):
        store = WorldStore()
        pipe = Pipeline(store)
        points = ingest_gpx(str(SAMPLE_GPX))
        proposals = pipe.research_gpx(points)
        for p in proposals:
            pipe.submit(p)
        pipe.flush()
        assert len(store.objects) == 1
        obj = list(store.objects.values())[0]
        assert obj.tipo == "strada"

    def test_sensor_stream_to_store(self):
        store = WorldStore()
        pipe = Pipeline(store)
        for feat in ingest_sensor_stream_stub(3):
            p = pipe.research_sensor(feat)
            pipe.submit(p)
        pipe.flush()
        # 3 sensor features each produce an update proposal
        # but without existing strada objects, updates fail (target_id=None)
        # so create count is 0, applied count reflects that
        assert len(store.objects) == 0  # updates without target fail gracefully
