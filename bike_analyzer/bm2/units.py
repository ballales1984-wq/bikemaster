"""BikeMaster 2.0 - Internal measurement system.

This module defines the fundamental concept of *physical quantity*:

    VALUE + UNIT + PRECISION + SOURCE

and the conversion registry between measurement units. All algorithms
in the system operate on normalized quantities (internal canonical units),
never on "raw" source units (Garmin, Strava, manual entry...).

Internal canonical units (BikeMaster standard):
    mass      -> kg
    length    -> m
    speed     -> m/s
    time      -> s
    energy    -> J
    power     -> W
    slope     -> %  (percentage)
    angle     -> deg
    frequency -> Hz
    temperature-> °C
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
# Physical quantity: value + unit + precision + source
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Quantity:
    """A measured quantity with its uncertainty and origin.

    Attributes:
        value: numeric value in the specified `unit`.
        unit: unit of measure symbol (e.g. ``"kg"``, ``"m/s"``, ``"%"").
        precision: estimated absolute uncertainty in the same unit as `value`.
        source: data origin (e.g. ``"garmin"``, ``"manual"``, ``"gps/dem"").
        timestamp: measurement time, if known.
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
    """Quick constructor for :class:`Quantity`."""
    return Quantity(value=value, unit=unit, precision=precision, source=source, timestamp=timestamp)


# ---------------------------------------------------------------------------
# Unit of measure registry
# ---------------------------------------------------------------------------
# Linear dimensions: multiplicative factor toward canonical unit.
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

# Canonical units per dimension.
_CANONICAL: dict[str, str] = {
    "mass": "kg", "length": "m", "speed": "m/s", "time": "s",
    "energy": "J", "power": "W",     "frequency": "bpm",
    "slope": "%", "angle": "deg", "temperature": "°C",
    "pressure": "Pa", "density": "kg/m^3", "torque": "Nm",
}

# Non-linear dimensions handled with dedicated formulas.
_SPECIAL = {"slope", "angle", "temperature"}


class UnitError(ValueError):
    """Unit conversion error (incompatible or unknown dimension)."""


class UnitRegistry:
    """Unit of measure registry and conversion engine.

    Linear conversions use a factor toward the canonical unit; non-linear
    conversions (temperature, slope/angle) use dedicated formulas.
    """

    def __init__(self, linear: Optional[dict[str, dict[str, float]]] = None) -> None:
        self._linear = dict(_LINEAR)
        if linear:
            for dim, units in linear.items():
                self._linear.setdefault(dim, {}).update(units)

    # -- introspection ----------------------------------------------------
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
            raise UnitError(f"Unknown unit: {unit!r}")
        return _CANONICAL[dim]

    def to_canonical(self, quantity: Quantity) -> Quantity:
        """Convert a quantity to the canonical unit of its dimension."""
        target = self.canonical_unit(quantity.unit)
        if target == quantity.unit:
            return quantity
        return self.convert(quantity, target)

    # -- conversion ------------------------------------------------------
    def explain_conversion(self, quantity: Quantity, target_unit: str) -> list[str]:
        """Describe the steps of a unit conversion."""
        src_dim = self.dimension_of(quantity.unit)
        tgt_dim = self.dimension_of(target_unit)
        steps = [
            f"From {quantity.value} {quantity.unit} to {target_unit}",
            f"Dimensions: {src_dim} -> {tgt_dim}",
        ]
        if src_dim != tgt_dim:
            steps.append("ERROR: incompatible dimensions")
            return steps
        if src_dim == "temperature":
            steps.append("Intermediate step: Kelvin")
            scale = 1.0 if target_unit != "°F" else 5.0 / 9.0
            steps.append(f"Conversion scale: {scale}")
        elif src_dim in ("slope", "angle"):
            steps.append("Non-linear conversion: atan/tan")
        else:
            f_src = self._linear[src_dim][quantity.unit]
            f_tgt = self._linear[src_dim][target_unit]
            canon = self.canonical_unit(quantity.unit)
            steps.append(f"Factor to canonical ({canon}): {f_src}")
            steps.append(f"Factor from canonical to {target_unit}: {f_tgt}")
        return steps

    def convert(self, quantity: Quantity, target_unit: str) -> Quantity:
        src_dim = self.dimension_of(quantity.unit)
        tgt_dim = self.dimension_of(target_unit)
        if src_dim is None or tgt_dim is None:
            raise UnitError(f"Unknown unit: {quantity.unit!r} or {target_unit!r}")
        if src_dim != tgt_dim:
            raise UnitError(
                f"Cannot convert between dimensions {src_dim!r} and {tgt_dim!r}"
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
        # uncertainty propagates linearly with the ratio of factors
        precision = quantity.precision * (f_src / f_tgt)
        return value, precision

    @staticmethod
    def _convert_temperature(quantity: Quantity, target_unit: str) -> tuple[float, float]:
        # Kelvin as bridge unit
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
        # thermal sensitivity is 1:1 between °C and K, 5/9 between °F
        scale = 1.0 if target_unit != "°F" else 5.0 / 9.0
        return out, quantity.precision * scale

    @staticmethod
    def _convert_slope(quantity: Quantity, target_unit: str) -> tuple[float, float]:
        if quantity.unit == target_unit:
            return quantity.value, quantity.precision
        if quantity.unit == "%":
            # % -> degrees: deg = atan(slope/100). The sensitivity (derivative
            # of conversion) propagates uncertainty: d(deg)/d(%) is
            # maximum at slope 0 and decays with 1/(1+grade²).
            grade = quantity.value / 100.0
            deg = math.degrees(math.atan(grade))
            scale = (math.degrees(1.0) / 100.0) / (1.0 + grade * grade)
            return deg, quantity.precision * scale
        # from degrees to percentage: pct = 100·tan(rad). Sensitivity = 100·rad(1)·sec²
        grade = math.tan(math.radians(quantity.value))
        pct = grade * 100.0
        scale = 100.0 * math.radians(1.0) * (1.0 + grade * grade)
        return pct, quantity.precision * scale


default_registry = UnitRegistry()


def dimension_of(unit: str) -> Optional[str]:
    return default_registry.dimension_of(unit)


def to_canonical_unit(unit: str) -> str:
    return default_registry.canonical_unit(unit)


def convert(quantity: Quantity, target_unit: str) -> Quantity:
    return default_registry.convert(quantity, target_unit)
