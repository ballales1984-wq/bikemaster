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
- `world.py` — `DigitalTwin` + `Environment`: `step()` ingestisce sensori
  (Fase 3) e applica l'ambiente, `snapshot()` espone lo stato vivo.
- `demo.py` — simula 3 istanti (giorno/sera/notte) e mostra l'evoluzione
  + una vista ASCII del globo.

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
