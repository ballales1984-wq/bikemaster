"""Stima calorie con modello MET (compendium) e modello fisico (potenza/efficienza).

Delega il calcolo vero e proprio a ``core.calculators.calories`` mantenendo
un'interfaccia stabile per i consumer (``Ride.calories`` garantito non-zero
quando i dati lo permettono).
"""

from __future__ import annotations

from dataclasses import replace

from bike_analyzer.core.calculators.calories import estimate as _core_estimate

from ..models.models import Ride


def calculate_calories_met(ride: Ride) -> float:
    """Stima calorie con metodo MET (Metabolic Equivalent of Task)."""
    return _core_estimate(ride, method="met")


def calculate_calories_physics(ride: Ride) -> float:
    """Stima calorie da modello fisico (potenza meccanica / efficienza metabolica)."""
    return _core_estimate(ride, method="physics")


def estimate_calories(ride: Ride, method: str = "met") -> float:
    """Wrapper unico per stima calorie (MET o physics)."""
    return _core_estimate(ride, method=method)


def calories_per_km(ride: Ride) -> float:
    """Calorie per chilometro (0 se distanza nulla)."""
    return ride.calories / ride.distance_km if ride.distance_km > 0 else 0.0


def ensure_calories(ride: Ride) -> float:
    """Ritorna ``ride.calories`` ricalcolandole se assenti o 0.

    Strategia di fallback per evitare calorie=0 silenti:
    1. Se ``ride.calories`` e' valorizzato, lo ritorna.
    2. Se manca ``avg_speed_kmh`` ma ci sono distanza+durata, la ricava.
    3. Se anche cosi' non c'e' velocita', ritorna 0 (input insufficiente).
    4. Altrimenti applica ``estimate_calories(method='physics')`` su una copia
       della ride con peso default 70kg se mancante.

    Returns:
        Valore calorico stimato in kcal, oppure 0.0 se i dati sono insufficienti.
    """
    if ride.calories:
        return float(ride.calories)
    avg_speed = ride.avg_speed_kmh
    if (
        not avg_speed
        and ride.distance_km
        and ride.duration_minutes
        and ride.duration_minutes > 0
    ):
        avg_speed = ride.distance_km / (ride.duration_minutes / 60)
    if not avg_speed:
        return 0.0
    updated = replace(
        ride,
        avg_speed_kmh=avg_speed,
        weight_kg=ride.weight_kg or 70.0,
    )
    return estimate_calories(updated, method="physics")
