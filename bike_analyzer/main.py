"""Entry point di demo per il motore di analisi BikeMaster.

Questo modulo è uno script standalone: costruisce due ``Ride`` di esempio,
calcola un riepilogo tramite ``calculate_summary`` e lo stampa a console.
Serve a verificare rapidamente il funzionamento del layer analytics senza
avviare il server FastAPI (si esegue con ``python main.py``).
"""

from bike_analyzer.backend.analytics.analytics import calculate_summary
from bike_analyzer.backend.models.models import Ride


def main() -> None:
    """Esegue la demo: crea uscite campione, calcola il riepilogo e stampa i totali.

    Le due ``Ride`` simulate coprono un giro breve (25 km) e uno medio (42 km)
    per esercitare i percorsi di calcolo di distanza, calorie, velocità e fatica.
    """
    rides = [
        Ride(
            date="2024-06-01",
            distance_km=25.3,
            duration_minutes=65,
            avg_speed_kmh=22.7,
            weight_kg=70,
            calories=420,
            heart_rate_avg=145,
            elevation_gain_m=180,
        ),
        Ride(
            date="2024-06-03",
            distance_km=42.0,
            duration_minutes=100,
            avg_speed_kmh=25.2,
            weight_kg=70,
            calories=720,
            heart_rate_avg=155,
            elevation_gain_m=320,
        ),
    ]
    s = calculate_summary(rides)
    print(
        f"=== BikeMaster ===\nRides: {s['total_rides']}\n"
        f"Distance: {s['total_km']:.1f} km\n"
        f"Calories: {s['total_calories']:.0f} kcal\n"
        f"Avg Speed: {s['avg_speed']:.1f} km/h\n"
        f"Avg Fatigue: {s['avg_fatigue']:.1f}/10"
    )


if __name__ == "__main__":
    main()
