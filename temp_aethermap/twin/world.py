from __future__ import annotations

from dataclasses import dataclass

from aethermap.ai.ingest import ingest_sensor_stream_stub
from aethermap.ai.pipeline import Pipeline, WorldStore
from aethermap.twin.objects import Albero, Montagna, Strada


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
        self.store = WorldStore()
        self.pipeline = Pipeline(self.store)

    def add(self, obj: Strada | Albero | Montagna) -> None:
        self.store.add(obj)

    def step(self, env: Environment) -> None:
        for feat in ingest_sensor_stream_stub(3):
            self.pipeline.submit(self.pipeline.research_sensor(feat))
        self.pipeline.flush()
        for obj in self.store.objects.values():
            self._apply_env(obj, env)

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
