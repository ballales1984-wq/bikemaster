"""
Folium Map Generator.
Produces standalone HTML maps for rides.
"""
from pathlib import Path
from typing import Optional

import folium
import numpy as np
from folium import plugins
from branca.colormap import LinearColormap

from backend.models.schemas import RideResponse


def generate_map(
    ride: RideResponse,
    speeds: Optional[np.ndarray] = None,
    heatmap: bool = False,
    output_path: Optional[str] = None,
) -> str:
    coords = [(p.latitude, p.longitude) for p in ride.gps_points] if hasattr(ride, 'gps_points') else []
    if not coords:
        return "<html><body>No coordinates</body></html>"

    center_lat = float(np.mean([c[0] for c in coords]))
    center_lon = float(np.mean([c[1] for c in coords]))

    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="OpenStreetMap")

    if heatmap and speeds is not None:
        points = [[c[0], c[1], s] for c, s in zip(coords, speeds)]
        plugins.HeatMap(points, radius=8, blur=5, min_opacity=0.4, name="Speed Heatmap").add_to(m)
    elif speeds is not None and len(speeds) == len(coords):
        colormap = LinearColormap(["blue", "green", "yellow", "red"],
                                  vmin=float(np.min(speeds)), vmax=float(np.max(speeds)),
                                  caption="Speed (km/h)")
        for i in range(len(coords) - 1):
            folium.PolyLine([coords[i], coords[i + 1]], color=colormap(speeds[i]),
                            weight=5, opacity=0.9).add_to(m)
        colormap.add_to(m)
    else:
        folium.PolyLine(coords, color="#1e88e5", weight=5, opacity=0.9, name=ride.name).add_to(m)

    folium.Marker(coords[0], popup=f"<b>Start</b>", icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker(coords[-1], popup=f"<b>End</b>", icon=folium.Icon(color="red", icon="flag")).add_to(m)

    folium.LayerControl().add_to(m)
    folium.LatLngPopup().add_to(m)
    plugins.Fullscreen().add_to(m)
    plugins.MeasureControl().add_to(m)

    html = m._repr_html_()
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(html, encoding="utf-8")
    return html
