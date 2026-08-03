"""Error propagation and uncertainty quantification for BikeMaster analytics.

Implements:
- Margine di errore +/-X% con regola del segno incerto
- Precisione interna e propagazione in quadratura
- Errore di risoluzione (unita' di misura)
- Errore di copertura (buchi/interruzioni)
- Trattamento elastico dei dati incompleti
- Default conservativo + incrocio fonti
- Doppio GPS e validazione incrociata
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class ErrorValue:
    """Valore con margini di errore statistico e di risoluzione.

    Attributes:
        value: Valore centrale.
        stat_error: Errore statistico (dev standard o margine).
        resolution_error: Errore di risoluzione (pavimento fisico dello strumento).
        coverage: Copertura dati (0.0-1.0), 1.0 = completo, 0.0 = mancante.
        is_certain: Se False, il segno del trend e' incerto (intervallo attraversa zero).
    """
    value: float
    stat_error: float = 0.0
    resolution_error: float = 0.0
    coverage: float = 1.0
    is_certain: bool = True

    @property
    def total_error(self) -> float:
        """Errore totale combinato in quadratura."""
        return math.sqrt(self.stat_error ** 2 + self.resolution_error ** 2)

    @property
    def margin_pct(self) -> float:
        """Margine percentuale sul valore."""
        if self.value == 0:
            return 0.0
        return (self.total_error / abs(self.value)) * 100.0

    @property
    def lower_bound(self) -> float:
        """Limite inferiore valore +/- margine."""
        return self.value - self.total_error

    @property
    def upper_bound(self) -> float:
        """Limite superiore valore +/- margine."""
        return self.value + self.total_error

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": round(self.value, 4),
            "stat_error": round(self.stat_error, 4),
            "resolution_error": round(self.resolution_error, 4),
            "total_error": round(self.total_error, 4),
            "margin_pct": round(self.margin_pct, 2),
            "coverage": round(self.coverage, 4),
            "is_certain": self.is_certain,
            "lower_bound": round(self.lower_bound, 4),
            "upper_bound": round(self.upper_bound, 4),
        }


def combine_errors_quadrature(errors: list[float]) -> float:
    """Combina errori indipendenti in quadratura."""
    return math.sqrt(sum(e ** 2 for e in errors))


def propagate_multiplication(
    value_a: float, error_a: float,
    value_b: float, error_b: float,
) -> ErrorValue:
    """Propaga errori per moltiplicazione: (A * B) con errori relativi in quadratura."""
    if value_a == 0 or value_b == 0:
        return ErrorValue(value=0.0, stat_error=combine_errors_quadrature([error_a, error_b]))
    rel_a = error_a / abs(value_a)
    rel_b = error_b / abs(value_b)
    total_rel = math.sqrt(rel_a ** 2 + rel_b ** 2)
    result_value = value_a * value_b
    result_error = abs(result_value) * total_rel
    return ErrorValue(value=result_value, stat_error=result_error)


def propagate_division(
    value_num: float, error_num: float,
    value_den: float, error_den: float,
) -> ErrorValue:
    """Propaga errori per divisione: (A / B) con errori relativi in quadratura."""
    if value_den == 0:
        return ErrorValue(value=0.0, stat_error=combine_errors_quadrature([error_num, error_den]))
    rel_num = error_num / abs(value_num) if value_num != 0 else 0.0
    rel_den = error_den / abs(value_den)
    total_rel = math.sqrt(rel_num ** 2 + rel_den ** 2)
    result_value = value_num / value_den
    result_error = abs(result_value) * total_rel
    return ErrorValue(value=result_value, stat_error=result_error)


def is_trend_certain(error_value: ErrorValue) -> bool:
    """Regola chiave: se intervallo valore +/- margine attraversa zero, il trend e' incerto."""
    return not (error_value.lower_bound < 0 < error_value.upper_bound)


def compute_coverage(valid_points: int, total_points: int) -> float:
    """Calcola la copertura dati (0.0-1.0)."""
    if total_points <= 0:
        return 0.0
    return valid_points / total_points


def coverage_weight(coverage: float, min_coverage: float = 0.5) -> float:
    """Peso proporzionale basato sulla copertura.

    Se coverage < min_coverage, il peso e' proporzionale alla copertura.
    Se coverage >= min_coverage, il peso e' 1.0.
    """
    if coverage >= min_coverage:
        return 1.0
    return max(0.0, coverage / min_coverage)


def elastic_missing_data_weight(
    reliable_count: int,
    total_count: int,
    base_weight: float = 1.0,
) -> float:
    """Trattamento elastico dei dati incompleti.

    Il peso di un'uscita dipende da quante altre uscite affidabili esistono gia'.
    - Pochi dati totali: l'uscita incerta pesa di piu' (serve calibrazione).
    - Molti dati affidabili: l'uscita incerta pesa pochissimo.
    """
    if total_count <= 0:
        return 0.0
    reliable_ratio = reliable_count / total_count
    if reliable_ratio >= 0.9:
        return base_weight * 0.1
    if reliable_ratio >= 0.7:
        return base_weight * 0.3
    if reliable_ratio >= 0.5:
        return base_weight * 0.6
    return base_weight


def conservative_default(has_reliable_signal: bool) -> float:
    """Default conservativo: se non c'e' segnale affidabile, assume utente fermo (0 progressi)."""
    return 0.0 if not has_reliable_signal else 1.0


def cross_source_correction(
    primary_value: float,
    secondary_values: list[float],
    secondary_weights: list[float] | None = None,
) -> ErrorValue:
    """Incrocio fonti: corregge il valore primario con fonti secondarie.

    Se secondary_weights e' None, tutti i pesi sono uguali.
    """
    if not secondary_values:
        return ErrorValue(value=primary_value, stat_error=0.0)

    if secondary_weights is None:
        secondary_weights = [1.0] * len(secondary_values)

    total_weight = sum(secondary_weights)
    if total_weight == 0:
        return ErrorValue(value=primary_value, stat_error=0.0)

    corrected = (
        primary_value + sum(v * w for v, w in zip(secondary_values, secondary_weights))
    ) / (1 + total_weight)

    deviations = [abs(v - corrected) for v in secondary_values] + [abs(primary_value - corrected)]
    stat_error = math.sqrt(sum(d ** 2 for d in deviations) / len(deviations))

    return ErrorValue(value=corrected, stat_error=stat_error)


def cross_validate_gps(
    primary_points: list[dict[str, Any]],
    secondary_points: list[dict[str, Any]],
    max_divergence_m: float = 5.0,
) -> dict[str, Any]:
    """Validazione incrociata GPS tra due fonti indipendenti.

    Restituisce:
    - match: se le fonti sono coerenti
    - observed_error: errore osservato (media delle divergenze)
    - stat_error_adjustment: fattore di aggiustamento dell'errore statistico
    - coverage: copertura basata su punti validi confrontabili
    """
    if not primary_points or not secondary_points:
        return {
            "match": True,
            "observed_error": 0.0,
            "stat_error_adjustment": 1.0,
            "coverage": 0.0,
        }

    matched = 0
    divergences: list[float] = []

    primary_by_time = {p.get("timestamp"): p for p in primary_points if p.get("timestamp")}
    secondary_by_time = {p.get("timestamp"): p for p in secondary_points if p.get("timestamp")}

    common_times = set(primary_by_time.keys()) & set(secondary_by_time.keys())

    for ts in common_times:
        p1 = primary_by_time[ts]
        p2 = secondary_by_time[ts]

        lat1, lon1 = p1.get("lat"), p1.get("lon")
        lat2, lon2 = p2.get("lat"), p2.get("lon")

        if None in (lat1, lon1, lat2, lon2):
            continue

        from ..models.models import haversine_distance_m
        dist = haversine_distance_m(lat1, lon1, lat2, lon2)
        divergences.append(dist)
        matched += 1

    if matched == 0:
        return {
            "match": True,
            "observed_error": 0.0,
            "stat_error_adjustment": 1.0,
            "coverage": 0.0,
        }

    avg_divergence = sum(divergences) / len(divergences)
    match = avg_divergence <= max_divergence_m

    if match:
        adjustment = 0.8
    else:
        adjustment = 1.0 + (avg_divergence / max_divergence_m)

    coverage = matched / max(len(primary_points), len(secondary_points))

    return {
        "match": match,
        "observed_error": round(avg_divergence, 2),
        "stat_error_adjustment": round(adjustment, 3),
        "coverage": round(coverage, 4),
        "matched_points": matched,
    }


__all__ = [
    "ErrorValue",
    "combine_errors_quadrature",
    "propagate_multiplication",
    "propagate_division",
    "is_trend_certain",
    "compute_coverage",
    "coverage_weight",
    "elastic_missing_data_weight",
    "conservative_default",
    "cross_source_correction",
    "cross_validate_gps",
]
