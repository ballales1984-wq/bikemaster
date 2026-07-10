"""BikeMaster 2.0 - Sistema di misure interno.

Questo modulo definisce il concetto fondamentale di *grandezza fisica*:

    VALORE + UNITA' + PRECISIONE + FONTE

e il registro delle conversioni tra unita' di misura. Tutti gli algoritmi
del sistema lavorano su grandezze normalizzate (unità canoniche interne),
mai su unità "grezze" di origine (Garmin, Strava, inserimento manuale...).

Unita' canoniche interne (standard BikeMaster):
    massa      -> kg
    lunghezza  -> m
    velocità   -> m/s
    tempo      -> s
    energia    -> J
    potenza    -> W
    pendenza   -> %  (percentuale)
    angolo     -> deg
    frequenza  -> Hz
    temperatura-> °C
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

__all__ = [
    "Quantity",
    "q",
    "UnitRegistry",
    "default_registry",
    "convert",
    "to_canonical_unit",
    "dimension_of",
]


# ---------------------------------------------------------------------------
# Grandezza fisica: valore + unità + precisione + fonte
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Quantity:
    """Una grandezza misurata con la sua incertezza e la sua origine.

    Attributes:
        value: valore numerico nella `unit` specificata.
        unit: simbolo di unità di misura (es. ``"kg"``, ``"m/s"``, ``"%"").
        precision: incertezza assoluta stimata nella stessa unità di `value`.
        source: provenienza del dato (es. ``"garmin"``, ``"manual"``, ``"gps/dem"").
        timestamp: istante di misura, se noto.
    """

    value: float
    unit: str
    precision: float = 0.0
    source: str = "unknown"
    timestamp: Optional[datetime] = None

    def __str__(self) -> str:  # pragma: no cover - debug only
        return f"{self.value:.3g} {self.unit} (±{self.precision:.3g}, {self.source})"


def q(value: float, unit: str, precision: float = 0.0, source: str = "unknown",
      timestamp: Optional[datetime] = None) -> Quantity:
    """Costruttore rapido di :class:`Quantity`."""
    return Quantity(value=value, unit=unit, precision=precision, source=source, timestamp=timestamp)


# ---------------------------------------------------------------------------
# Registro delle unità di misura
# ---------------------------------------------------------------------------
# Dimensioni lineari: fattore moltiplicativo verso l'unità canonica.
_LINEAR: dict[str, dict[str, float]] = {
    "mass": {"kg": 1.0, "g": 1e-3, "t": 1000.0, "lb": 0.45359237,
             "oz": 0.028349523125, "stone": 6.35029318},
    "length": {"m": 1.0, "km": 1000.0, "cm": 1e-2, "mm": 1e-3,
               "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "nmi": 1852.0},
    "speed": {"m/s": 1.0, "km/h": 1.0 / 3.6, "mph": 0.44704, "knot": 0.514444},
    "time": {"s": 1.0, "min": 60.0, "h": 3600.0, "day": 86400.0},
    "energy": {"J": 1.0, "kJ": 1000.0, "MJ": 1e6,
               "cal": 4.184, "kcal": 4184.0, "wh": 3600.0, "kwh": 3.6e6},
    "power": {"W": 1.0, "kW": 1000.0},
    "frequency": {"bpm": 1.0, "rpm": 1.0, "Hz": 60.0, "1/s": 60.0},
    "pressure": {"Pa": 1.0, "hPa": 100.0, "mmHg": 133.322, "atm": 101325.0, "bar": 100000.0},
    "density": {"kg/m^3": 1.0, "g/L": 1.0},
    "torque": {"Nm": 1.0, "kNm": 1000.0},
}

# Unità canoniche per dimensione.
_CANONICAL: dict[str, str] = {
    "mass": "kg", "length": "m", "speed": "m/s", "time": "s",
    "energy": "J", "power": "W",     "frequency": "bpm",
    "slope": "%", "angle": "deg", "temperature": "°C",
    "pressure": "Pa", "density": "kg/m^3", "torque": "Nm",
}

# Dimensioni non lineari gestite con formule dedicate.
_SPECIAL = {"slope", "angle", "temperature"}


class UnitError(ValueError):
    """Errore di conversione di unità (dimensione incompatibile o sconosciuta)."""


class UnitRegistry:
    """Registro delle unità di misura e motore di conversione.

    Le conversioni lineari usano un fattore verso l'unità canonica; le
    conversioni non lineari (temperatura, pendenza/angolo) usano formule
    dedicate.
    """

    def __init__(self, linear: Optional[dict[str, dict[str, float]]] = None) -> None:
        self._linear = dict(_LINEAR)
        if linear:
            for dim, units in linear.items():
                self._linear.setdefault(dim, {}).update(units)

    # -- introspezione ----------------------------------------------------
    def dimension_of(self, unit: str) -> Optional[str]:
        special_units = {"%": "slope", "deg": "slope", "°": "slope",
                         "°C": "temperature", "K": "temperature", "°F": "temperature"}
        if unit in special_units:
            return special_units[unit]
        for dim, units in self._linear.items():
            if unit in units:
                return dim
        return None

    def canonical_unit(self, unit: str) -> str:
        dim = self.dimension_of(unit)
        if dim is None:
            raise UnitError(f"Unità sconosciuta: {unit!r}")
        return _CANONICAL[dim]

    def to_canonical(self, quantity: Quantity) -> Quantity:
        """Riporta una grandezza nell'unità canonica interna della sua dimensione."""
        target = self.canonical_unit(quantity.unit)
        if target == quantity.unit:
            return quantity
        return self.convert(quantity, target)

    # -- conversione ------------------------------------------------------
    def explain_conversion(self, quantity: Quantity, target_unit: str) -> list[str]:
        """Descrive i passaggi della conversione tra unità."""
        src_dim = self.dimension_of(quantity.unit)
        tgt_dim = self.dimension_of(target_unit)
        steps = [
            f"Da {quantity.value} {quantity.unit} a {target_unit}",
            f"Dimensioni: {src_dim} -> {tgt_dim}",
        ]
        if src_dim != tgt_dim:
            steps.append("ERRORE: dimensioni incompatibili")
            return steps
        if src_dim == "temperature":
            steps.append("Passaggio intermedio: Kelvin")
            scale = 1.0 if target_unit != "°F" else 5.0 / 9.0
            steps.append(f"Scala di conversione: {scale}")
        elif src_dim in ("slope", "angle"):
            steps.append("Conversione non lineare: atan/tan")
        else:
            f_src = self._linear[src_dim][quantity.unit]
            f_tgt = self._linear[src_dim][target_unit]
            canon = self.canonical_unit(quantity.unit)
            steps.append(f"Fattore verso canonica ({canon}): {f_src}")
            steps.append(f"Fattore da canonica a {target_unit}: {f_tgt}")
        return steps

    def convert(self, quantity: Quantity, target_unit: str) -> Quantity:
        src_dim = self.dimension_of(quantity.unit)
        tgt_dim = self.dimension_of(target_unit)
        if src_dim is None or tgt_dim is None:
            raise UnitError(f"Unità sconosciuta: {quantity.unit!r} o {target_unit!r}")
        if src_dim != tgt_dim:
            raise UnitError(
                f"Conversione impossibile tra dimensioni {src_dim!r} e {tgt_dim!r}"
            )

        if src_dim == "temperature":
            value, precision = self._convert_temperature(quantity, target_unit)
        elif src_dim in ("slope", "angle"):
            value, precision = self._convert_slope(quantity, target_unit)
        else:
            value, precision = self._convert_linear(quantity, target_unit)

        return Quantity(
            value=value,
            unit=target_unit,
            precision=precision,
            source=quantity.source,
            timestamp=quantity.timestamp,
        )

    def _convert_linear(self, quantity: Quantity, target_unit: str) -> tuple[float, float]:
        dim = self.dimension_of(quantity.unit)
        assert dim is not None
        f_src = self._linear[dim][quantity.unit]
        f_tgt = self._linear[dim][target_unit]
        canonical = quantity.value * f_src
        value = canonical / f_tgt
        # l'incertezza si propaga linearmente col rapporto dei fattori
        precision = quantity.precision * (f_src / f_tgt)
        return value, precision

    @staticmethod
    def _convert_temperature(quantity: Quantity, target_unit: str) -> tuple[float, float]:
        # passaggio per Kelvin come unità ponte
        c = {
            "°C": quantity.value,
            "K": quantity.value - 273.15,
            "°F": (quantity.value - 32.0) * 5.0 / 9.0,
        }[quantity.unit]
        out = {
            "°C": c,
            "K": c + 273.15,
            "°F": c * 9.0 / 5.0 + 32.0,
        }[target_unit]
        # la sensibilità termica è 1:1 tra °C e K, 5/9 tra °F
        scale = 1.0 if target_unit != "°F" else 5.0 / 9.0
        return out, quantity.precision * scale

    @staticmethod
    def _convert_slope(quantity: Quantity, target_unit: str) -> tuple[float, float]:
        if quantity.unit == target_unit:
            return quantity.value, quantity.precision
        if quantity.unit == "%":
            grade = quantity.value / 100.0
            deg = math.degrees(math.atan(grade))
            # d(deg)/d(%) = (180/pi) * (1/100) / (1 + grade^2)
            scale = (math.degrees(1.0) / 100.0) / (1.0 + grade * grade)
            return deg, quantity.precision * scale
        # da gradi a percentuale
        grade = math.tan(math.radians(quantity.value))
        pct = grade * 100.0
        # d(%)/d(deg) = 100 * (pi/180) * sec^2(rad) = 100 * radians(1) * (1 + grade^2)
        scale = 100.0 * math.radians(1.0) * (1.0 + grade * grade)
        return pct, quantity.precision * scale


default_registry = UnitRegistry()


def dimension_of(unit: str) -> Optional[str]:
    return default_registry.dimension_of(unit)


def to_canonical_unit(unit: str) -> str:
    return default_registry.canonical_unit(unit)


def convert(quantity: Quantity, target_unit: str) -> Quantity:
    return default_registry.convert(quantity, target_unit)
