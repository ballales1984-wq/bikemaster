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
from urllib.parse import urlparse

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
        if path == "/api/step":
            self._serve_step()
            return
        if path == "/":
            self._serve_html()
            return
        if path.startswith("/world_data.json"):
            self._serve_world_data()
            return

        super().do_GET()

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
        with self._dynamic_lock:
            env = Environment(temp_c=15.0, solar_elev_deg=30.0, ora="12:00")
            twin: DigitalTwin = self._world_data["_twin"]  # type: ignore[index]
            twin.step(env)
            self._world_data["entities"] = [
                _entity_to_gl(obj) for obj in twin.store.objects.values()
            ]
        self._send_json_or_text(200, json.dumps({"ok": True, "entities": self._world_data["entities"]}), "application/json")

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


def _build_dynamic_world(dem_url: str | None = None) -> dict[str, Any]:
    from aethermap.render.webgl_exporter import _terrain_mesh
    from aethermap.render.terrain_enhancer import build_enhanced_heightfield

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
    result = {
        "version": "aethermap-webgl-1.0",
        "terrain": terrain,
        "entities": entities,
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
) -> HTTPServer:
    """Avvia il server AetherMap sulla porta specificata."""
    AetherMapHandler._bikemaster_url = bikemaster_url or "http://localhost:8000"
    if dynamic:
        import threading
        lock = threading.Lock()
        world = _build_dynamic_world(dem_base_url)
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
        print(f"[server] Modalita' dinamica: DigitalTwin attivo")
        print(f"[server] API step: GET /api/step")
    if dem_base_url:
        print(f"[server] DEM integration: {dem_base_url}")
    print(f"[server] Apri {addr} nel browser.")
    print(f"[server] Premi Ctrl+C per fermare.")
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
    args = parser.parse_args()

    serve(
        port=args.port,
        static_world=args.static,
        static_html_dir=args.html_dir,
        dynamic=args.dynamic,
        dem_base_url=args.dem_base_url,
        bikemaster_url=args.bikemaster_url,
    )


if __name__ == "__main__":
    main()
