from __future__ import annotations

from aethermap.ai.models import Oggetto, Posizione


class Strada(Oggetto):
    def traffico(self) -> float | None:
        return self.proprieta.get("traffico")

    def asfalto(self) -> str:
        return self.proprieta.get("asfalto", "asfalto")

    def manutenzione(self) -> str:
        return self.proprieta.get("manutenzione", "buona")

    def pendenza(self) -> float:
        pts = self.geometria.dati.get("punti", [])
        if len(pts) < 2:
            return 0.0
        import math
        tot_h = 0.0
        tot_d = 0.0
        for a, b in zip(pts, pts[1:]):
            dh = (a.get("ele") or 0) - (b.get("ele") or 0)
            dl = math.hypot(
                (a["lat"] - b["lat"]) * 111320,
                (a["lon"] - b["lon"]) * 111320 * math.cos(math.radians(a["lat"])),
            )
            tot_h += abs(dh)
            tot_d += dl
        return round(100.0 * tot_h / tot_d, 2) if tot_d else 0.0

    def ombrata(self, solar_elev_deg: float) -> bool:
        return solar_elev_deg < 12.0


class Albero(Oggetto):
    def specie(self) -> str | None:
        return self.proprieta.get("specie")

    def altezza(self) -> float | None:
        return self.proprieta.get("altezza_m")

    def ombra(self, solar_elev_deg: float) -> bool:
        return bool(self.altezza()) and solar_elev_deg < 18.0

    def crescita(self, giorni: float) -> float:
        base = self.proprieta.get("altezza_m", 1.0)
        return round(base + 0.002 * giorni, 3)


class Montagna(Oggetto):
    def versanti(self) -> list[str]:
        return self.proprieta.get("versanti", [])

    def vegetazione(self) -> str:
        return self.proprieta.get("vegetazione", "bosco")

    def sentieri(self) -> int:
        return self.proprieta.get("sentieri", 0)

    def neve(self, temp_c: float) -> bool:
        return temp_c < 1.0


def make_strada(id_: str, lat: float, lon: float, pts: list[dict]) -> Strada:
    return Strada(id=id_, tipo="strada",
                  posizione=Posizione.from_latlon(lat, lon),
                  geometria=__import__("aethermap.ai.models", fromlist=["Geometria"]).Geometria(tipo="linea", dati={"punti": pts}))


def make_albero(id_: str, lat: float, lon: float, specie: str, h: float) -> Albero:
    a = Albero(id=id_, tipo="albero", posizione=Posizione.from_latlon(lat, lon))
    a.proprieta["specie"] = specie
    a.proprieta["altezza_m"] = h
    return a


def make_montagna(id_: str, lat: float, lon: float, alt: float, versanti: list[str]) -> Montagna:
    m = Montagna(id=id_, tipo="montagna", posizione=Posizione.from_latlon(lat, lon, alt))
    m.proprieta["versanti"] = versanti
    m.proprieta["sentieri"] = len(versanti) * 2
    return m
