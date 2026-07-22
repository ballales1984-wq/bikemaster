"""Tests for aethermap.twin (Phase 5 digital twin)."""
from __future__ import annotations

import numpy as np
import pytest

from aethermap.ai.models import Posizione
from aethermap.twin.objects import (
    Albero,
    make_albero,
    make_montagna,
    make_strada,
)
from aethermap.twin.svo import SparseVolume
from aethermap.twin.world import DigitalTwin, Environment

# ===========================================================================
# twin.objects — Strada
# ===========================================================================


def _make_strada_pts():
    """Build a simple sloped road with elevation changes."""
    return [
        {"lat": 45.0, "lon": 9.0, "ele": 100.0},
        {"lat": 45.001, "lon": 9.001, "ele": 110.0},
        {"lat": 45.002, "lon": 9.002, "ele": 130.0},
    ]


def _make_strada():
    return make_strada("s1", 45.0, 9.0, _make_strada_pts())


class TestStrada:
    def test_pendenza_flat_road(self):
        pts = [
            {"lat": 45.0, "lon": 9.0, "ele": 100.0},
            {"lat": 45.001, "lon": 9.001, "ele": 100.0},
            {"lat": 45.002, "lon": 9.002, "ele": 100.0},
        ]
        s = make_strada("s_flat", 45.0, 9.0, pts)
        assert s.pendenza() == pytest.approx(0.0, abs=0.01)

    def test_pendenza_positive_slope(self):
        s = _make_strada()
        p = s.pendenza()
        assert p > 0.0

    def test_pendenza_single_point_returns_zero(self):
        pts = [{"lat": 45.0, "lon": 9.0, "ele": 100.0}]
        s = make_strada("s_single", 45.0, 9.0, pts)
        assert s.pendenza() == 0.0

    def test_ombrata_low_sun(self):
        s = _make_strada()
        assert s.ombrata(solar_elev_deg=5.0) is True

    def test_ombrata_high_sun(self):
        s = _make_strada()
        assert s.ombrata(solar_elev_deg=30.0) is False

    def test_ombrata_threshold(self):
        s = _make_strada()
        # threshold is 12.0
        assert s.ombrata(11.9) is True
        assert s.ombrata(12.0) is False
        assert s.ombrata(12.1) is False

    def test_traffico_default_none(self):
        s = _make_strada()
        assert s.traffico() is None

    def test_traffico_set(self):
        s = _make_strada()
        s.proprieta["traffico"] = 42
        assert s.traffico() == 42

    def test_asfalto_default(self):
        s = _make_strada()
        assert s.asfalto() == "asfalto"

    def test_manutenzione_default(self):
        s = _make_strada()
        assert s.manutenzione() == "buona"


# ===========================================================================
# twin.objects — Albero
# ===========================================================================


def _make_albero(specie: str = "querci", h: float = 5.0):
    return make_albero("a1", 45.0, 9.0, specie, h)


class TestAlbero:
    def test_specie(self):
        a = _make_albero("pino")
        assert a.specie() == "pino"

    def test_specie_default_none(self):
        a = Albero(id="a_empty", tipo="albero",
                   posizione=Posizione.from_latlon(0.0, 0.0))
        assert a.specie() is None

    def test_altezza(self):
        a = _make_albero(h=7.5)
        assert a.altezza() == 7.5

    def test_altezza_default_none(self):
        a = Albero(id="a_empty", tipo="albero",
                   posizione=Posizione.from_latlon(0.0, 0.0))
        assert a.altezza() is None

    def test_ombra_low_sun_with_height(self):
        a = _make_albero(h=5.0)
        assert a.ombra(solar_elev_deg=10.0) is True

    def test_ombra_high_sun(self):
        a = _make_albero(h=5.0)
        assert a.ombra(solar_elev_deg=25.0) is False

    def test_ombra_no_height_returns_false(self):
        a = Albero(id="a_no_h", tipo="albero",
                   posizione=Posizione.from_latlon(0.0, 0.0))
        # altezza() returns None -> bool(None) is False
        assert a.ombra(solar_elev_deg=5.0) is False

    def test_crescita_zero_days(self):
        a = _make_albero(h=3.0)
        assert a.crescita(giorni=0.0) == pytest.approx(3.0)

    def test_crescisa_positive_growth(self):
        a = _make_albero(h=3.0)
        result = a.crescita(giorni=100.0)
        assert result == pytest.approx(3.0 + 0.002 * 100.0)
        assert result > 3.0

    def test_crescita_formula(self):
        a = _make_albero(h=2.0)
        assert a.crescita(giorni=500.0) == pytest.approx(2.0 + 1.0)


# ===========================================================================
# twin.objects — Montagna
# ===========================================================================


def _make_montagna(alt: float = 2000.0, versanti: list[str] | None = None):
    if versanti is None:
        versanti = ["N", "S"]
    return make_montagna("m1", 45.0, 9.0, alt, versanti)


class TestMontagna:
    def test_neve_true_when_cold(self):
        m = _make_montagna()
        assert m.neve(temp_c=-2.0) is True

    def test_neve_false_when_warm(self):
        m = _make_montagna()
        assert m.neve(temp_c=10.0) is False

    def test_neve_threshold(self):
        m = _make_montagna()
        assert m.neve(temp_c=0.5) is True
        assert m.neve(temp_c=1.0) is False
        assert m.neve(temp_c=0.999) is True

    def test_versanti(self):
        m = _make_montagna(versanti=["N", "S", "E", "W"])
        assert m.versanti() == ["N", "S", "E", "W"]

    def test_versanti_default(self):
        m = _make_montagna()
        assert m.versanti() == ["N", "S"]

    def test_vegetazione_default(self):
        m = _make_montagna()
        assert m.vegetazione() == "bosco"

    def test_sentieri_default(self):
        m = _make_montagna(versanti=["N"])
        assert m.sentieri() == 2  # len(versanti) * 2

    def test_neve_interna_returns_float(self):
        m = _make_montagna()
        frac = m.neve_interna(temp_c=0.0)
        assert isinstance(frac, float)
        assert 0.0 <= frac <= 1.0

    def test_volume_stats_returns_dict(self):
        m = _make_montagna()
        stats = m.volume_stats(temp_c=5.0)
        assert isinstance(stats, dict)
        assert "voxel_totali" in stats
        assert "snow_%" in stats
        assert "rock_%" in stats
        assert "veg_%" in stats

    def test_volume_stats_voxel_totali_positive(self):
        m = _make_montagna()
        stats = m.volume_stats(temp_c=5.0)
        assert stats["voxel_totali"] > 0

    def test_volume_stats_percentages_sum(self):
        m = _make_montagna()
        stats = m.volume_stats(temp_c=5.0)
        total_pct = stats["snow_%"] + stats["rock_%"] + stats["veg_%"]
        # Should approximately sum to 100 (minor rounding)
        assert total_pct == pytest.approx(100.0, abs=0.5)

    def test_colder_more_snow(self):
        """Lower temp -> higher snow fraction."""
        m = _make_montagna()
        stats_cold = m.volume_stats(temp_c=-10.0)
        stats_warm = m.volume_stats(temp_c=20.0)
        assert stats_cold["snow_%"] > stats_warm["snow_%"]


# ===========================================================================
# twin.svo
# ===========================================================================


class TestSparseVolume:
    def test_build_creates_non_empty_grid(self):
        sv = SparseVolume(base_alt=1000.0, height=2000.0, radius=3000.0,
                          versanti=["N"], temp_c=0.0)
        assert np.count_nonzero(sv.grid != 3) > 0

    def test_material_at(self):
        sv = SparseVolume(base_alt=1000.0, height=2000.0, radius=3000.0,
                          versanti=["N"], temp_c=0.0)
        # Just verify it runs and returns int
        mat = sv.material_at(0, 0, 0)
        assert isinstance(mat, int)
        assert mat in (0, 1, 2, 3)

    def test_snow_fraction_range(self):
        sv = SparseVolume(base_alt=1000.0, height=2000.0, radius=3000.0,
                          versanti=["N"], temp_c=0.0)
        frac = sv.snow_fraction()
        assert 0.0 <= frac <= 1.0

    def test_snow_fraction_zero_when_warm(self):
        sv = SparseVolume(base_alt=1000.0, height=2000.0, radius=3000.0,
                          versanti=["N"], temp_c=30.0)
        frac = sv.snow_fraction()
        assert frac == 0.0

    def test_stats_keys(self):
        sv = SparseVolume(base_alt=1000.0, height=2000.0, radius=3000.0,
                          versanti=["N"], temp_c=5.0)
        stats = sv.stats()
        assert set(stats.keys()) == {"voxel_totali", "snow_%", "rock_%", "veg_%"}

    def test_different_temps_different_snow(self):
        sv_cold = SparseVolume(base_alt=1000.0, height=2000.0, radius=3000.0,
                               versanti=["N", "S"], temp_c=-5.0)
        sv_warm = SparseVolume(base_alt=1000.0, height=2000.0, radius=3000.0,
                               versanti=["N", "S"], temp_c=25.0)
        assert sv_cold.snow_fraction() > sv_warm.snow_fraction()


# ===========================================================================
# twin.world
# ===========================================================================


class TestDigitalTwin:
    def test_add_and_snapshot(self):
        twin = DigitalTwin()
        twin.add(_make_strada())
        snap = twin.snapshot()
        assert len(snap) == 1
        assert snap[0]["tipo"] == "strada"

    def test_step_applies_sensor_updates(self):
        twin = DigitalTwin()
        strada = _make_strada()
        twin.add(strada)
        # Before step, traffico is None
        assert twin.store.objects[strada.id].traffico() is None

        env = Environment(temp_c=5.0, solar_elev_deg=30.0, ora="10:00")
        twin.step(env)
        # After step with sensor stream, traffico should be set on the strada
        obj = twin.store.objects[strada.id]
        # The sensor proposals target the nearest strada (this one)
        assert obj.traffico() is not None

    def test_step_applies_environment(self):
        twin = DigitalTwin()
        strada = _make_strada()
        twin.add(strada)
        env = Environment(temp_c=5.0, solar_elev_deg=5.0, ora="10:00")
        twin.step(env)
        obj = twin.store.objects[strada.id]
        # low solar elevation -> ombrata True
        assert obj.proprieta.get("ombrata") is True

    def test_snapshot_strada_fields(self):
        twin = DigitalTwin()
        twin.add(_make_strada())
        snap = twin.snapshot()
        assert "traffico" in snap[0]
        assert "pendenza_%" in snap[0]
        assert "ombrata" in snap[0]

    def test_snapshot_albero_fields(self):
        twin = DigitalTwin()
        twin.add(make_albero("a1", 45.0, 9.0, "pino", 8.0))
        snap = twin.snapshot()
        assert snap[0]["tipo"] == "albero"
        assert snap[0]["specie"] == "pino"
        assert snap[0]["altezza_m"] == 8.0

    def test_snapshot_montagna_fields(self):
        twin = DigitalTwin()
        twin.add(make_montagna("m1", 46.0, 10.0, 3000.0, ["N", "S"]))
        snap = twin.snapshot()
        assert snap[0]["tipo"] == "montagna"
        assert "neve" in snap[0]
        assert "sentieri" in snap[0]


class TestAlberoInTwin:
    def test_ombra_set_after_step(self):
        twin = DigitalTwin()
        albero = make_albero("a1", 45.0, 9.0, "betulla", 6.0)
        twin.add(albero)
        env = Environment(temp_c=15.0, solar_elev_deg=5.0, ora="08:00")
        twin.step(env)
        obj = twin.store.objects[albero.id]
        assert obj.proprieta.get("ombra") is True

    def test_ombra_not_set_after_high_sun(self):
        twin = DigitalTwin()
        albero = make_albero("a2", 45.0, 9.0, "betulla", 6.0)
        twin.add(albero)
        env = Environment(temp_c=15.0, solar_elev_deg=25.0, ora="12:00")
        twin.step(env)
        obj = twin.store.objects[albero.id]
        assert obj.proprieta.get("ombra") is False


class TestMontagnaInTwin:
    def test_neve_set_after_step(self):
        twin = DigitalTwin()
        montagna = make_montagna("m1", 46.0, 10.0, 3000.0, ["N"])
        twin.add(montagna)
        env = Environment(temp_c=-5.0, solar_elev_deg=30.0, ora="12:00")
        twin.step(env)
        obj = twin.store.objects[montagna.id]
        assert obj.proprieta.get("neve") is True

    def test_no_neve_after_warm_step(self):
        twin = DigitalTwin()
        montagna = make_montagna("m2", 46.0, 10.0, 3000.0, ["N"])
        twin.add(montagna)
        env = Environment(temp_c=20.0, solar_elev_deg=30.0, ora="12:00")
        twin.step(env)
        obj = twin.store.objects[montagna.id]
        assert obj.proprieta.get("neve") is False


class TestMixedTwinSnapshot:
    def test_full_scenario(self):
        twin = DigitalTwin()
        twin.add(_make_strada())
        twin.add(make_albero("a1", 45.0, 9.0, "pino", 5.0))
        twin.add(make_montagna("m1", 46.0, 10.0, 2500.0, ["N", "S", "E"]))

        env = Environment(temp_c=0.0, solar_elev_deg=8.0, ora="09:00")
        twin.step(env)

        snap = twin.snapshot()
        assert len(snap) == 3
        types = {s["tipo"] for s in snap}
        assert types == {"strada", "albero", "montagna"}

        # Montagna with cold -> neve True
        montagna_snap = next(s for s in snap if s["tipo"] == "montagna")
        assert montagna_snap["neve"] is True
