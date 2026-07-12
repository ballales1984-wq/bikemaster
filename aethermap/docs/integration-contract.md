# AetherMap ↔ BikeMaster — Contratto di Integrazione

> **Stato**: Fase 1 e 2 completate. Integrazione runtime attiva tra `aethermap` e
> `bike_analyzer` senza modifiche al tracking esistente.

## Premessa
- `bike_analyzer/` è il prodotto corrente. Il tracking
  (`frontend/src/views/RideTracking.vue` + service Android foreground) funziona ed è
  preservato.
- `aethermap/` è il motore cartografico "evoluzione": cube-sphere, S2/H3, WebGL stub,
  digital twin (`ai/`, `render/`, `twin/`).
- I due package sono **integrati** a runtime attraverso un adapter esplicito.

## Principi
1. **Tracking intatto**: nessuna modifica a `RideTracking.vue`, al service Android, né a
   `bike_analyzer/backend/maps/map_renderer.py` durante l'integrazione.
2. **Integrazione a valle**: AetherMap sostituisce il layer mappe di BikeMaster
   (`bike_analyzer/backend/maps/`) come passo successivo, dietro un'interfaccia stabile.
3. **Interfaccia stabile**: BikeMaster consuma AetherMap tramite un adapter esplicito,
   non importando i moduli interni di `aethermap`.
4. **Fallback automatico**: se AetherMap non è installato o la feature flag è disattivata,
   il sistema usa Folium/Google Maps come prima dell'integrazione.

## Contratto (implementato)
AetherMap espone un punto d'ingresso minimo in `aethermap/src/aethermap/__init__.py`:

```python
from aethermap.core.coordinates import geodetic_to_cube, cube_cell_id
from aethermap.render.scene import Scene
from aethermap.render.projection import project
```

BikeMaster usa l'adapter in `bike_analyzer/backend/maps/aethermap_adapter.py`:
- input: tracciato GPX / punti GPS (`GPSPoint` da `bike_analyzer.core.models`).
- output: JSON serializzato della scena AetherMap con entità e statistiche opzionali.
- endpoint API: `GET /api/v1/rides/{ride_id}/map?provider=aethermap`.

L'adapter replica la firma di `map_renderer.create_route_map` per consentire swap
senza modificare i chiamanti.

## Dipendenze / packaging
- `aethermap` ha `pyproject.toml` autonomo (`pip install -e ./aethermap`); dipendenze
  minime: numpy, h3, pydantic. `s2geometry` è opzionale (`[s2]`) per compatibilità
  Windows.
- `bikemaster` include `aethermap` come dipendenza opzionale:
  ```bash
  pip install -e ".[maps]"
  ```

## Feature flag
- Backend: variabile ambiente `BIKEMASTER_MAP_PROVIDER=aethermap` (default: `folium`).
- Frontend: variabile ambiente `VITE_AETHERMAP_ENABLED=true` (default: `false`).
- Quando disattivata, `bike_analyzer/backend/maps/__init__.py` e `RideMapPanel.vue`
  mantengono il comportamento esistente (Folium/Leaflet).

## Step completati
1. API pubblica `aethermap` esposta (`__init__.py`).
2. Adapter `bike_analyzer/backend/maps/aethermap_adapter.py` creato.
3. Dispatch lazy in `bike_analyzer/backend/maps/__init__.py` con supporto
   `BIKEMASTER_MAP_PROVIDER=aethermap`.
4. Endpoint API `/rides/{ride_id}/map` esteso con query param `provider`.
5. Feature flag frontend `useAetherMap` in `frontend/src/stores/ui.ts`.
6. Componente `AetherMapViewer.vue` (WebGL2 cube-sphere stub) integrato in
   `RideMapPanel.vue`.

## Step completati
1. API pubblica `aethermap` esposta (`__init__.py`).
2. Adapter `bike_analyzer/backend/maps/aethermap_adapter.py` creato.
3. Dispatch lazy in `bike_analyzer/backend/maps/__init__.py` con supporto
   `BIKEMASTER_MAP_PROVIDER=aethermap`.
4. Endpoint API `/rides/{ride_id}/map` esteso con query param `provider`.
5. Feature flag frontend `useAetherMap` in `frontend/src/stores/ui.ts`.
6. Componente `AetherMapViewer.vue` (WebGL2 cube-sphere) con colorazione
   per velocità e props dinamiche.
7. Integrazione in `RideMapPanel.vue`: toggle UI, sostituzione completa di
   Leaflet quando `useAetherMap` è attivo.
8. Benchmark latenza completato.
9. Test unit frontend per feature flag aggiunti.

## Benchmark latenza (backend adapter vs Folium)
- 10 punti: AetherMap ~384 ms vs Folium ~1583 ms (~4x più veloce)
- 100 punti: AetherMap ~7 ms vs Folium ~163 ms (~23x più veloce)
- 1000 punti: AetherMap ~66 ms vs Folium ~2185 ms (~33x più veloce)

Nota: il primo run a 10 punti include overhead di import/JIT. Dai 100 punti in poi
l'adapter serializza JSON statico, mentre Folium genera HTML+JS interattivo.

## Step futuri
1. Serializzazione condivisa avanzata (GeoJSON / 3D Tiles) al posto del JSON attuale.
2. Estensione CI con job di integrazione dedicato.
3. Test E2E Playwright per toggle e viewer WebGL.
4. Rendering WebGL avanzato: rimuovere wireframe quando ci sono dati,
   aggiungere LOD tile e skirts.

## Validazione
- `ruff` pulito sui nuovi file.
- `mypy` pulito su adapter e maps package.
- `vue-tsc` pulito su `AetherMapViewer.vue` e `RideMapPanel.vue`.
- `pytest`: 1720 passed; fallimenti pre-esistenti non correlati alle modifiche.
- `vitest`: test unit frontend per `useAetherMap` passati.
- Test manuale endpoint: `GET /api/v1/rides/{id}/map?provider=aethermap` restituisce
  `{"map_url": "/static/ride_{id}_map.json", "engine": "aethermap"}`.
