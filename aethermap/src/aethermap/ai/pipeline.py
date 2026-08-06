from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from aethermap.ai.ingest import RawFeature, RawPoint
from aethermap.ai.models import (
    Confidenza,
    Geometria,
    Oggetto,
    Posizione,
    Proposta,
    Stato,
)
from aethermap.ai.researcher import Researcher


class WorldStore:
    def __init__(self, store: Any = None) -> None:
        self.store = store
        self.objects: dict[str, Oggetto] = {}

    def add(self, obj: Oggetto) -> None:
        self.objects[obj.id] = obj
        if self.store is not None:
            self.store.add(obj)

    def get(self, oid: str) -> Oggetto | None:
        return self.objects.get(oid)

    def to_json(self) -> str:
        return json.dumps([o.model_dump() for o in self.objects.values()], default=str, indent=2)


class Pipeline:
    """Orchestra ingestione -> ricercatore -> proposte -> stato del mondo.

    'Latencia tollerata' (Fase 1 §8.3): le proposte non sono applicate in
    modo sincrono. Il buffer le raccoglie e flush() le applica in batch,
    simulando il tempo necessario a calcoli/trasmissione. Lo stato delle
    entita e quindi 'eventualmente coerente', non istantaneo.
    """

    def __init__(self, store: WorldStore, max_latency_s: float = 1.0) -> None:
        self.store = store
        self.researcher = Researcher()
        self.buffer: list[Proposta] = []
        self.max_latency_s = max_latency_s
        self._counter = 0

    def research_gpx(self, points: list[RawPoint]) -> list[Proposta]:
        return self.researcher.propose_from_gpx(points)

    def research_sensor(self, feat: RawFeature) -> Proposta:
        return self.researcher.propose_from_sensor(feat, self.store.objects)

    def submit(self, proposta: Proposta) -> None:
        self.buffer.append(proposta)

    def flush(self) -> int:
        applied = 0
        for p in self.buffer:
            if self._apply(p):
                applied += 1
        self.buffer.clear()
        return applied

    def _apply(self, p: Proposta) -> bool:
        if p.nuovo:
            return self._create(p)
        return self._update(p)

    def _create(self, p: Proposta) -> bool:
        self._counter += 1
        oid = f"obj_{self._counter:06d}"
        geom = Geometria()
        if p.campo == "geometria" and isinstance(p.valore, dict):
            geom = Geometria(tipo=p.valore.get("tipo", "punto"), dati=p.valore)
        obj = Oggetto(
            id=oid,
            tipo=p.tipo or "oggetto",
            posizione=p.posizione or Posizione(lat=0.0, lon=0.0),
            geometria=geom,
            affidabilita=Confidenza(valore=p.confidence),
        )
        self.store.add(obj)
        return True

    def _update(self, p: Proposta) -> bool:
        target = self.store.get(p.target_id) if p.target_id else None
        if target is None:
            return False
        stato = Stato(campi={p.campo: p.valore}, confidence=p.confidence)
        target.cronologia.append(stato)
        target.proprieta[p.campo] = p.valore
        self._trim(target)
        return True

    @staticmethod
    def _trim(obj: Oggetto) -> None:
        if obj.stale_after_s is None:
            return
        cutoff = datetime.now(UTC).timestamp() - obj.stale_after_s
        obj.cronologia = [s for s in obj.cronologia
                          if s.t.timestamp() >= cutoff]
