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
        for a, b in zip(pts[:-1], pts[1:], strict=True):
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

    def _volume(self, temp_c: float):
        from aethermap.twin.svo import SparseVolume
        h = 1500.0
        r0 = 1500.0 + len(self.versanti()) * 500.0
        return SparseVolume(base_alt=self.posizione.alt, height=h, radius=r0,
                             versanti=self.versanti(), temp_c=temp_c)

    def neve_interna(self, temp_c: float) -> float:
        return self._volume(temp_c).snow_fraction()

    def volume_stats(self, temp_c: float) -> dict:
        return self._volume(temp_c).stats()


class POI(Oggetto):
    def categoria(self) -> str | None:
        return self.proprieta.get("categoria")

    def descrizione(self) -> str | None:
        return self.proprieta.get("descrizione")


class Percorso(Oggetto):
    def punti(self) -> list[dict]:
        return self.geometria.dati.get("punti", [])

    def distanza_km(self) -> float | None:
        return self.proprieta.get("distanza_km")

    def dislivello_m(self) -> float | None:
        return self.proprieta.get("dislivello_m")


class Terreno(Oggetto):
    def tipo_terreno(self) -> str | None:
        return self.proprieta.get("tipo_terreno")

    def pendenza_media(self) -> float | None:
        return self.proprieta.get("pendenza_media")


def make_strada(id_: str, lat: float, lon: float, pts: list[dict]) -> Strada:
    geom = __import__("aethermap.ai.models", fromlist=["Geometria"]).Geometria(
        tipo="linea", dati={"punti": pts}
    )
    return Strada(id=id_, tipo="strada",
                  posizione=Posizione.from_latlon(lat, lon),
                  geometria=geom)


def make_albero(id_: str, lat: float, lon: float, specie: str, h: float, alt: float = 0.0) -> Albero:
    a = Albero(id=id_, tipo="albero", posizione=Posizione.from_latlon(lat, lon, alt))
    a.proprieta["specie"] = specie
    a.proprieta["altezza_m"] = h
    return a


def make_montagna(id_: str, lat: float, lon: float, alt: float, versanti: list[str]) -> Montagna:
    m = Montagna(id=id_, tipo="montagna", posizione=Posizione.from_latlon(lat, lon, alt))
    m.proprieta["versanti"] = versanti
    m.proprieta["sentieri"] = len(versanti) * 2
    return m


def make_poi(id_: str, lat: float, lon: float, nome: str, categoria: str, descrizione: str = "") -> POI:
    p = POI(id=id_, tipo="poi", posizione=Posizione.from_latlon(lat, lon))
    p.proprieta["nome"] = nome
    p.proprieta["categoria"] = categoria
    p.proprieta["descrizione"] = descrizione
    return p


def make_perorso(
    id_: str, lat: float, lon: float, pts: list[dict], distanza_km: float, dislivello_m: float
) -> Percorso:
    geom = __import__("aethermap.ai.models", fromlist=["Geometria"]).Geometria(
        tipo="linea", dati={"punti": pts}
    )
    p = Percorso(id=id_, tipo="percorso", posizione=Posizione.from_latlon(lat, lon), geometria=geom)
    p.proprieta["distanza_km"] = distanza_km
    p.proprieta["dislivello_m"] = dislivello_m
    return p


def make_terreno(id_: str, lat: float, lon: float, tipo_terreno: str, pendenza_media: float) -> Terreno:
    t = Terreno(id=id_, tipo="terreno", posizione=Posizione.from_latlon(lat, lon))
    t.proprieta["tipo_terreno"] = tipo_terreno
    t.proprieta["pendenza_media"] = pendenza_media
    return t
