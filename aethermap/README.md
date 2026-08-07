# AetherMap Engine

> "Se oggi inventassimo da zero il miglior motore cartografico del mondo,
> come lo progetteremmo?"

Corso/percorso di ingegneria di un motore cartografico. Ogni scelta sfida
le convenzioni esistenti (Mercator, WGS84, Leaflet, mesh planari) con la
regola: **perché oggi si fa così? quali limiti ha? possiamo fare di meglio?**

## Struttura
```
aethermap/
  docs/
    phase-1-earth-model.md      # modello matematico Terra (cube-sphere + S2/H3)
    phase-2-data-model.md       # "database del mondo" (classe Oggetto)
    phase-4-rendering-design.md # SVG/Canvas/WebGL/GPU -> WebGL
  src/aethermap/
    core/coordinates.py         # libreria coordinate condivisa (Fase 1 §6.3)
    ai/                         # Fase 3: pipeline IA "ricercatore"
    render/                     # Fase 4: rendering cube-sphere + WebGL stub
    twin/                       # Fase 5: digital twin (oggetti vivi)
```

## Decisioni vincolanti (checkpoint utente)
- **Hardware:** ibrido web + Python backend (riusa stack BikeMaster Vue+FastAPI).
- **Risoluzione:** adattiva per zona (LOD semantico).
- **Digital twin:** real-time con latenza tollerata (stato eventualmente coerente).
- **Interoperabilità:** supporta GeoJSON / 3D Tiles / CityGML (I/O).
- **Storage prototipo:** tutto Python/Parquet + S2 (gratuito, zero server).
- **Spatial key:** S2 primario (geometria/LOD), H3 analisi.
- **Retention:** politica per-oggetto (`stale_after`).

## Esegui i prototipi
```bash
cd aethermap/src
python -m aethermap.ai.demo      # Fase 3: GPX -> strada + sensori -> traffico
python -m aethermap.render.demo  # Fase 4: globo cube-sphere ASCII
python -m aethermap.render.webgl_exporter --dem-base-url http://localhost:8000  # Fase 4: export con DEM reale dal backend BikeMaster
python -m aethermap.render.webgl_exporter --natural-earth --ne-resolution 110m  # Fase 4: export con mappa Terra reale (Natural Earth)
python -m aethermap.twin.demo    # Fase 5: oggetti vivi (giorno/sera/notte)
```
Vista interattiva (richiede pygame + display): `python -m aethermap.render.app`.
Vista WebGL (server locale): `python -m aethermap.render.server --dynamic`.
Vista WebGL con DEM reale: `python -m aethermap.render.server --dynamic --dem-base-url http://localhost:8000`.
Vista WebGL con mappa Terra reale: `python -m aethermap.render.server --dynamic --natural-earth`.
Vista WebGL con mappa Terra ad alta risoluzione: `python -m aethermap.render.server --dynamic --natural-earth --ne-resolution 50m`.

## Stato
- Fase 1-2: design doc completi e vincolati.
- Fase 3-4: prototipi Python funzionanti e verificati; WebGL2 viewer attivo con shader PBR-lite (specular + rim light), wireframe toggle (F), hover glow e label dinamiche, camera smooth reset (D), modalita' live con auto-refresh da server, overlay griglia S2 (G), filtro entita' per risoluzione S2 minima basato su zoom.
- Fase 5: digital twin attivo con SVO backend e stato ambiente-driven; nel viewer le montagne mostrano stats SVO (snow/rock/veg %) all'hover.
- DEM reale: `webgl_exporter.py` supporta `--dem-base-url` per sostituire l'FBM procedurale con tile Copernicus/SRTM dal backend BikeMaster (`/aethermap/terrain`). Server espone `/api/terrain` come proxy.
- I/O completo: GeoJSON, Parquet, 3D Tiles (b3dm) e CityGML 2.0 (Building/SolitaryVegetation/Road, gml:pos ECEF).
- ML: `models_ml.py` include SimpleNN (1-hidden-layer numpy) con persistenza JSON, oltre a ridge regression lineare.
- In corso: risoluzione S2 minima nel viewer. Completato: fix radius_summary (analytics) con filtro geodesico, overlay griglia S2 nel viewer WebGL2 (toggle G), filtro entita' per livello S2 basato su zoom.
- **Mappa Terra reale**: integrato Natural Earth (public domain) per coste, confini e citta' sulla sfera. Usa `--natural-earth` nel server o exporter. Dati scaricati da GitHub (nvkelso/natural-earth-vector) e cachati in `aethermap/geo/natural_earth/`. Default 110m (~134 coste, 333 confini, 221 citta). Opzioni: `--ne-resolution 50m` o `10m` (richiede `pip install aethermap[geo]` per semplificazione con geopandas).
