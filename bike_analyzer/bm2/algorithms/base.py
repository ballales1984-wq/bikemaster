"""BikeMaster 2.0 - Model Engine: base degli algoritmi.

Principio fondamentale del sistema: ogni risultato deve riportare

    RISULTATO + formula usata + dati utilizzati + precisione + fonte

 questo è incapsulato in :class:`ModelResult`. Ogni algoritmo dichiara i
 suoi input richiesti e produce sempre un :class:`ModelResult` normalizzato.
 """

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from ..models import AnalysisContext
from ..units import Quantity

__all__ = ["ModelResult", "Algorithm", "AnalysisContext"]


@dataclass
class ModelResult:
    """Risultato di un algoritmo, completo di provenienza e incertezza.

    Attributes:
        value: valore del risultato nell'unità `unit`.
        unit: unità del risultato.
        formula: nome/descrizione della formula applicata.
        data_used: elenco dei dati di ingresso utilizzati.
        precision: incertezza assoluta stimata sul `value`.
        confidence: affidabilità stimata (0..1) in base alla completezza dei dati.
        source: algoritmo / metodo che ha prodotto il risultato.
        details: output secondari eventuali.
    """

    value: float
    unit: str
    formula: str
    data_used: list[str]
    precision: float
    confidence: float
    source: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "unit": self.unit,
            "formula": self.formula,
            "data_used": self.data_used,
            "precision": self.precision,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "details": self.details,
        }

    def uncertainty_bounds(self) -> tuple[float, float]:
        """Intervallo di incertezza: (value - precision, value + precision)."""
        return (self.value - self.precision, self.value + self.precision)

    def compare_with(self, other: "ModelResult") -> dict:
        """Confronta questo risultato con un altro. Restituisce delta e rapporto."""
        return {
            "self": self.source,
            "other": other.source,
            "delta_value": round(self.value - other.value, 4),
            "delta_confidence": round(self.confidence - other.confidence, 4),
            "self_unit": self.unit,
            "other_unit": other.unit,
            "comparable_units": self.unit == other.unit,
        }


class Algorithm(ABC):
    """Base di tutti gli algoritmi del Model Engine."""

    G = 9.81            # m/s^2
    RHO = 1.225         # densità aria kg/m^3
    SOURCE_CONFIDENCE: dict[str, float] = {
        "power_meter": 0.95,
        "hr_band": 0.8,
        "hr_sensor": 0.85,
        "gps": 0.85,
        "gps/dem": 0.75,
        "baro": 0.8,
        "manual": 0.8,
        "scale": 0.9,
        "dem": 0.7,
        "estimate": 0.5,
    }

    name: str = "algorithm"
    formula: str = ""
    description: str = ""
    unit: str = ""
    required_inputs: list[str] = field(default_factory=list)
    default_precision: float = 0.0
    default_confidence: float = 0.8

    @abstractmethod
    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Restituisce (value, precision, confidence)."""
        raise NotImplementedError

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Output secondari facoltativi (sovrascrivibile)."""
        return {}

    def run(self, ctx: AnalysisContext, extra: Optional[dict] = None) -> ModelResult:
        missing = [inp for inp in self.required_inputs if not self._has_input(ctx, extra, inp)]
        if missing:
            return ModelResult(
                value=0.0,
                unit=self.unit,
                formula=self.formula,
                data_used=list(self.required_inputs),
                precision=0.0,
                confidence=0.0,
                source=self.name,
                details={"error": f"input mancanti: {missing}"},
            )
        value, precision, confidence = self._compute(ctx, extra)
        return ModelResult(
            value=value,
            unit=self.unit,
            formula=self.formula,
            data_used=list(self.required_inputs),
            precision=precision,
            confidence=confidence,
            source=self.name,
            details=self._extra_details(ctx, extra),
        )

    @staticmethod
    def _has_input(ctx: AnalysisContext, extra: Optional[dict], name: str) -> bool:
        m = ctx.activity.metrics(ctx.transformer)
        checks = {
            "gps_points": lambda: bool(ctx.activity.points),
            "distanza": lambda: m.get("distance_m", 0) > 0,
            "durata": lambda: m.get("duration_s", 0) > 0,
            "velocità": lambda: m.get("avg_speed_ms", 0) > 0,
            "dislivello": lambda: m.get("gain_m", 0) > 0,
            "pendenza": lambda: bool(ctx.world.avg_slope_percent),
            "massa_totale": lambda: ctx.total_mass_kg > 0,
            "peso": lambda: ctx.athlete.weight_kg.value > 0,
            "ftp": lambda: ctx.athlete.ftp_w is not None and ctx.athlete.ftp_w.value > 0,
            "crr": lambda: ctx.bike.crr > 0,
            "cda": lambda: ctx.bike.cda > 0,
            "efficienza": lambda: ctx.bike.drivetrain_efficiency > 0,
            "experience_level": lambda: bool(ctx.athlete.experience_level),
            "rugosità": lambda: True,
            "capacità_atleta": lambda: bool(ctx.athlete.experience_level),
            "intensità": lambda: m.get("avg_speed_ms", 0) > 0,
            "massa_corpo": lambda: ctx.athlete.weight_kg.value > 0,
            "fatica": lambda: True,
            "sonno_ore": lambda: True,
            "hrv": lambda: True,
            "storico_attivita": lambda: True,
        }
        if name in checks:
            try:
                return checks[name]()
            except Exception:
                return False
        if extra and name in extra:
            val = extra[name]
            if isinstance(val, (int, float)):
                return val != 0
            return bool(val)
        return True

    # -- helper condivisi -------------------------------------------------
    @staticmethod
    def _has(value: Optional[Quantity]) -> bool:
        return value is not None and value.value != 0.0

    @classmethod
    def _cycling_forces(cls, mass_kg: float, slope_pct: float, crr: float, cda: float,
                        v_ms: float, wind_ms: float = 0.0, eta: float = 1.0) -> dict:
        """Forze di resistenza e potenza meccanica richiesta."""
        slope = slope_pct / 100.0
        v_air = max(v_ms + wind_ms, 0.0)
        f_roll = crr * mass_kg * cls.G
        f_grav = mass_kg * cls.G * slope
        f_air = 0.5 * cls.RHO * cda * (v_air ** 2)
        p = (f_roll + f_grav + f_air) * v_ms / max(eta, 1e-3)
        return {"roll": f_roll, "grav": f_grav, "air": f_air, "power_w": p}

    @classmethod
    def _source_confidence(cls, source: str, default: float = 0.7) -> float:
        """Affidabilità di base per fonte dati (0..1)."""
        return cls.SOURCE_CONFIDENCE.get(source, default)

    @classmethod
    def _confidence_for_source(cls, source: str, base: float = 1.0) -> float:
        """Scala una confidenza base con la qualità della fonte (capped a 1)."""
        return min(1.0, base * cls._source_confidence(source))
