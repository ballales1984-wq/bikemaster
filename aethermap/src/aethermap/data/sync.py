"""AetherMap digital twin sync engine (Punto 3 — offline-first).

Export / import dello stato del digital twin per sync tra dispositivi.
Formato: JSON con oggetti e stato cronologia.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aethermap.ai.models import Stato
from aethermap.twin.world import DigitalTwin

logger = logging.getLogger(__name__)


class TwinSyncEngine:
    """Export / import stato DigitalTwin per sync offline-first."""

    def __init__(self, twin: DigitalTwin) -> None:
        self._twin = twin

    def export(self) -> dict[str, Any]:
        objects = []
        for obj in self._twin.store.objects.values():
            objects.append({
                "id": obj.id,
                "tipo": obj.tipo,
                "posizione": {
                    "lat": obj.posizione.lat,
                    "lon": obj.posizione.lon,
                    "alt": getattr(obj.posizione, "alt", 0.0),
                },
                "proprieta": obj.proprieta,
                "relazioni": [r.model_dump() for r in obj.relazioni],
            })

        history = []
        if hasattr(self._twin, "_persistent_store") and self._twin._persistent_store is not None:
            store = self._twin._persistent_store
            if hasattr(store, "_spatial"):
                for obj_id, obj in store._spatial.objects.items():
                    for stato in getattr(obj, "_stato_cronologia", []):
                        history.append({
                            "object_id": obj_id,
                            "campi": stato.campi,
                            "t": stato.t.isoformat(),
                            "confidence": stato.confidence,
                        })

        return {
            "version": "aethermap-twin-1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "objects": objects,
            "history": history,
        }

    def import_sync(self, data: dict[str, Any]) -> None:
        if data.get("version") != "aethermap-twin-1.0":
            raise ValueError(f"Unsupported sync version: {data.get('version')}")

        for obj_data in data.get("objects", []):
            tipo = obj_data.get("tipo")
            pos = obj_data.get("posizione", {})
            props = obj_data.get("proprieta", {})

            if tipo == "strada":
                from aethermap.twin.objects import make_strada
                obj = make_strada(
                    obj_data["id"],
                    pos.get("lat", 0.0),
                    pos.get("lon", 0.0),
                    props.get("geometria", {}).get("punti", []),
                )
            elif tipo == "albero":
                from aethermap.twin.objects import make_albero
                obj = make_albero(
                    obj_data["id"],
                    pos.get("lat", 0.0),
                    pos.get("lon", 0.0),
                    props.get("specie"),
                    pos.get("alt", 5.0),
                )
            elif tipo == "montagna":
                from aethermap.twin.objects import make_montagna
                obj = make_montagna(
                    obj_data["id"],
                    pos.get("lat", 0.0),
                    pos.get("lon", 0.0),
                    pos.get("alt", 0.0),
                    props.get("versanti", []),
                )
            else:
                continue

            obj.proprieta.update(props)
            self._twin.add(obj)

        for entry in data.get("history", []):
            try:
                t = datetime.fromisoformat(entry["t"])
                stato = Stato(campi=entry["campi"], t=t, confidence=entry.get("confidence", 1.0))
                self._twin.add_state(entry["object_id"], stato)
            except Exception as exc:
                logger.warning("Failed to import history entry: %s", exc)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.export(), ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.import_sync(data)
