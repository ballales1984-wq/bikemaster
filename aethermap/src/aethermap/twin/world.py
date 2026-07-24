from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from aethermap.ai.ingest import ingest_sensor_stream_stub
from aethermap.ai.models import Relazione
from aethermap.ai.pipeline import Pipeline
from aethermap.data.store import SpatialStore, WorldStore as DataWorldStore
from aethermap.twin.objects import Albero, Montagna, Strada, make_albero, make_montagna, make_strada


@dataclass
class Environment:
    temp_c: float
    solar_elev_deg: float
    ora: str


class DigitalTwin:
    """Sintesi di Fasi 1-4: geometria cube-sphere (core) + modello dati
    (Fase 2) + pipeline IA 'ricercatore' (Fase 3) + rendering (Fase 4).

    Ogni oggetto e' VIVO: il suo stato muta via stream IA (traffico) e via
    ambiente (neve, ombra) senza mai riscrivere la geometria immutabile.
    """

    def __init__(self) -> None:
        spatial = SpatialStore()
        self.store = DataWorldStore(store=spatial)
        self.pipeline = Pipeline(self.store)

    def add(self, obj: Strada | Albero | Montagna) -> None:
        self.store.add(obj)

    def add_relation(self, source_id: str, target_id: str, tipo: str, confidence: float = 1.0) -> None:
        if source_id not in self.store.objects or target_id not in self.store.objects:
            return
        source = self.store.objects[source_id]
        source.relazioni.append(Relazione(tipo=tipo, target_id=target_id, peso=confidence))

    def get_relations(self, obj_id: str) -> list[dict]:
        obj = self.store.objects.get(obj_id)
        if not obj:
            return []
        return [r.model_dump() for r in obj.relazioni]

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list:
        return self.store.query_radius(lat, lon, radius_m)

    def query_s2(self, s2: str) -> list:
        return self.store.query_s2(s2)

    def step(self, env: Environment) -> None:
        for feat in ingest_sensor_stream_stub(3):
            self.pipeline.submit(self.pipeline.research_sensor(feat))
        self.pipeline.flush()
        for obj in self.store.objects.values():
            self._apply_env(obj, env)
        self._build_relations()

    def _build_relations(self) -> None:
        for obj in self.store.objects.values():
            nearby = self.query_radius(obj.posizione.lat, obj.posizione.lon, 2000)
            for other in nearby:
                if other.id == obj.id:
                    continue
                self.add_relation(obj.id, other.id, "vicino", 0.8)

    @staticmethod
    def _apply_env(obj, env: Environment) -> None:
        if isinstance(obj, Strada):
            obj.proprieta["ombrata"] = obj.ombrata(env.solar_elev_deg)
        elif isinstance(obj, Albero):
            obj.proprieta["ombra"] = obj.ombra(env.solar_elev_deg)
        elif isinstance(obj, Montagna):
            obj.proprieta["neve"] = obj.neve(env.temp_c)

    def snapshot(self) -> list[dict]:
        out = []
        for obj in self.store.objects.values():
            if isinstance(obj, Strada):
                out.append({"id": obj.id, "tipo": "strada",
                            "traffico": obj.traffico(), "pendenza_%": obj.pendenza(),
                            "ombrata": obj.proprieta.get("ombrata"),
                            "manutenzione": obj.manutenzione()})
            elif isinstance(obj, Albero):
                out.append({"id": obj.id, "tipo": "albero",
                            "specie": obj.specie(), "altezza_m": obj.altezza(),
                            "ombra": obj.proprieta.get("ombra")})
            elif isinstance(obj, Montagna):
                out.append({"id": obj.id, "tipo": "montagna",
                            "versanti": obj.versanti(), "neve": obj.proprieta.get("neve"),
                            "sentieri": obj.sentieri()})
        return out

    def h3_summary(self, resolution: int = 9) -> dict[str, dict[str, int]]:
        try:
            import h3
        except ImportError as exc:
            raise RuntimeError("h3 package required for H3 aggregation") from exc
        grid: dict[str, dict[str, int]] = {}
        for obj in self.store.objects.values():
            h3_idx = getattr(obj.posizione, "h3", None)
            if not h3_idx:
                continue
            parent = h3.cell_to_parent(h3_idx, resolution)
            cell = grid.setdefault(parent, {})
            cell[obj.tipo] = cell.get(obj.tipo, 0) + 1
        return grid

    def save_json(self, path: str | Path) -> None:
        out = []
        for obj in self.store.objects.values():
            if isinstance(obj, Strada):
                out.append({"id": obj.id, "tipo": "strada",
                            "posizione": {"lat": obj.posizione.lat, "lon": obj.posizione.lon, "alt": getattr(obj.posizione, "alt", 0)},
                            "geometria": obj.geometria.dati,
                            "proprieta": obj.proprieta})
            elif isinstance(obj, Albero):
                out.append({"id": obj.id, "tipo": "albero",
                            "posizione": {"lat": obj.posizione.lat, "lon": obj.posizione.lon, "alt": getattr(obj.posizione, "alt", 0)},
                            "proprieta": obj.proprieta})
            elif isinstance(obj, Montagna):
                out.append({"id": obj.id, "tipo": "montagna",
                            "posizione": {"lat": obj.posizione.lat, "lon": obj.posizione.lon, "alt": getattr(obj.posizione, "alt", 0)},
                            "proprieta": obj.proprieta})
        Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_json(self, path: str | Path) -> None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for item in data:
            tipo = item.get("tipo")
            pos = item.get("posizione", {})
            lat = pos.get("lat", 0.0)
            lon = pos.get("lon", 0.0)
            props = item.get("proprieta", {})
            if tipo == "strada":
                obj = make_strada(
                    item["id"], lat, lon,
                    item.get("geometria", {}).get("punti", [])
                )
                obj.proprieta.update(props)
                self.add(obj)
            elif tipo == "albero":
                obj = make_albero(
                    item["id"], lat, lon,
                    props.get("specie"), props.get("altezza_m", 5.0)
                )
                obj.proprieta.update(props)
                self.add(obj)
            elif tipo == "montagna":
                obj = make_montagna(
                    item["id"], lat, lon,
                    pos.get("alt", 0.0), props.get("versanti", [])
                )
                obj.proprieta.update(props)
                self.add(obj)
