# AetherMap ↔ BikeMaster — Contratto di Integrazione (roadmap futura)

> **Stato**: NON implementato. Questo documento definisce *come* AetherMap diventera'
> il motore cartografico di BikeMaster, **senza mai rompere** il tracking esistente.

## Premessa
- `bike_analyzer/` è il prodotto corrente. Il tracking
  (`frontend/src/views/RideTracking.vue` + service Android foreground) funziona ed è
  da preservare.
- `aethermap/` è il motore cartografico "evoluzione": cube-sphere, S2/H3, WebGL stub,
  digital twin (`ai/`, `render/`, `twin/`).
- Oggi i due package sono **indipendenti**: `aethermap` importa solo `aethermap.*` e
  non dipende da `bike_analyzer`. Il tooling root (pyproject, ruff/mypy/pytest, CI,
  pre-commit) copre entrambi, ma non c'è ancora integrazione runtime.

## Principi
1. **Tracking intatto**: nessuna modifica a `RideTracking.vue`, al service Android, né a
   `bike_analyzer/backend/maps/` durante l'organizzazione.
2. **Integrazione a valle**: AetherMap sostituisce il layer mappe di BikeMaster
   (`bike_analyzer/backend/maps/`: `google_maps.py`, `map_renderer.py`, `osm_maps.py`,
   `serpapi_maps.py`) come passo successivo, dietro una interfaccia stabile.
3. **Interfaccia stabile**: BikeMaster consuma AetherMap tramite un adapter esplicito,
   non importando i moduli interni di `aethermap`.

## Contratto (interfaccia proposta)
AetherMap esporra' un punto d'ingresso minimo, es.:

```python
# aethermap/src/aethermap/__init__.py (futuro)
from aethermap.core.coordinates import geodetic_to_cube, cube_cell_id
from aethermap.render.scene import Scene
from aethermap.render.projection import project
```

BikeMaster (futuro adapter in `bike_analyzer/backend/maps/aethermap_adapter.py`):
- input: tracciato GPX / punti GPS (lat, lon, alt, t).
- output: tile/scene cube-sphere pronte per il rendering WebGL (coerente con
  `render/webgl_stub.html`).

## Dipendenze / packaging
- `aethermap` ha `pyproject.toml` autonomo (`pip install -e ./aethermap`); dipendenze
  minime: numpy, h3, s2geometry, pydantic. Nessun vincolo su quelle di BikeMaster.

## Step futuri (fuori scope corrente)
1. Definire `Scene`/serializzazione condivisa (es. GeoJSON/3D Tiles).
2. Adapter `bike_analyzer/backend/maps/aethermap_adapter.py` con fallback a
   `map_renderer.py`.
3. Flag di feature per abilitare AetherMap lato backend + frontend Vue.
4. Benchmark latenza vs Folium/Google Static per parita' funzionale.

## Validazione (corrente)
- `pytest` (root) verde → tracking BikeMaster intatto.
- `ruff`/`mypy` puliti su entrambi i package.
- `python -m aethermap.ai.demo`, `render.demo`, `twin.demo` eseguono.
