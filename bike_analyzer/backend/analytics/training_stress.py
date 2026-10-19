"""Training Stress Score (TSS) and exponentially weighted moving average.

Implementa il calcolo TSS semplificato per BikeMaster, l'EWMA usata per
derivarne CTL (chronic) e ATL (acute), e la propagazione di errore
statistico/resolution per il TSS stesso (utile per le soglie di confidenza
nel coach).

L'algoritmo TSS ``duration_h * 100 * IF^2`` e' una semplificazione della
formula TrainingPeaks (che richiede Normalized Power NP); qui, in assenza
di power stream, viene usata un'approssimazione basata su
``avg_speed_kmh`` o sull'``intensity_factor`` se disponibile.
"""

from __future__ import annotations

from .error_propagation import ErrorValue


def exponentially_weighted_moving_average(values: list[float], tau_days: float) -> float:
    """Calcola l'EWMA di una serie di valori con costante di tempo ``tau_days``.

    L'algoritmo applica ricorsivamente ``alpha * v + (1-alpha) * result``
    con ``alpha = 1 - e^(-1/tau)``. Questa formulazione produce una media
    mobile che pesa maggiormente i valori recenti e "dimentica" progressivamente
    quelli vecchi con tempo caratteristico ``tau``.

    Args:
        values: Lista di valori (es. TSS giornalieri) ordinati dal piu' vecchio
            al piu' recente.
        tau_days: Costante di tempo in giorni. Valori tipici: 42 (CTL),
            7 (ATL), 1 (carico giornaliero).

    Returns:
        Valore EWMA arrotondato a 1 decimale, oppure 0.0 se la lista e' vuota.
    """
    if not values:
        return 0.0
    alpha = 1.0 - 2.718281828459045 ** (-1.0 / tau_days)
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1.0 - alpha) * result
    return round(result, 1)


def estimate_tss(ride, ftp: float = 250.0) -> float:
    """Stima il Training Stress Score per una singola uscita.

    Usa la formula semplificata ``duration_h * 100 * IF^2`` clamp a 500.
    Per la versione con propagazione d'errore, vedi
    :func:`estimate_tss_with_error`.

    Args:
        ride: Oggetto ride con attributi ``duration_hours``, ``avg_speed_kmh``
            e opzionalmente ``intensity_factor``.
        ftp: Soglia di potenza funzionale in watt (non usata direttamente
            in questa versione semplificata, mantenuta per compatibilita' API).

    Returns:
        TSS arrotondato a 1 decimale.
    """
    result = estimate_tss_with_error(ride, ftp)
    return round(result.value, 1)


def estimate_tss_with_error(ride, ftp: float = 250.0) -> ErrorValue:
    """Stima il TSS con errore statistico e coverage.

    L'errore statistico cresce al diminuire della copertura informativa
    (manca ``duration_minutes``, ``avg_speed_kmh`` o ``intensity_factor``):
    la confidenza nel valore degrada fino a 2x quando la copertura e' 0.
    Il ``resolution_error`` fisso di 0.5 riflette la precisione intrinseca
    del modello semplificato (vs formula NP completa).
    """
    duration_h = ride.duration_hours
    if duration_h <= 0:
        return ErrorValue(value=0.0, stat_error=0.0, coverage=0.0)

    intensity_factor = 0.5
    if hasattr(ride, "intensity_factor") and ride.intensity_factor:
        intensity_factor = ride.intensity_factor
    elif ride.avg_speed_kmh and ride.avg_speed_kmh > 0:
        intensity_factor = min(ride.avg_speed_kmh / 40.0, 1.0)

    tss_value = duration_h * 100 * (intensity_factor**2)
    tss_value = min(tss_value, 500.0)

    coverage = 1.0
    if not ride.duration_minutes:
        coverage -= 0.3
    if not ride.avg_speed_kmh:
        coverage -= 0.3
    if not hasattr(ride, "intensity_factor") or not ride.intensity_factor:
        coverage -= 0.2
    coverage = max(0.0, coverage)

    base_stat_error = 0.2
    if coverage < 1.0:
        base_stat_error *= (2.0 - coverage)
    base_stat_error = min(base_stat_error, 1.0)

    return ErrorValue(
        value=round(tss_value, 1),
        stat_error=round(base_stat_error, 4),
        resolution_error=0.5,
        coverage=coverage,
    )


__all__ = ["estimate_tss", "estimate_tss_with_error", "exponentially_weighted_moving_average"]
