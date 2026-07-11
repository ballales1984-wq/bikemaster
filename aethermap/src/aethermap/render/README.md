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
```

## Dove andra il WebGL reale
`webgl_stub.html` è solo uno scheletro: la mesh cube-sphere andra generata
lato GPU (quadtree per faccia), con `float32` *relative all'origine camera*
e clipmap/skirts per evitare il cracking LOD. Il layer entità (stato vivo)
sara un overlay che legge `Oggetto.cronologia` senza riscrivere la geometria.

## Limiti del prototipo
- Sfera unitaria: il problema di precisione ECEF float32 e annullato; il
  principio camera-relative resta documentato per la versione WebGL.
- Nessun heightfield/LOD reale: la mesh e a risoluzione fissa.
- Layer volumetrico (SVO) rimandato a Fase 5.
