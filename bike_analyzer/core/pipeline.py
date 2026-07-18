"""Core processing pipeline: ingestion → processing → analytics → fitness state.

La pipeline trasforma una attivita' grezza (``Ride``) in:
1. Statistiche di percorso (``RouteStatistics``) tramite pulizia GPS.
2. Metriche aggregate (fatica, recupero, calorie, performance, TSS).
3. (Opzionale) Fitness State Vector (ATL/CTL/TSB) tramite ``AnalysisEngine``.

L'architettura e' sincrona per le operazioni CPU-bound (GPS, metriche)
ma supporta anche un'esecuzione asincrona per compatibilita' con il resto
del backend FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Ride, RouteStatistics


@dataclass
class PipelineResult:
    """Contenitore del risultato di una analisi di attivita'.

    Attributes:
        ride: L'attivita' originale (eventualmente modificata con GPS puliti).
        route_statistics: Statistiche aggregate del percorso (distanza, dislivello,
            velocita' media, ecc.) o None se non presenti punti GPS.
        fitness_snapshot: Dizionario con ATL/CTL/TSB calcolati per questa attivita'.
        metrics: Metriche aggregate (fatica, recupero, calorie, performance, TSS).
    """
    ride: Ride
    route_statistics: RouteStatistics | None = None
    fitness_snapshot: dict | None = None
    metrics: dict | None = None


class AnalysisPipeline:
    """Pipeline di elaborazione che trasforma una attivita' grezza in statistiche e metriche.

    Attributi:
        ftp: Functional Threshold Power in watt, usata per il calcolo del TSS.

    Passi della pipeline:
    1. Pulizia GPS e calcolo statistiche di percorso (``_process_gps``).
    2. Calcolo metriche: fatica, recupero, calorie, performance, potenza (``_compute_metrics``).
    """

    def __init__(self, ftp: float = 250.0) -> None:
        """Create the pipeline with the athlete's FTP in watts.

        Args:
            ftp: Functional Threshold Power used for TSS calculation.
                Default 250W.
        """
        self.ftp = ftp

    async def run(self, ride: Ride) -> PipelineResult:
        """Execute the pipeline asynchronously for a ride.

        Args:
            ride: Cycling activity to process.

        Returns:
            PipelineResult con statistiche percorso e metriche aggregate.
        """
        stats = self._process_gps(ride)
        metrics = self._compute_metrics(ride)
        return PipelineResult(ride=ride, route_statistics=stats, metrics=metrics)

    def run_sync(self, ride: Ride) -> PipelineResult:
        """Execute the pipeline synchronously for a ride.

        Args:
            ride: Cycling activity to process.

        Returns:
            PipelineResult con statistiche percorso e metriche aggregate.
        """
        stats = self._process_gps(ride)
        metrics = self._compute_metrics(ride)
        return PipelineResult(ride=ride, route_statistics=stats, metrics=metrics)

    def _process_gps(self, ride: Ride) -> RouteStatistics | None:
        """Pulisce i punti GPS e calcola le statistiche di percorso.

        Usa ``process_route`` dal backend processing per pulizia outlier,
        rilevamento pause e calcolo statistiche aggregate. Modifica
        ``ride.gps_points`` in-place con i punti puliti.

        Args:
            ride: Attivita' con punti GPS grezzi.

        Returns:
            RouteStatistics aggregate, o None se non ci sono punti GPS.
        """
        if not ride.gps_points:
            return None
        from bike_analyzer.backend.processing.processing import process_route

        cleaned, stats = process_route(ride.gps_points)
        ride.gps_points = cleaned
        return stats

    def _compute_metrics(self, ride: Ride) -> dict:
        """Calcola tutte le metriche aggregate per l'attivita'.

        Calcola: fatica, ore di recupero stimate, calorie, punteggio
        performance, efficienza e Training Stress Score (TSS).

        Args:
            ride: Attivita' elaborata con GPS puliti.

        Returns:
            Dizionario con chiavi: ``fatigue_score``, ``recovery_hours``,
            ``calories``, ``performance_score``, ``efficiency_score``, ``tss``.
        """
        from .calculators import calories, fatigue, performance, power

        fatigue_score = fatigue.calculate_fatigue_score(ride)
        return {
            "fatigue_score": round(fatigue_score, 1),
            "recovery_hours": round(fatigue.estimate_recovery_hours(fatigue_score), 1),
            "calories": round(calories.estimate(ride), 0),
            "performance_score": performance.performance_score(ride),
            "efficiency_score": performance.efficiency_score(ride),
            "tss": power.training_stress_score(ride, self.ftp),
        }
