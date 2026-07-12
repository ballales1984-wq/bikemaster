"""Benchmark AetherMap adapter vs Folium map_renderer."""

from __future__ import annotations

import time
from datetime import datetime

from bike_analyzer.core.models import GPSPoint, RouteStatistics
from bike_analyzer.backend.maps import aethermap_adapter
from bike_analyzer.backend.maps.map_renderer import create_route_map as folium_create_route_map


def _points(n: int) -> list[GPSPoint]:
    base_lat = 45.0
    base_lon = 9.0
    return [
        GPSPoint(
            lat=base_lat + i * 0.0001,
            lon=base_lon + i * 0.0001,
            timestamp=datetime.now(),
            altitude=100.0 + i,
            speed=20.0 + (i % 20),
        )
        for i in range(n)
    ]


def benchmark(name: str, fn, *args, runs: int = 5) -> None:
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        fn(*args)
        times.append(time.perf_counter() - start)
    avg = sum(times) / len(times)
    print(f"{name:40s}  avg={avg*1000:.2f} ms  runs={runs}")


def main() -> None:
    import tempfile
    from pathlib import Path

    base = Path(tempfile.mkdtemp(prefix="aethermap_bench_"))

    for n in (10, 100, 1000):
        pts = _points(n)
        aether_out = base / f"aether_{n}.json"
        folium_out = base / f"folium_{n}.html"

        print(f"\n--- {n} points ---")
        benchmark("aethermap_adapter", aethermap_adapter.create_route_map, pts, None, str(aether_out))
        benchmark("folium_map_renderer", folium_create_route_map, pts, None, str(folium_out))


if __name__ == "__main__":
    main()
