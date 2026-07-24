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
python -m aethermap.twin.demo    # Fase 5: oggetti vivi (giorno/sera/notte)
```
Vista interattiva (richiede pygame + display): `python -m aethermap.render.app`.
Vista WebGL (server locale): `python -m aethermap.render.server --dynamic`.
Vista WebGL con DEM reale: `python -m aethermap.render.server --dynamic --dem-base-url http://localhost:8000`.

## Stato
- Fase 1-2: design doc completi e vincolati.
- Fase 3-4: prototipi Python funzionanti e verificati; WebGL2 viewer attivo con shader PBR-lite (specular + rim light), wireframe toggle (F), hover glow e label dinamiche, camera smooth reset (D).
- Fase 5: digital twin attivo con SVO backend e stato ambiente-driven.
- DEM reale: `webgl_exporter.py` supporta `--dem-base-url` per sostituire l'FBM procedurale con tile Copernicus/SRTM dal backend BikeMaster (`/aethermap/terrain`). Server espone `/api/terrain` come proxy.
- In corso: sostituzione modello IA numpy con modello addestrato, storage Parquet/PostGIS completo, risoluzione S2 minima.
