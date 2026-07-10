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

    # -- helper condivisi -------------------------------------------------
    @staticmethod
    def _has(value: Optional[Quantity]) -> bool:
        return value is not None and value.value != 0.0
