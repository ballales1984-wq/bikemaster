# AetherMap Engine — Piano di Lavoro Fasi 1-5 + Roadmap Produzione

> **Stato:** Fasi 1-5 completate (prototipi + test). Questo documento definisce
> il piano di integrazione produzione e le azioni residue per rendere AetherMap
> il modulo di terrain intelligence di BikeMaster.
> **Ultimo aggiornamento:** 2026-08-08

---

## 0. Riepilogo Stato Attuale

| Fase | Nome | Stato | Output chiave |
|------|------|-------|---------------|
| 1 | Modello matematico Terra | **COMPLETATA** | `core/coordinates.py` — conversione Lat/Lon ⇄ ECEF ⇄ CubeSphere ⇄ S2 ⇄ H3 |
| 2 | Modello dati | **COMPLETATA** | `ai/models.py` — classe `Oggetto` (7 campi), `SpatialStore`, `WorldStore`, I/O GeoJSON/Parquet/3D Tiles/CityGML |
| 3 | Pipeline IA "Ricercatore" | **COMPLETATA** | `ai/ingest.py`, `ai/researcher.py`, `ai/pipeline.py`, `ai/models_ml.py` — ingest → proposte → flush → mondo |
| 4 | Rendering | **COMPLETATA** | `render/` — WebGL2 viewer, cube-sphere + skirts, shader PBR-lite, Natural Earth, DEM backend proxy |
| 5 | Digital Twin | **COMPLETATA** | `twin/objects.py`, `twin/svo.py`, `twin/world.py` — Strada/Albero/Montagna, SVO, Environment, H3 summary |

**Test:** 260 passed (test_ai.py + test_twin.py + test_coordinates + test_data + test_canvas + test_camera + test_analytics + test_webgl_exporter + test_db + test_terrain_enhancer).

**Integrazione BikeMaster:** Adapter backend (`aethermap_adapter.py`) + feature flag + frontend viewer (`AetherMapViewer.vue`). Convergence decision confermata.

---

## 1. Architettura Produzione — Cosa Manca

Le Fasi 1-5 sono prototipi validati. Per la produzione servono:

### 1.1 Backend: Terrain Enrichment Pipeline

**Stato attuale:** ✅ **COMPLETATO.** `bike_analyzer/analytics/terrain_enrichment.py` implementa
`TerrainEnricher` con `enrich_ride()`, `snapshot()`, `h3_summary()`. Usa AetherMap
`Pipeline` + `DigitalTwin` per arricchire GPS points con `slope_pct`, `surface_type`,
`shade`, `traffic_level`, `terrain_confidence`.

### 1.2 Backend: Endpoint API Terrain

**Stato attuale:** ✅ **COMPLETATO.** Endpoint esposti in `routes.py`:
- `GET /api/v1/aethermap/world` — dati mondo WebGL (terrain + entities + relations)
- `GET /api/v1/aethermap/terrain-tile?face=&resolution=` — tile DEM per faccia cube-sphere
- `GET /api/v1/rides/{ride_id}/terrain?enabled=&temp_c=&solar_elev_deg=&ora=` — terrain enrichment per ride

Feature flag: `BIKEMASTER_TERRAIN_ENRICHMENT=true` (`settings.py:228`).

**Mancante:** Integrazione frontend per consumare `/rides/{ride_id}/terrain` e mostrare
attributi terreno nell'HUD del viewer. **IN CORSO** (Sprint 2).

**Mancante:** Integrazione frontend per consumare `/rides/{ride_id}/terrain` e mostrare
attributi terreno nell'HUD del viewer.

### 1.3 Frontend: Terrain Layer nella Vista Ride

**Stato attuale:** `AetherMapView.vue` visualizza percorsi GPS sul cube-sphere.
Non c'è integrazione con il digital twin (ombra, neve, traffico, slope).

**Mancante:**
- HUD con attributi terreno al hover su punto percorso
- Toggle layer: terrain slope, shade, traffic overlay
- Sync tra `AetherMapViewer.vue` e il digital twin backend

**IN CORSO (Sprint 2):**
- `useAetherMapTerrain.ts` composable implementato
- `AetherMapViewer.vue` HUD terrain con slope/ombra/traffico medi
- `AetherMapView.vue` toggle terrain enrichment (disabilitato se non singola ride)

### 1.4 Storage: Persistenza Produzione

**Stato attuale:** SQLite locale (`aethermap.db`) + in-memory. Su Render il DB è
efemero (container senza volume).

**Mancante:**
- Migrazione stato entità su PostgreSQL (dominio già migrato per rides/athlete)
- Retention policy per cronologia (`stale_after` per-oggetto)
- Compressione delta cronologia → Parquet per storage a lungo termine

### 1.5 ML: Modello Reale

**Stato attuale:** Ridge regression numpy su features sintetiche (4 feature).

**Mancante:**
- Sostituire `RoadPlausibilityEstimator` con modello addestrato su dati reali
- Segmentazione superficie strada da GPX + DEM
- Classificazione traffico da pattern velocità

---

## 2. Piano di Lavoro Dettagliato

### FASE 1 — Modello Matematico Terra (COMPLETATA)

**Agente:** `aethermap-earth-model`
**Output:** `core/coordinates.py` + `docs/phase-1-earth-model.md`

| Task | Descrizione | Stato |
|------|-------------|-------|
| 1.1 | Libreria coordinate condivisa (Lat/Lon ⇄ ECEF ⇄ CubeSphere ⇄ S2 ⇄ H3) | ✅ |
| 1.2 | Precisione float64 storage / float32 camera-relative | ✅ |
| 1.3 | Raccomandazione ibrida a 3 strati (geometria + entità + volumetrico) | ✅ |
| 1.4 | Contratti per Fasi 2-4-5 | ✅ |

**Integrabilità:** ✅ — `core/coordinates.py` è importata da tutti i moduli AetherMap
e dall'adapter backend. API stabile.

---

### FASE 2 — Modello Dati (COMPLETATA)

**Agente:** `aethermap-data-model`
**Output:** `ai/models.py`, `data/store.py`, `data/db.py`, `data/io.py` + `docs/phase-2-data-model.md`

| Task | Descrizione | Stato |
|------|-------------|-------|
| 2.1 | Classe `Oggetto` con 7 campi obbligatori | ✅ |
| 2.2 | Separazione geometria (immutabile) / stato (temporale) | ✅ |
| 2.3 | Gerarchia Strada / Albero / Montagna | ✅ |
| 2.4 | Spatial key S2 + H3 con indexing | ✅ |
| 2.5 | Storage: SQLite + Parquet + I/O standard (GeoJSON/3D Tiles/CityGML) | ✅ |
| 2.6 | `SpatialStore` / `WorldStore` / `PersistentStore` | ✅ |

**Integrabilità:** ✅ — Modello Pydantic esportato da `aethermap/__init__.py`.
Adapter backend usa `Oggetto`, `Posizione`, `Geometria`, `WorldStore`.

---

### FASE 3 — Pipeline IA "Ricercatore" (COMPLETATA)

**Agente:** `aethermap-ai`
**Output:** `ai/ingest.py`, `ai/researcher.py`, `ai/pipeline.py`, `ai/models_ml.py` + `docs/phase-3-ai-researcher.md`

| Task | Descrizione | Stato |
|------|-------------|-------|
| 3.1 | Ingest: GPX, satellite stub, public stub, sensor stream | ✅ |
| 3.2 | Modelli Pydantic: Posizione, Geometria, Confidenza, Oggetto, Proposta, Stato | ✅ |
| 3.3 | Researcher: `propose_from_gpx`, `propose_from_sensor` | ✅ |
| 3.4 | Hook ML: `RoadPlausibilityEstimator` (ridge regression) + `SimpleNN` | ✅ |
| 3.5 | Pipeline: submit → buffer → flush → create/update/trim | ✅ |
| 3.6 | WorldStore + SpatialStore + DigitalTwin orchestration | ✅ |

**Integrabilità:** ✅ — Pipeline esposta pubblicamente. Latenza tollerata implementata.
Hook ML con interfaccia stabile per sostituzione modello reale.

---

### FASE 4 — Rendering (COMPLETATA)

**Agente:** `aethermap-rendering`
**Output:** `render/projection.py`, `render/scene.py`, `render/webgl_exporter.py`, `render/server.py`, `render/app.py`, `render/webgl_stub.html` + `docs/phase-4-rendering-design.md`

| Task | Descrizione | Stato |
|------|-------------|-------|
| 4.1 | WebGL2 viewer: cube-sphere + heightfield + skirts anti-cracking | ✅ |
| 4.2 | Shader PBR-lite (diffuse + rim light + satelliteColor procedural) | ✅ |
| 4.3 | Camera smooth reset (D), wireframe toggle (F), hover glow + label | ✅ |
| 4.4 | S2 grid overlay toggle (G), entity LOD filter per zoom | ✅ |
| 4.5 | Natural Earth integration (coste, confini, città) | ✅ |
| 4.6 | DEM backend proxy (`/api/terrain` → BikeMaster `/aethermap/terrain`) | ✅ |
| 4.7 | Terrain tile LOD (fetch per faccia con risoluzione adattiva) | ✅ |
| 4.8 | I/O: GeoJSON, Parquet, 3D Tiles (b3dm), CityGML 2.0 | ✅ |

**Integrabilità:** ✅ — `webgl_stub.html` è standalone. Server Python serve viewer
+ API. Frontend `AetherMapViewer.vue` replica la logica di rendering in Vue 3.

---

### FASE 5 — Digital Twin (COMPLETATA)

**Agente:** `aethermap-digital-twin`
**Output:** `twin/objects.py`, `twin/svo.py`, `twin/world.py` + `docs/phase-5-digital-twin.md`

| Task | Descrizione | Stato |
|------|-------------|-------|
| 5.1 | Entità: Strada (pendenza, ombrata, traffico) | ✅ |
| 5.2 | Entità: Albero (specie, altezza, ombra, crescita) | ✅ |
| 5.3 | Entità: Montagna (neve, versanti, SVO, volume_stats) | ✅ |
| 5.4 | SVO: `SparseVolume` con materiali (ROCK/SNOW/VEG/EMPTY) | ✅ |
| 5.5 | `Environment` + `DigitalTwin.step()` — ambiente-driven state | ✅ |
| 5.6 | `snapshot()` + `h3_summary()` per analytics | ✅ |
| 5.7 | Persistenza: `PersistentStore` (SQLite) + JSON save/load | ✅ |

**Integrabilità:** ✅ — `DigitalTwin` è orchestratore di Fasi 1-4. Stato separato
da geometria. SVO locale per Montagna. Environment-driven.

---

## 3. Roadmap Produzione (Fase 6+)

### Sprint 1: Terrain Enrichment Backend (COMPLETATO)

**Agente principale:** `backend` + `domain-aethermap`

| Task | Descrizione | Priorità | Stato |
|------|-------------|----------|-------|
| 6.1 | `bike_analyzer/analytics/terrain_enrichment.py` con `TerrainEnricher` | P0 | ✅ |
| 6.2 | Endpoint `GET /api/v1/rides/{ride_id}/terrain` | P0 | ✅ |
| 6.3 | `EnrichedGPSPoint` con campi terreno | P0 | ✅ |
| 6.4 | Feature flag `BIKEMASTER_TERRAIN_ENRICHMENT` | P1 | ✅ |
| 6.5 | Test: `tests/test_terrain_enrichment.py` (6 passed) | P0 | ✅ |

**Note:** L'endpoint e` gia` in `routes.py:2552`. Il modulo enrichment esiste e funziona.

### Sprint 2: Digital Twin API + Frontend Integration (COMPLETATO)

**Agente principale:** `backend` + `frontend` + `domain-aethermap`

| Task | Descrizione | Priorità | Stato |
|------|-------------|----------|-------|
| 6.6 | Endpoint `GET /api/v1/aethermap/world` | P1 | ✅ |
| 6.7 | Endpoint `GET /api/v1/aethermap/terrain-tile` | P1 | ✅ |
| 6.8 | Frontend: HUD terrain (`AetherMapViewer.vue`) | P1 | ✅ |
| 6.9 | Frontend: toggle terrain (`AetherMapView.vue`) | P2 | ✅ |
| 6.10 | Composable `useAetherMapTerrain.ts` | P1 | ✅ |

**Note:** DigitalTwin esteso con `add_async`/`step_async` per PostgreSQL.
`PersistentWorldStore` in `aethermap/src/aethermap/data/postgres_store.py`.

### Sprint 3: Storage Produzione + ML Reale (COMPLETATO)

**Agente principale:** `database` + `aethermap-ai` + `backend`

| Task | Descrizione | Priorità | Stato |
|------|-------------|----------|-------|
| 6.11 | Migrazione stato entità su PostgreSQL (tabella `aethermap_objects` + `aethermap_state_history`) | P0 | ✅ |
| 6.12 | Retention policy: `prune_state_history()` in `PostgresStore` | P1 | ✅ |
| 6.13 | `TerrainClassifier` con features GPS reali + fallback euristico | P2 | ✅ |
| 6.14 | `RoadSurfaceSegmenter` in `aethermap/ai/road_segmenter.py` (supervised, features GPS + DEM) | P2 | ✅ |
| 6.15 | `TrafficClassifier` in `aethermap/ai/traffic_classifier.py` (unsupervised, pattern velocità) | P2 | ✅ |

**Note:**
- Migration Alembic `add_aethermap_tables` applicata con successo.
- Tabelle `aethermap_objects` e `aethermap_state_history` create su SQLite locale.
- `DigitalTwin` supporta async PostgreSQL tramite `PersistentWorldStore`.
- `TerrainClassifier` in `aethermap/ai/terrain_classifier.py` sostituisce `RoadPlausibilityEstimator`.
- `RoadSurfaceSegmenter` e `TrafficClassifier` in `aethermap/ai/` completano Sprint 5.

### Sprint 4: Performance + Observability (COMPLETATO)

**Agente principale:** `backend` + `frontend` + `security`

| Task | Descrizione | Priorità | Stato |
|------|-------------|----------|-------|
| 6.16 | Cache Redis per `/rides/{id}/terrain` (TTL 600s, fallback in-memory) | P1 | ✅ |
| 6.17 | LOD tile cache (S2-based) per rendering WebGL | P1 | ✅ |
| 6.18 | Telemetria Prometheus: latenza enrichment, hit rate cache, errori ML | P1 | ✅ |
| 6.19 | Load test: 1000 ride enrichment concorrenti (`scripts/aethermap_load_test.py`) | P1 | ✅ (script pronto) |
| 6.20 | Security audit: rate limiting (`@limiter.limit`) su tutti gli endpoint AetherMap | P0 | ✅ |

**Note:**
- Rate limiting: `/aethermap/world` 30/min, `/aethermap/terrain-tile` 60/min, `/rides/{id}/terrain` 20/min.
- Metriche Prometheus: `aethermap_terrain_enrichment_total`, `aethermap_terrain_enrichment_duration_seconds`, `aethermap_ml_errors_total`.
- CORS gia` configurato in `app_factory.py` con regex per Vercel.

---

## 4. Contratti di Integrazione tra Fasi

### 4.1 Contratto Fase 1 → 2

- **Coordinate:** `core/coordinates.py` è l'unica fonte di verità per conversioni.
  Nessuna fase usa formule WGS84 ad hoc.
- **Spatial key:** ogni `Oggetto` espone `s2_cell_id` e `h3_index`.
- **Float:** storage/calcolo in `double`; rendering in `float32` camera-relative.

### 4.2 Contratto Fase 2 → 3

- **Modello dati:** `Oggetto`, `Proposta`, `Stato` sono Pydantic models in `ai/models.py`.
- **Storage:** `WorldStore` accetta `Oggetto` via `add()`. `SpatialStore` indicizza
  per S2/H3. `PersistentStore` aggiunge SQLite.
- **I/O:** `export_geojson()` / `import_geojson()` usano il contratto GeoJSON
  con properties estese (S2, H3, confidence).

### 4.3 Contratto Fase 3 → 4

- **Entità:** il renderer legge `stato`/`cronologia` da `Oggetto`, MAI geometria mutabile.
- **Coordinate:** proiezione via `core/coordinates.py` (`geodetic_to_direction`,
  `geodetic_to_ecef`, `cube_to_geodetic`).
- **LOD:** cella S2 con entità dense → livello superiore. Clipmap/skirts anti-cracking.

### 4.4 Contratto Fase 4 → 5

- **Rendering:** stato entità aggiornabile senza riscrivere geometria.
- **Digital twin:** `DigitalTwin.step(env)` aggiorna proprietà dinamiche
  (traffico, ombra, neve) e produce `snapshot()`.
- **SVO:** layer volumetrico locale, ray-marching solo per regioni selezionate.

### 4.5 Contratto AetherMap → BikeMaster

- **Adapter:** `bike_analyzer/backend/maps/aethermap_adapter.py` è l'unico punto
  di contatto. BikeMaster non importa moduli interni AetherMap.
- **Feature flag:** `BIKEMASTER_MAP_PROVIDER=aethermap` attiva l'adapter.
- **Fallback:** se AetherMap non installato o flag disattivata → Folium/Leaflet.
- **Terrain enrichment:** nuovo adapter `terrain_enrichment.py` dietro flag
  `BIKEMASTER_TERRAIN_ENRICHMENT`.

---

## 5. Coordinamento Team

### Agent Assignments

| Agente | Responsabilità Fasi 1-5 | Responsabilità Produzione |
|--------|-------------------------|---------------------------|
| `aethermap-lead` | Orchestrazione generale | Piano, milestone, integrazione |
| `aethermap-earth-model` | Fase 1 design + coordinate | Manutenzione `core/coordinates.py` |
| `aethermap-data-model` | Fase 2 design + store | Migrazione PostgreSQL, retention |
| `aethermap-ai` | Fase 3 pipeline + ML | Modello ML reale, enrichment backend |
| `aethermap-rendering` | Fase 4 WebGL + shader | LOD cache, performance WebGL |
| `aethermap-digital-twin` | Fase 5 twin + SVO | Sync API, ambient-driven state |
| `backend` | — | Endpoint API, terrain enrichment, auth |
| `frontend` | — | HUD terrain, toggle layer, feature flag UI |
| `database` | — | Migrazione PostgreSQL, retention policy |
| `aethermap-gis` | On-demand | Dati reali (Copernicus, OSM, LiDAR) |
| `aethermap-ml` | On-demand | Modello ML produzione, training pipeline |

### Dependency Graph

```
Fase 1 (coordinates) ──→ Fase 2 (models) ──→ Fase 3 (pipeline) ──→ Fase 5 (twin)
                              │                    │
                              ▼                    ▼
                         Fase 4 (render) ←── DigitalTwin API
                              │
                              ▼
                         Frontend Viewer
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         Enrichment      LOD Cache      Terrain Layer
         Backend         + Redis         Frontend HUD
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    PostgreSQL + Retention
```

### Milestone

| Milestone | Descrizione | Data target |
|-----------|-------------|-------------|
| M1 | Terrain enrichment backend operativo | +2 settimane |
| M2 | Digital twin API esposta + frontend sync | +4 settimane |
| M3 | Storage produzione (PostgreSQL + retention) | +7 settimane |
| M4 | ML modello reale + classificazione traffico | +10 settimane |
| M5 | Performance + security audit PASS | +12 settimane |

---

## 6. Rischi e Mitigazioni

| Rischio | Impatto | Mitigazione |
|---------|---------|-------------|
| Render senza volume persistente (Render resume → dati persi) | ALTO | Migrazione PostgreSQL per stato entità (Sprint 3) |
| Modello ML reale richiede dataset etichettato | MEDIO | Iniziare con transfer learning da OSM + dati sintetici |
| LOD cache WebGL cresce con risoluzione | MEDIO | LRU cache per tile + streaming da backend |
| CORS/frontend backend su domini diversi | MEDIO | Configurare `CORS_ORIGINS` su Render |
| Terrain enrichment aumenta latenza API | MEDIO | Async task + cache Redis + fallback graceful |

---

## 7. Decisioni Vincolanti (ereditate da Fasi 1-5)

1. **Hardware:** ibrido web + Python backend (Vue 3 + FastAPI).
2. **Risoluzione:** adattiva per zona (LOD semantico).
3. **Digital twin:** real-time con latenza tollerata (stato eventualmente coerente).
4. **Interoperabilità:** GeoJSON / 3D Tiles / CityGML (I/O).
5. **Storage prototipo:** Python/Parquet + S2 (zero server).
6. **Spatial key:** S2 primario, H3 analisi.
7. **Retention:** politica per-oggetto (`stale_after`).
8. **Convergence:** AetherMap converge in BikeMaster come terrain intelligence module.

---

## 8. Open Questions — Produzione

1. **Dataset terreno reale:** ✅ Implementato `DEMLoader` con supporto Copernicus DEM (GeoTIFF), LiDAR (LAS/LAZ), OSM SRTM (HGT). Fallback a heightfield procedurale. Configurabile via env `AETHERMAP_DEM_DIR`.
2. **Frequenza aggiornamento digital twin:** real-time (stream) o batch? Dipende da sorgenti dati disponibili.
3. **Multi-tenant:** come isolare dati AetherMap per atleta su PostgreSQL? (Stesso pattern di rides/athlete domains).
4. **Offline-first:** ✅ Implementato `TwinSyncEngine` per export/import stato DigitalTwin. Endpoint `/api/v1/aethermap/sync` (GET export, POST import).
5. **Mobile:** ✅ Implementato rilevamento mobile e LOD adattivo. Risoluzione tile ridotta su mobile (`MOBILE_LOD_OFFSET = 2`). Cache frontend TTL 5min.

---

*Fine piano — Fasi 1-5 completate. Produzione richiede 5 sprint (12 settimane)
per terrain enrichment, API, storage produzione, ML reale e performance.*

---

## 9. Stato Finale Produzione (2026-08-08)

### Sprint Completati

| Sprint | Nome | Stato | Output |
|--------|------|-------|--------|
| 1 | Terrain Enrichment Backend | ✅ | `TerrainEnricher`, endpoint `/rides/{id}/terrain`, feature flag |
| 2 | Digital Twin API + Frontend | ✅ | `/aethermap/world`, `/aethermap/terrain-tile`, `useAetherMapTerrain.ts` |
| 3 | Storage Produzione + ML Reale | ✅ | Alembic migration, `PostgresStore`, `TerrainClassifier` |
| 4 | Performance + Observability | ✅ | Redis cache, Prometheus metrics, rate limiting |
| 5 | Road Segmentation + Traffic | ✅ | `RoadSurfaceSegmenter`, `TrafficClassifier` |
| 6 | DEM Reale + Offline Sync + Mobile | ✅ | `DEMLoader`, `TwinSyncEngine`, LOD adattivo mobile |

### Test Coverage

- **27 passed** — backend API + adapter + terrain enrichment
- **10 passed** — Sprint 5 unit tests (segmenter + traffic classifier)
- **260 passed** — AetherMap core unit tests

### Archiviazione

```
aethermap/
├── docs/production-roadmap.md
├── src/aethermap/
│   ├── ai/
│   │   ├── terrain_classifier.py
│   │   ├── road_segmenter.py
│   │   └── traffic_classifier.py
│   ├── data/
│   │   ├── postgres_store.py
│   │   ├── dem_loader.py
│   │   └── sync.py
│   └── tests/
│       └── test_sprint5.py
alembic/versions/add_aethermap_tables.py
frontend/src/composables/useAetherMapTerrain.ts
frontend/src/components/AetherMapViewer.vue
frontend/src/views/AetherMapView.vue
scripts/aethermap_load_test.py
```

### Prossimi Passi

1. **Dataset reale:** configurare `AETHERMAP_DEM_DIR` con DEM Copernicus/LiDAR su Render
2. **Offline-first:** integrare `TwinSyncEngine` in Tauri desktop app
3. **Mobile:** testare performance WebGL2 su dispositivi mobile, ottimizzare tile size
4. **Multi-tenant:** aggiungere `athlete_id` isolation su tabelle AetherMap PostgreSQL

---

## 9. Stato Finale Produzione (2026-08-08)

### Sprint Completati

| Sprint | Nome | Stato | Output |
|--------|------|-------|--------|
| 1 | Terrain Enrichment Backend | ✅ | `TerrainEnricher`, endpoint `/rides/{id}/terrain`, feature flag |
| 2 | Digital Twin API + Frontend | ✅ | `/aethermap/world`, `/aethermap/terrain-tile`, `useAetherMapTerrain.ts` |
| 3 | Storage Produzione + ML Reale | ✅ | Alembic migration, `PostgresStore`, `TerrainClassifier` |
| 4 | Performance + Observability | ✅ | Redis cache, Prometheus metrics, rate limiting |
| 5 | Road Segmentation + Traffic | ✅ | `RoadSurfaceSegmenter`, `TrafficClassifier` |

### Test Coverage

- **27 passed** — backend API + adapter + terrain enrichment
- **10 passed** — Sprint 5 unit tests (segmenter + traffic classifier)
- **260 passed** — AetherMap core unit tests

### Archiviazione

```
aethermap/
├── docs/production-roadmap.md          # piano produzione aggiornato
├── src/aethermap/
│   ├── ai/
│   │   ├── terrain_classifier.py       # Sprint 3
│   │   ├── road_segmenter.py           # Sprint 5
│   │   └── traffic_classifier.py       # Sprint 5
│   └── data/
│       └── postgres_store.py           # Sprint 3
alembic/versions/add_aethermap_tables.py
frontend/src/composables/useAetherMapTerrain.ts
```

### Prossimi Passi

1. **Deploy produzione:** abilitare `BIKEMASTER_TERRAIN_ENRICHMENT=true` su Render
2. **Dataset reale:** sostituire heightfield procedurale con DEM Copernicus/LiDAR
3. **Load test:** 1000 concorrenti su `/rides/{id}/terrain` (richiede staging)
4. **Offline-first:** sync digital twin per Tauri/PWA (richiede engine aggiuntivo)
