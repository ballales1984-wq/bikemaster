"""Demo script to generate the first HTML route map."""

import sys

sys.path.insert(0, ".")

from bike_analyzer.backend.maps.map_renderer import create_route_map
from bike_analyzer.backend.processing.processing import process_route
from scripts.generate_sample_ride import generate_sample_ride


def generate_first_map():
    points = generate_sample_ride(
        n_points=50,
        center_lat=45.4654,
        center_lon=9.1859,
        radius_km=5.0,
        duration_minutes=45,
    )
    processed, stats = process_route(points)
    output_path = "bike_route_demo.html"
    create_route_map(processed, statistics=stats, output_path=output_path)
    print(f"Mappa generata: {output_path}")
    print(
        "Statistiche: "
        f"distanza={stats.total_distance_m / 1000:.2f}km, "
        f"velocità media={stats.avg_speed_km_h:.1f}km/h, pausa={stats.pause_count}"
    )
    return output_path


if __name__ == "__main__":
    generate_first_map()