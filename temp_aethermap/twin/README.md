# AetherMap Engine — Fase 5: Digital Twin

## Cosa fa
Sintesi di Fasi 1-4: ogni oggetto del mondo e' **VIVO**. La geometria
(cube-sphere, Fase 1) resta immutabile; lo **stato** muta via:
- **stream IA** (Fase 3): sensore → proposta `traffico` applicata con latenza tollerata;
- **ambiente** (Fase 4/5): sole/temperatura → `ombra`, `neve` calcolate,
  senza mai riscrivere la geometria.

## File
- `objects.py` — `Strada`/`Albero`/`Montagna` che estendono `Oggetto` (Fase 2)
  con attributi "vivi" e metodi derivati (`pendenza()`, `ombrata()`, `neve()`…).
  `Montagna` espone anche `volume()` / `neve_interna()` / `volume_stats()` (layer SVO).
- `svo.py` — `SparseVolume`: volume SVO minimale (ottree sparso) con
  materiale per voxel (`rock`/`snow`/`vegetazione`/`vuoto`). Generato dalla
  montagna; `material_at`, `snow_fraction`, `stats`, `fraction_per_versant`.
- `world.py` — `DigitalTwin` + `Environment`: `step()` ingestisce sensori
  (Fase 3) e applica l'ambiente, `snapshot()` espone lo stato vivo.
- `demo.py` — simula 3 istanti (giorno/sera/notte) e mostra l'evoluzione
  + i `volume_stats()` della montagna (es. `NOTTE gelata` → 100% neve).

### Layer volumetrico SVO (montagna come volume vivo)
La `Montagna` non e' piu' una "pelle": `SparseVolume` la rappresenta
come griglia N^3 con materiale interno. La **linea delle nevi** dipende
dalla temperatura (`snow_line = base + 1500 + (temp_c - 15) * 100`):
22°C → 0% neve / 77.5% veg; 6°C → 22.5% neve; −3°C → 100% neve.
In produzione l'ottree diventa gerarchico (SVO) e il ray-marching e' locale
(perche il costo e' cubico: solo dove serve).

## Esegui
```bash
python -m aethermap.twin.demo
```
Vedrai `traffico` aggiornarsi, `ombrata`/`ombra` diventare `True` di sera,
e `neve=True` sulla montagna di notte gelata.

## Limiti / aperto
- Ombra/neve sono euristiche (sole=angolo, neve=temperatura): da sostituire
  con un modello solare/condizioni reali.
- Layer volumetrico (SVO) rimandato: la montagna e ancora una "pelle", non un volume.
- Rendering reale = WebGL (vedi `render/webgl_stub.html`), non l'ASCII di demo.
