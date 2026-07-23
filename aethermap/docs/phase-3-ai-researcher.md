# AetherMap Engine — Phase 3: Pipeline IA "Ricercatore"

> **Agente:** Fase 3 (IA per arricchimento mondo)
> **Tipo:** Design Doc + prototipo
> **Principio:** l'IA non genera la mappa, propone modifiche confutabili con confidenza.

## 1. Perche "ricercatore" e non "generatore"

Il modello generativo diretto (es. "genera la strada da questo GPX") e'
opaco: non sappiamo perche' ha scelto quella geometria, non possiamo
correggerla senza riaddestrare, e la confidenza e' un numero magico.

AetherMap adotta un'architettura a **proposte**:
1. Un sensore/gpX produce dati grezzi.
2. Il **ricercatore** analizza e produce `Proposta(tipo, campo, valore, confidence)`.
3. Il **pipeline** applica la proposta (crea/aggiorna oggetto) o la scarta.
4. Ogni proposta e' tracciabile: `motivazione`, `confidence`, `ts`.

Vantaggi:
- Umano nel loop: un operatore puo' accettare/rifiutare proposte.
- Multi-fonte: GPX, sensori, satellite, pubblico si fondono come proposte.
- Etichettatura temporale: lo stato e' a blocchi (stati successivi), non un float
  magico che cambia senza storia.
- Confidenza esplicita: ogni modifica ha `confidence`, l'utente vede "traffico 50
  (conf. 0.7)".

## 2. Architettura

```
[Ingest] -> [Ricercatore] -> [Proposte] -> [Buffer] -> [Applicatore] -> [Mondo]
                ^                                                     |
                +---- feedback (world state per nearest lookups) -----+
```

### 2.1 Ingest

Funzioni pure che convertono dati grezzi in strutture interne:
- `ingest_gpx(path)` -> `list[RawPoint]`: XML GPX sicuro (defusedxml).
- `ingest_satellite_stub(bbox)` -> `list[RawFeature]`: stub per edifici.
- `ingest_public_stub(region)` -> `list[RawFeature]`: stub per dati pubblici.
- `ingest_sensor_stream_stub(n)` -> `Iterator[RawFeature]`: stream sensori.

### 2.2 Modelli dati

Pydantic models in `ai/models.py`:
- `Posizione`: lat/lon/alt + cube_face + s2 + h3 (derivati da core/coordinates.py).
- `Geometria`: tipo ("punto"/"linea") + dati (dict generico).
- `Confidenza`: valore (0..1) + incertezza_spaziale_m + incertezza_temporale_s.
- `Oggetto`: id, tipo, posizione, geometria, proprieta, affidabilita, sorgenti,
  cronologia (append-only), relazioni (lista), stale_after_s.
- `Proposta`: target_id, nuovo, posizione, tipo, campo, valore, confidence,
  motivazione, ts.
- `Stato`: campi (dict), t, confidence.

### 2.3 Ricercatore

Classe `Researcher` in `ai/researcher.py`:
- `propose_from_gpx(points)` -> `list[Proposta]`: analizza tracciato GPX,
  propone creazione/aggiornamento strada.
- `propose_from_sensor(feat, world)` -> `Proposta`: abbina sensore a oggetto
  esistente tramite nearest-neighbor ECEF.

### 2.4 Hook ML

Il ricercatore usa un hook ML in `ai/models_ml.py`:
- `extract_gpx_features(points)` -> `GpxFeatures`: 4 feature (n_points, spanning_deg,
  elevation_variance, spatial_regularity).
- `RoadPlausibilityEstimator`: ridge regression numpy (solo numpy, no sklearn).
  Addestrata su campioni sintetici.
- `estimate_gpx(points)` -> `(plausibility, confidence)`: interfaccia stabile.

Punto di innesto futuro: qui subentrera' un vero modello ML (segmentazione
 satellitare, grafo OSM) mantenendo la stessa firma.

### 2.5 Pipeline

Classe `Pipeline` in `ai/pipeline.py`:
- `submit(proposta)` -> bufferizza proposta.
- `flush()` -> applica tutte le proposte nel buffer in batch (simula latenza).
- `_create(p)` / `_update(p)`: crea nuovo oggetto o aggiorna stato esistente.
- `_trim(obj)`: rimuove stati vecchi secondo `stale_after_s`.

### 2.6 WorldStore / SpatialStore

- `WorldStore` (AI pipeline): store dedicato al pipeline IA, mantiene
  `objects` dict per lookups veloci.
- `SpatialStore` (data layer): indicizza oggetti per S2/H3, supporta query
  spaziali (query_s2, query_h3, query_radius).
- `DigitalTwin` (twin): combina SpatialStore + Pipeline + Environment,
  orchestra `step(env)` per simulazione.

## 3. Flussi principali

### 3.1 Ingest GPX -> Strada

```
ingest_gpx(file.gpx) -> RawPoints
  -> researcher.propose_from_gpx(points) -> [Proposta(nuovo=True, tipo="strada")]
  -> pipeline.submit(proposta)
  -> pipeline.flush() -> Oggetto("strada") aggiunto al mondo
```

### 3.2 Stream sensori -> Aggiornamento traffico

```
ingest_sensor_stream_stub(n) -> [RawFeature("sensore_traffico")]
  -> per feature: researcher.propose_from_sensor(feat, world) -> Proposta(target_id="...")
  -> pipeline.submit(proposta)
  -> pipeline.flush() -> Oggetto.proprieta["traffico"] aggiornato
```

### 3.3 Step digitale con ambiente

```
env = Environment(temp_c=5.0, solar_elev_deg=30.0, ora="10:00")
  -> twin.step(env)
  -> per oggetto: _apply_env(obj, env) -> ombrata/ombra/neve calcolata
  -> snapshot() -> stato attuale leggibile
```

## 4. Decisioni vincolanti

1. **S2 come chiave spaziale primaria**: ogni Posizione deriva s2 cell id dalla
   libreria coordinate condivisa (core/coordinates.py).
2. **Latenza tollerata**: le proposte non sono applicate sincronamente. Il buffer
   raccoglie e flush() in batch, simulando il tempo di calcolo/trasmissione.
   Lo stato e' "eventualmente coerente" (Fase 1 §8.3).
3. **Modello ML minimale ma reale**: ridge regression numpy addestrata su dati
   sintetici. Il modello non dipende da rete/download; l'interfaccia e' pronta
   per sostituzione con modello reale.
4. **Retention per-oggetto**: ogni Oggetto ha `stale_after_s`. Il `_trim()` rimuove
   stati oltre la soglia (Fase 2 design doc §3).

## 5. Metriche e validazione

Test suite in `src/tests/test_ai.py`: 63 test covering:
- Ingest GPX (6 test): parsing, coordinate, elevazione, timestamp, empty.
- Ingest satellite/public/sensor stub (9 test).
- Modelli Pydantic (12 test): validazione, clamp, creazione.
- Feature extraction ML (6 test): vuoto, singolo punto, span, shape, varianza,
  regolarita'.
- RoadPlausibilityEstimator (8 test): fitting, shape, range, edge cases.
- Researcher (8 test): GPX, sensor, world targeting, nearest.
- Pipeline (14 test): research_gpx/sensor, submit, flush, create, update, trim.
- End-to-end (2 test): GPX -> store, sensor -> store.

## 6. Open Questions

1. **Modello ML reale**: quando sostituire la ridge regression con segmentazione
   satellitare + OSM? Da pianificare in Fase 4/5.
2. **Sorgenti dati reali**: da dove arrivano i dati (Copernicus, LiDAR, OSM,
   sensori privati)? Determina il layer entita'.
3. **Relazioni dinamiche**: le `Relazione` tra oggetti sono statiche o ridefinite
   da IA? Se dinamiche, servono indici inversi.
4. **Scale temporale**: real-time (stream) o batch giornaliero? Influenza
   l'architettura dello stato e la retention.
5. **Multi-tenant / sync**: quando il modello sara' usato come servizio cloud,
   come isolare i dati tra atleti? (vedi deployment_architecture in project.md).
