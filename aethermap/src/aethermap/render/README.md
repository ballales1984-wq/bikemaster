# AetherMap Engine — Fase 4: Rendering (prototipo)

## Cosa fa
Rendering del cube-sphere (Fase 1) con entità vive (Fase 2) proiettate via
`core/coordinates.py`. Dimostra la scelta **WebGL** con cadute controllate
(camera-relative, LOD, layer entità) rispetto a SVG/Canvas/Leaflet.

## File
- `projection.py` — mesh cube-sphere, rotazione camera, proiezione ortografica.
- `scene.py` — scena di esempio (`Strada` linea, `Albero` punto, `Montagna` bump).
- `ascii.py` — render su griglia terminale (verificabile senza display).
- `demo.py` — lancia la modalità headless e salva `frame.txt`.
- `app.py` — finestra **pygame** interattiva (frecce = ruota camera).
- `webgl_stub.html` — accenno della stessa scena in **WebGL2 puro**.

## Esegui
```bash
# headless (funziona ovunque, anche CI)
python -m aethermap.render.demo

# interattivo (richiede pygame + un display)
python -m aethermap.render.app

# export con DEM reale (richiede backend BikeMaster in esecuzione)
python -m aethermap.render.webgl_exporter --dem-base-url http://localhost:8000 --output world_data_dem.json

# server con DEM reale
python -m aethermap.render.server --dynamic --dem-base-url http://localhost:8000
```

## Dove andra il WebGL reale
`webgl_stub.html` e' il viewer principale Fase 4. Funzionalita attive:
- Cube-sphere procedurale con heightfield NxN per faccia.
- Shader PBR-lite: specular highlights su entita, rim light su terreno, atmosfera blue ai bordi.
- Wireframe toggle (tasto F) per debug mesh.
- Hover interattivo: glow sull'entita' puntata e label con props dinamiche.
- Camera smooth reset (tasto D) con interpolazione esponenziale.

Integrazione DEM:
- `webgl_exporter --dem-base-url` sostituisce l'FBM procedurale delle facce equatoriali (0, 1, 4, 5) con tile Copernicus/SRTM reali dal backend BikeMaster (`GET /aethermap/terrain?min_lat=...`).
- `server.py --dem-base-url` rigenera il mondo dinamico con DEM e espone `/api/terrain` come proxy.

Prossimi passi:
- Quadtree LOD GPU camera-relative con clipmap/skirts.
- Layer volumetrico SVO montagne nel viewer WebGL.

## Limiti del prototipo
- Sfera unitaria: il problema di precisione ECEF float32 e annullato; il
  principio camera-relative resta documentato per la versione WebGL.
- Nessun heightfield/LOD reale: la mesh e a risoluzione fissa.
- Layer volumetrico (SVO) rimandato a Fase 5.
