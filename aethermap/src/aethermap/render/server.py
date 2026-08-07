"""AetherMap Fase 4 — HTTP server per il viewer WebGL.

Avvia un server locale che serve la pagina WebGL e i dati del mondo.
Supporta due modalita' di dati:
- **Static**: carica un file JSON pre-generato (world_data.json).
- **Dynamic**: genera dati on-the-fly da un DigitalTwin.

Uso:
    python -m aethermap.render.server [--port 8080] [--static world_data.json]
    python -m aethermap.render.server --dynamic [--port 8080]
"""
from __future__ import annotations

import argparse
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from aethermap.render.webgl_exporter import _entity_to_gl, _terrain_mesh
from aethermap.twin.objects import make_albero, make_montagna, make_strada
from aethermap.twin.world import DigitalTwin, Environment


class AetherMapHandler(SimpleHTTPRequestHandler):
    """Request handler che serve il viewer AetherMap e l'API dati."""

    _html_content: str | None = None
    _world_data: dict[str, Any] | None = None
    _static_path: Path | None = None
    _dynamic: bool = False
    _dynamic_lock: Any = None
    _bikemaster_url: str = "http://localhost:8000"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/world":
            self._serve_world_data()
            return
        if path == "/api/terrain":
            self._serve_terrain_tile()
            return
        if path == "/api/terrain-enhanced":
            self._serve_terrain_enhanced()
            return
        if path == "/api/terrain-tile":
            self._serve_terrain_tile_lod()
            return
        if path == "/api/step":
            self._serve_step()
            return
        if path == "/api/snapshot":
            self._serve_snapshot()
            return
        if path == "/api/save":
            self._serve_save()
            return
        if path == "/api/export":
            self._serve_export()
            return
        if path == "/api/geojson":
            self._serve_geojson()
            return
        if path == "/":
            self._serve_html()
            return
        if path.startswith("/world_data.json"):
            self._serve_world_data()
            return

        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/load":
            self._serve_load()
            return
        self.send_response(501)
        self.end_headers()

    def _serve_save(self) -> None:
        if not self._dynamic or not self._dynamic_lock:
            self._send_json_or_text(404, '{"error": "Dynamic mode not enabled"}', "application/json")
            return
        with self._dynamic_lock:
            twin: DigitalTwin = self._world_data["_twin"]  # type: ignore[index]
            out_path = Path(__file__).resolve().parent / "world_state.json"
            twin.save_json(out_path)
        self._send_json_or_text(200, json.dumps({"ok": True, "path": str(out_path)}), "application/json")

    def _serve_load(self) -> None:
        if not self._dynamic or not self._dynamic_lock:
            self._send_json_or_text(404, '{"error": "Dynamic mode not enabled"}', "application/json")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        with self._dynamic_lock:
            twin: DigitalTwin = self._world_data["_twin"]  # type: ignore[index]
            twin.store.objects.clear()
            twin.load_json(json.loads(body))
            twin._build_relations()
            self._world_data["entities"] = [
                _entity_to_gl(obj) for obj in twin.store.objects.values()
            ]
            self._world_data["relations"] = [
                {"from": obj.id, "to": rel.target_id, "tipo": rel.tipo, "peso": rel.peso}
                for obj in twin.store.objects.values()
                for rel in obj.relazioni
            ]
        body = json.dumps({
            "ok": True,
            "entities": self._world_data["entities"],
            "relations": self._world_data.get("relations", []),
        })
        self._send_json_or_text(200, body, "application/json")

    def _serve_terrain_tile(self, params: dict | None = None) -> None:
        bikemaster = getattr(self.__class__, "_bikemaster_url", "http://localhost:8000")
        try:
            import urllib.request
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            url = f"{bikemaster}/aethermap/terrain{('?' + qs) if qs else ''}"
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = resp.read()
            self._send_json_or_text(200, data.decode("utf-8"), "application/json")
        except Exception as exc:
            self._send_json_or_text(502, json.dumps({"error": str(exc)}), "application/json")

    def _serve_terrain_enhanced(self) -> None:
        try:
            from aethermap.render.terrain_enhancer import build_enhanced_heightfield
            hf = build_enhanced_heightfield(
                n=64,
                base_alt=0.0,
                height_scale=0.04,
                base_url=getattr(self.__class__, "_bikemaster_url", "http://localhost:8000"),
            )
            from aethermap.render.webgl_exporter import _terrain_mesh_from_hf
            terrain = _terrain_mesh_from_hf(hf, 64)
            payload = json.dumps({
                "terrain": terrain,
                "dem_source": "backend-dem",
            })
            self._send_json_or_text(200, payload, "application/json")
        except Exception as exc:
            self._send_json_or_text(500, json.dumps({"error": str(exc)}), "application/json")

    def _serve_terrain_tile_lod(self) -> None:
        qs = parse_qs(urlparse(self.path).query)
        face = int(qs.get("face", [0])[0])
        resolution = int(qs.get("resolution", [64])[0])
        try:
            from aethermap.render.terrain_enhancer import _face_bbox, build_enhanced_heightfield
            from aethermap.render.webgl_exporter import _terrain_mesh_from_hf
            hf = build_enhanced_heightfield(
                n=resolution,
                base_alt=0.0,
                height_scale=0.04,
                base_url=getattr(self.__class__, "_bikemaster_url", "http://localhost:8000"),
            )
            bbox = _face_bbox(face, resolution)
            tile = _terrain_mesh_from_hf(hf.reshape(6, resolution, resolution), resolution)
            payload = json.dumps({
                "face": face,
                "resolution": resolution,
                "bbox": bbox,
                "terrain": tile,
                "dem_source": "backend-dem",
            })
            self._send_json_or_text(200, payload, "application/json")
        except Exception as exc:
            self._send_json_or_text(500, json.dumps({"error": str(exc)}), "application/json")

    def _serve_html(self) -> None:
        html_path = (
            self._static_path / "webgl_stub.html"
            if self._static_path
            else Path(__file__).resolve().parent / "webgl_stub.html"
        )
        content = html_path.read_text(encoding="utf-8")
        self._send_json_or_text(200, content, "text/html")

    def _serve_world_data(self) -> None:
        if self._world_data is not None:
            payload = json.dumps(self._world_data)
            self._send_json_or_text(200, payload, "application/json")
            return
        fallback = Path(__file__).resolve().parent / "world_data.json"
        if fallback.exists():
            content = fallback.read_text(encoding="utf-8")
            self._send_json_or_text(200, content, "application/json")
            return
        self._send_json_or_text(404, '{"error": "No world data available"}', "application/json")

    def _serve_step(self) -> None:
        if not self._dynamic or not self._dynamic_lock:
            self._send_json_or_text(404, '{"error": "Dynamic mode not enabled"}', "application/json")
            return
        qs = parse_qs(urlparse(self.path).query)
        temp_c = float(qs.get("temp_c", [15.0])[0])
        solar_elev_deg = float(qs.get("solar_elev_deg", [30.0])[0])
        with self._dynamic_lock:
            env = Environment(temp_c=temp_c, solar_elev_deg=solar_elev_deg, ora="12:00")
            twin: DigitalTwin = self._world_data["_twin"]  # type: ignore[index]
            twin.step(env)
            self._world_data["entities"] = [
                _entity_to_gl(obj) for obj in twin.store.objects.values()
            ]
            self._world_data["relations"] = [
                {"from": obj.id, "to": rel.target_id, "tipo": rel.tipo, "peso": rel.peso}
                for obj in twin.store.objects.values()
                for rel in obj.relazioni
            ]
        body = json.dumps({
            "ok": True,
            "entities": self._world_data["entities"],
            "relations": self._world_data.get("relations", []),
        })
        self._send_json_or_text(200, body, "application/json")

    def _serve_snapshot(self) -> None:
        if not self._dynamic or not self._dynamic_lock:
            self._send_json_or_text(404, '{"error": "Dynamic mode not enabled"}', "application/json")
            return
        with self._dynamic_lock:
            twin: DigitalTwin = self._world_data["_twin"]  # type: ignore[index]
            snap = twin.snapshot()
        self._send_json_or_text(200, json.dumps(snap), "application/json")

    def _serve_export(self) -> None:
        if self._world_data is None:
            self._send_json_or_text(404, '{"error": "No world data available"}', "application/json")
            return
        payload = json.dumps(self._world_data, ensure_ascii=False, indent=2)
        self._send_json_or_text(200, payload, "application/json")

    def _serve_geojson(self) -> None:
        from aethermap.render.webgl_exporter import export_world_geojson

        if self._world_data is None:
            self._send_json_or_text(404, '{"error": "No world data available"}', "application/json")
            return
        twin = DigitalTwin()
        twin.add(make_strada("strada-1", 45.0, 9.0, [
            {"lat": 45.0 + i * 0.0005, "lon": 9.0 + i * 0.0006, "ele": 120 + (i % 2) * 2}
            for i in range(6)
        ]))
        twin.add(make_albero("albero-1", 45.005, 9.01, "quercia", 8.5))
        twin.add(make_montagna("montagna-1", 45.015, 9.03, 1800.0, ["nord", "sud", "est"]))
        env = Environment(temp_c=15.0, solar_elev_deg=30.0, ora="12:00")
        twin.step(env)
        import os
        import tempfile
        tmp = os.path.join(tempfile.gettempdir(), "aethermap_geojson.json")
        export_world_geojson(twin, tmp)
        payload = Path(tmp).read_text(encoding="utf-8")
        self._send_json_or_text(200, payload, "application/geojson")

    def _send_json_or_text(self, code: int, content: str, content_type: str) -> None:
        payload = content.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        print(f"[server] {format % args}")


def _load_static_world(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _build_dynamic_world(
    dem_url: str | None = None,
    natural_earth: bool = False,
    ne_resolution: str = "110m",
) -> dict[str, Any]:
    from aethermap.geo.natural_earth import load_cities, load_coastlines, load_country_borders
    from aethermap.geo.natural_earth import to_entities as ne_to_entities
    from aethermap.render.webgl_exporter import _entity_to_gl, _natural_earth_entity_to_gl

    twin = DigitalTwin()
    twin.add(make_strada("strada-1", 45.0, 9.0, [
        {"lat": 45.0 + i * 0.0005, "lon": 9.0 + i * 0.0006, "ele": 120 + (i % 2) * 2}
        for i in range(6)
    ]))
    twin.add(make_albero("albero-1", 45.005, 9.01, "quercia", 8.5))
    twin.add(make_montagna("montagna-1", 45.015, 9.03, 1800.0, ["nord", "sud", "est"]))
    env = Environment(temp_c=15.0, solar_elev_deg=30.0, ora="12:00")
    twin.step(env)
    terrain = _terrain_mesh(64)
    entities = [_entity_to_gl(obj) for obj in twin.store.objects.values()]
    relations = [
        {"from": obj.id, "to": rel.target_id, "tipo": rel.tipo, "peso": rel.peso}
        for obj in twin.store.objects.values()
        for rel in obj.relazioni
    ]

    if natural_earth:
        try:
            ne_data = ne_to_entities(
                coastlines=load_coastlines(resolution=ne_resolution),
                borders=load_country_borders(resolution=ne_resolution),
                cities=load_cities(resolution=ne_resolution, min_pop=50000),
            )
            for ne_ent in ne_data["entities"]:
                entities.append(_natural_earth_entity_to_gl(ne_ent))
            print(f"[server] Natural Earth: +{ne_data['coastline_count']} coastlines, "
                  f"+{ne_data['border_count']} borders, +{ne_data['city_count']} cities")
        except Exception as exc:
            print(f"[server] Natural Earth data unavailable: {exc}")

    result = {
        "version": "aethermap-webgl-1.0",
        "terrain": terrain,
        "entities": entities,
        "relations": relations,
        "camera": {"yaw": 0.6, "pitch": 0.35},
        "earth_r": 6_371_000.0,
        "_twin": twin,
    }
    if dem_url:
        result["dem_source"] = dem_url
    return result


def serve(
    port: int = 8080,
    static_world: str | Path | None = None,
    static_html_dir: str | Path | None = None,
    dynamic: bool = False,
    dem_base_url: str | None = None,
    bikemaster_url: str | None = None,
    natural_earth: bool = False,
    ne_resolution: str = "110m",
) -> HTTPServer:
    """Avvia il server AetherMap sulla porta specificata."""
    AetherMapHandler._bikemaster_url = bikemaster_url or "http://localhost:8000"
    if dynamic:
        import threading
        lock = threading.Lock()
        world = _build_dynamic_world(dem_base_url, natural_earth, ne_resolution)
        AetherMapHandler._world_data = {k: v for k, v in world.items() if not k.startswith("_")}
        AetherMapHandler._dynamic = True
        AetherMapHandler._dynamic_lock = lock
    else:
        if static_world:
            AetherMapHandler._world_data = _load_static_world(static_world)
    if static_html_dir:
        AetherMapHandler._static_path = Path(static_html_dir)
    else:
        AetherMapHandler._static_path = Path(__file__).resolve().parent

    server = HTTPServer(("0.0.0.0", port), AetherMapHandler)
    addr = f"http://localhost:{port}"
    print(f"[server] AetherMap WebGL viewer attivo su {addr}")
    if dynamic:
        print("[server] Modalita' dinamica: DigitalTwin attivo")
        print("[server] API step: GET /api/step")
    if dem_base_url:
        print(f"[server] DEM integration: {dem_base_url}")
    print(f"[server] Apri {addr} nel browser.")
    print("[server] Premi Ctrl+C per fermare.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Fermato.")
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="AetherMap WebGL server")
    parser.add_argument("--port", type=int, default=8080, help="Porta di ascolto")
    parser.add_argument("--static", type=str, default=None, help="Percorso a world_data.json pre-generato")
    parser.add_argument("--html-dir", type=str, default=None, help="Directory contenente webgl_stub.html")
    parser.add_argument("--dynamic", action="store_true", help="Modalita' dinamica: genera dati da DigitalTwin")
    parser.add_argument("--dem-base-url", type=str, default=None, help="URL backend BikeMaster per DEM reale (es. http://localhost:8000)")
    parser.add_argument("--bikemaster-url", type=str, default=None, help="URL backend BikeMaster per proxy tile (es. http://localhost:8000)")
    parser.add_argument("--natural-earth", action="store_true",
                        help="Carica dati Natural Earth (coste, confini, citta)")
    parser.add_argument("--ne-resolution", type=str, default="110m",
                        choices=["10m", "50m", "110m"],
                        help="Risoluzione dati Natural Earth")
    args = parser.parse_args()

    serve(
        port=args.port,
        static_world=args.static,
        static_html_dir=args.html_dir,
        dynamic=args.dynamic,
        dem_base_url=args.dem_base_url,
        bikemaster_url=args.bikemaster_url,
        natural_earth=args.natural_earth,
        ne_resolution=args.ne_resolution,
    )


if __name__ == "__main__":
    main()
