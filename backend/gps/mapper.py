"""Map generation using Folium - produces standalone HTML maps"""

from pathlib import Path
from typing import Optional

import folium
from folium import plugins
import numpy as np
from branca.colormap import LinearColormap


def _coords_to_list(lats, lons):
    if hasattr(lats, "tolist"):
        lats = lats.tolist()
    if hasattr(lons, "tolist"):
        lons = lons.tolist()
    return list(zip(lats, lons))


def generate_map(
    lat: list[float],
    lon: list[float],
    elevations: Optional[list[Optional[float]]] = None,
    speeds: Optional[list[float]] = None,
    name: str = "Ride",
    show_heatmap: bool = False,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate an interactive Folium map of the ride.
    Returns the HTML string; optionally saves to output_path.
    """
    coords = _coords_to_list(lat, lon)

    center_lat = float(np.mean(lat))
    center_lon = float(np.mean(lon))

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    folium.TileLayer(
        tiles="CartoDB positron",
        name="Light",
        control=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Streets",
        control=True,
        overlay=False,
    ).add_to(m)

    if show_heatmap and speeds is not None:
        points = [[c[0], c[1], s] for c, s in zip(coords, speeds)]
        plugins.HeatMap(points, radius=8, blur=5, min_opacity=0.4, name="Speed Heatmap").add_to(m)
    elif speeds is not None and len(speeds) == len(coords):
        colormap = LinearColormap(
            ["blue", "green", "yellow", "red"],
            vmin=min(speeds),
            vmax=max(speeds),
            caption="Speed (km/h)",
        )
        for i in range(len(coords) - 1):
            color = colormap(speeds[i])
            folium.PolyLine(
                [coords[i], coords[i + 1]],
                color=color,
                weight=5,
                opacity=0.9,
            ).add_to(m)
        colormap.add_to(m)
    else:
        folium.PolyLine(coords, color="#1e88e5", weight=5, opacity=0.9, name=name).add_to(m)

    start_marker = folium.Marker(
        coords[0],
        popup=f"<b>Start</b><br>{name}",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    end_marker = folium.Marker(
        coords[-1],
        popup=f"<b>End</b><br>{name}",
        icon=folium.Icon(color="red", icon="flag"),
    ).add_to(m)

    folium.LayerControl().add_to(m)
    folium.LatLngPopup().add_to(m)
    plugins.Fullscreen().add_to(m)
    plugins.MeasureControl().add_to(m)

    html = m._repr_html_()

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    return html
