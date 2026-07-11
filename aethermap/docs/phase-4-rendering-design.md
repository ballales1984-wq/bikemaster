# AetherMap Engine — Phase 4: Rendering

> **Agente:** Fase 4 (Rendering)
> **Tipo:** Design Doc + prototipo
> **Regola guida:** non dare per scontata la tecnologia esistente (Leaflet/SVG/Canvas). Perché esistono tutti questi strumenti e quando usarli?

---

## 1. Il panorama degli strumenti di rendering

| Strumento | Cos'è | Quando ha senso | Limite |
|-----------|-------|-----------------|--------|
| **SVG** | grafica vettoriale DOM | mappe 2D statiche/poco dense, UI, annotazioni | non scala a milioni di primitive; il DOM esplode |
| **Canvas 2D** | bitmap immediato | 2D denso (heatmap, migliaia di punti), disegno programmatico | nessuna geometria 3D, niente pipeline GPU |
| **WebGL** | API GPU via shader | 3D interattivo, milioni di triangoli, digital twin | curva di apprendimento, gestione stato GPU |
| **GPU compute / Vulkan / WebGPU** | calcolo general-purpose sulla GPU | simulazioni, ray tracing, volume rendering, ML on-GPU | complessità massima, portabilità minore |

### Perché esistono tutti e quattro?
Perché **nessuno vince ovunque**. SVG è perfetto per pochi elementi interattivi (pulsanti, label); Canvas 2D per densità 2D; WebGL per la scena 3D; GPU compute per ciò che non è "disegno" ma "calcolo" (il ray-marching dei voxel, le simulazioni di traffico).

### Perché NON basta Leaflet/SVG per AetherMap
Leaflet è una raccolta di **tile piani (proiezione Mercator)**. Va bene per una *mappa 2D di sfondo*, ma viola i contratti di Fase 1:
- impone una proiezione piana (distorzione globale nascosta);
- non ha un digitwin 3D "vivo";
- la sua "geometria" è un'immagine, non il nostro cube-sphere heightfield.

Leaflet può restare come **minimappa 2D secondaria**, non come motore. Il motore di AetherMap è **WebGL**.

---

## 2. Raccomandazione: WebGL (con cadute controllate)

AetherMap adotta **WebGL2 / WebGPU** come spazio di rendering, con queste decisioni derivate da Fase 1 §6.2:

1. **Coordinate `float32` camera-relative.** ECEF in metri (~6.37e6) perde precisione in `float32`. Si sottrae l'origine della camera (o del tile) così le coordinate diventano `O(1e3)` → precisione sub-centimetro. (Prototipo in `render/` usa sfera unitaria, quindi il problema è annullato; il principio resta.)
2. **Cube-sphere heightfield.** La superficie è generata su 6 facce di cubo (quadtree), non su una mesh piana con cuciture ai poli.
3. **Clipmap / skirts anti-cracking.** Ai bordi delle tile si aggiungono "falde" verticali che nascondono il cracking tra LOD diversi senza topologia complessa.
4. **LOD guidato da distanza + semantica.** Una cella con una città ha LOD più alto di una cella oceanica, indipendentemente dalla distanza.
5. **Layer entità sopra la pelle.** Strade/alberi/montagne sono disegnati come overlay sopra la geometria; il loro `stato` (traffico, neve) si aggiorna senza riscrivere la geometria.
6. **Ray-marching SVO locale.** Il layer volumetrico (atmosfera, interni, sottosuolo) è renderizzato solo per le regioni selezionate, non globalmente.

---

## 3. Prototipo in `render/`

Il prototipo è **Python + pygame** per la vista interattiva (sull'hardware dell'utente) e una modalità **headless ASCII/PPM** per la verifica automatica. La matematica di proiezione è pura (numpy) e riutilizzabile tal quale in WebGL.

File:
- `projection.py` — mesh cube-sphere, rotazione camera, proiezione ortografica, camera-relative.
- `scene.py` — costruisce la scena da entità (`Strada` linea, `Albero` punto, `Montagna` bump).
- `ascii.py` — render su griglia terminale / PPM (verificabile senza display).
- `app.py` — finestra pygame interattiva (per l'utente).
- `demo.py` — lancia la modalità headless e salva un frame.
- `webgl_stub.html` — **renderer WebGL2 cube-sphere funzionante** (non un motore completo). Genera lato JS la mesh cube-sphere (6 facce, griglia NxN proiettata sulla sfera unitaria, stessa topologia di `projection.cube_sphere_mesh`), la disegna come wireframe `LINES` con rotazione camera ortografica e front-face culling su `z>0` (uguale a `project()`). Le coordinate sono **camera-relative** (`cameraRelative()` sottrae l'origine = centro sfera/target camera) così restano O(1) e si evita la perdita di precisione float32 dell'ECEF reale (~6.37e6 m). Proietta 3 entità di esempio da `scene.py` usando `geodetic_to_direction` di `core/coordinates.py` (strada=`LINE_STRIP`, albero/montagna=`POINTS`, la montagna alzata di `alt/EARTH_R`). Gli **skirt/clipmap** anti-cracking sono documentati solo come commento (bordi delle tile del quadtree), non implementati. Solo HTML+JS+WebGL2, nessun build/server.

---

## 4. Contratti per Fase 5 (Digital Twin)

- Il renderer legge `stato`/`cronologia` da `Oggetto` (Fase 2), mai la geometria mutabile.
- Ogni entità è proiettata tramite `core/coordinates.py` (cube-sphere / ECEF), mai con formule ad hoc.
- Il layer volumetrico resta opzionale e locale (rimandato a valutazione Fase 5).
