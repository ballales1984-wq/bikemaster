from __future__ import annotations

from math import sqrt

from aethermap.ai.ingest import RawFeature, RawPoint
from aethermap.ai.models import Posizione, Proposta
from aethermap.ai.models_ml import estimate_gpx
from aethermap.core.coordinates import geodetic_to_ecef


def _gpx_confidence(points: list[RawPoint]) -> float:
    """Euristica di fallback (densita' / n. punti) usata solo se il modello ML
    non converge. Mantenuta per retrocompatibilita'."""
    if len(points) < 2:
        return 0.1
    lats = [p.lat for p in points]
    lons = [p.lon for p in points]
    span = max(lats) - min(lats) + max(lons) - min(lons)
    density = len(points) / max(span, 1e-6)
    conf = min(0.95, 0.3 + 0.4 * min(1.0, density / 50.0) + 0.25 * min(1.0, len(points) / 200.0))
    return round(conf, 3)


class Researcher:
    """IA 'ricercatore': propone modifiche, non genera la mappa.

    Perche un ricercatore e non generazione diretta? Perche ogni modifica
    al mondo deve essere tracciabile, confutabile e associata a una
    confidenza: il motore puo accettare/rifiutare, umano o automaticamente.
    """

    def propose_from_gpx(self, points: list[RawPoint]) -> list[Proposta]:
        if not points:
            return []
        first = points[0]
        pos = Posizione.from_latlon(first.lat, first.lon, first.ele or 0.0)
        pts = [{"lat": p.lat, "lon": p.lon, "ele": p.ele} for p in points]

        # --- HOOK ML REALE (Fase 3) ---------------------------------------
        # Stima plausibilita' strada + confidence via modello numpy
        # (aethermap.ai.models_ml.RoadPlausibilityEstimator). Fallback
        # all'euristica se il modello non converge.
        # PUNTO DI INNESTO: qui subentrera' un vero modello (es.
        # segmentazione da immagini satellitari + grafo OSM) che arricchisce
        # le feature o rimpiazza `estimate_gpx`, mantenendo la stessa firma.
        try:
            plausibility, conf = estimate_gpx(points)
        except Exception:
            plausibility, conf = None, _gpx_confidence(points)
        if plausibility is None:
            plausibility = conf
        motivazione = (
            f"tracciato GPX con {len(points)} punti "
            f"(ML road_score={round(plausibility, 3)})"
        )
        return [Proposta(
            nuovo=True,
            posizione=pos,
            tipo="strada",
            campo="geometria",
            valore={"tipo": "linea", "punti": pts},
            confidence=conf,
            motivazione=motivazione,
        )]

    def propose_from_sensor(self, feat: RawFeature, world: dict | None = None) -> Proposta:
        lat, lon = feat.posizione
        traffico = feat.payload.get("traffico", 0)
        conf = 0.7
        target_id = None
        if world:
            target_id = self._nearest_strada(lat, lon, world)
        return Proposta(
            target_id=target_id,
            campo="traffico",
            valore=traffico,
            confidence=conf,
            motivazione="lettura sensore traffico",
        )

    @staticmethod
    def _nearest_strada(lat: float, lon: float, world: dict) -> str | None:
        best, best_d = None, 1e18
        a = geodetic_to_ecef(lat, lon)
        for obj in world.values():
            if obj.tipo != "strada":
                continue
            b = geodetic_to_ecef(obj.posizione.lat, obj.posizione.lon)
            d = sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)
            if d < best_d:
                best, best_d = obj.id, d
        return best
