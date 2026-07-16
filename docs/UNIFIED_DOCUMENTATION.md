# BikeMaster — Documentazione Unica del Progetto

> **Scopo di questo file:** unificare in un solo documento l'intera conoscenza del
> repository (product vision, architettura, logica di calcolo, storage locale,
> sottosistemi, R&D AetherMap) **senza cancellare né riscrivere i documenti
> sorgente**. Ogni sezione rimanda ai file originali per il dettaglio.
>
> **Data consolidamento:** 2026-07-16
> **Fonti primarie:** `AGENTS.md`, `docs/README.md`, `docs/MASTER.md`,
> `docs/PRODUCT_LOGIC.md`, `docs/ARCHITECTURE.md`, `docs/BM2_*.md`,
> `docs/local-data-storage.md`, `docs/reference/*`, `PROJECT_STATUS.md`,
> `ROADMAP.md`, `aethermap/README.md`, `docs/agent/*`.
>
> **Stato prodotto (verificato 2026-07-13):** Production Ready. Backend
> 108 file test / 1674 test · Frontend 47 file / 318 test Vitest · 138 endpoint REST.

---

## 0. Indice rapido delle fonti (non cancellate)

| Area | File originale (intatto) |
|---|---|
| Visione prodotto | `docs/PRODUCT_LOGIC.md` |
| Architettura madre | `docs/ARCHITECTURE.md`, `docs/MASTER.md` §4 |
| Riferimento completo | `docs/reference/README.md` + moduli (`architecture`, `api-reference`, `database-schema`, `domain-models`, `configuration`, `engines-and-analytics`, `frontend`) |
| BM2 algoritmi | `docs/BM2_ALGORITHMS.md`, `docs/BM2_ENGINE_ARCHITECTURE.md`, `docs/BM2_INTEGRATION_GUIDE.md`, `docs/BM2_TESTING_STRATEGY.md` |
| BM2 dati | `docs/bm2/data-contracts.md`, `docs/bm2/database-schema.md`, `docs/bm2/variables.md` |
| Storage locale | `docs/local-data-storage.md` |
| Phone tracking | `docs/PHONE_TRACKING.md`, `docs/PHONE_TRACKING_TESTING.md` |
| Deploy / config | `docs/deployment.md`, `docs/configuration.md`, `docs/deployment-plan.md` |
| Stato / roadmap | `PROJECT_STATUS.md`, `ROADMAP.md`, `DELUXE_ROADMAP.md` |
| AetherMap (R&D) | `aethermap/README.md`, `aethermap/docs/phase-*.md`, `docs/agent/aethermap.md` |
| Istruzioni agent | `docs/agent/README.md` + `docs/agent/*.md` |

---

## 1. Cos'è BikeMaster (visione strategica)

**BikeMaster** è un sistema di *performance intelligence* per ciclisti basato su GPS.
Importa tracciati da **GPX/FIT** o servizi esterni (Strava, Garmin, Wahoo, Google Fit),
analizza metriche, stima calorie, calcola un *fatigue score*, confronta con percentile
di benchmark, fornisce un **AI Coach** (Groq + RAG) e visualizza percorsi su mappe
interattive. Include inoltre **BikeMaster 2.0 (BM2)**, motore di simulazione "what-if",
e **AetherMap**, progetto R&D cartografico separato.

### 1.1 Posizionamento — la scelta strategica fondamentale
> **Non** compete con Strava/Garmin/TrainingPeaks. È uno **strato di intelligenza
> sopra gli strumenti che il ciclista già usa**.

La motivazione programmatica di questa scelta è decisiva:
- **Elimina la barriera di onboarding** → l'utente non parte da zero, importa i dati esistenti.
- **Concentra il valore unico** → non si ricostruisce ciò che esiste, si aggiunge *consiglio*.
- Il ciclo distintivo è: `dati → comprensione → decisione → miglioramento`.

### 1.2 I Quattro Pilastri (roadmap)
1. **Core** — utile con una sola uscita (import, storico, metriche, dashboard, report).
2. **Intelligent Coach** — profilo dinamico, consigli adattivi, piano di allenamento.
3. **Live Assistant** — notifiche vocali, alert in corsa, stato di allenamento real-time.
4. **Ecosystem** — solo dopo 1–3 solidi: smartwatch, community, eventi, sicurezza avanzata.

### 1.3 Il problema centrale (cuore logico del prodotto)
> Non solo *"Quanto hai fatto?"* ma *"Quanto ti è costato?"*.

Due atleti con dati esterni identici possono rispondere in modo opposto. Il sistema
impara la **relazione personale stimolo→risposta** (carico→recupero), non si limita a
memorizzare eventi. È la differenza fra un *database di attività* e un **modello di atleta**.

---

## 2. Architettura software (Clean Architecture)

Principi vincolanti (`docs/ARCHITECTURE.md`):
1. Ogni modulo ha dipendenze **esplicite** (nessun accoppiamento nascosto).
2. Il **dominio non dipende dall'infrastruttura** (DB, provider, mappe).
3. La logica di calcolo è **pura** (input→output, testabile), separata dall'I/O.
4. I dati grezzi entrano come `SessionData` e diventano `Activity` + `FusionRecord`.
5. L'**AI Coach consuma solo `FusionRecord`** (contesto già fuso), mai sorgenti grezze.

```
Presentation    API (FastAPI) · Frontend Vue · Android/iOS (Capacitor) · Tauri 2 (desktop)
      │
Application     Use cases: StartSession, PromoteSession, ImportActivity,
                AnalyzeActivity, SyncHealth, CoachAdvise, PlanTraining
      │
Domain          Entities + UnifiedMetricsEngine (logica di calcolo pura)
      │
Infrastructure  Repositories · Ingestion (Strava/Garmin/Fit/GPX) ·
                Tracking · Maps · Weather · Traffic · VectorDB
```

> **Nota architetturale (2026-07-15):** piattaforma primaria = **Tauri 2 desktop**
> (Rust + WebView, `.exe`/`.dmg`/`.AppImage`). Il backend FastAPI gira embedded in
> `localhost`. SQLite è lo store primario **per ogni utente**; PostgreSQL è opzionale
> (solo cloud, per sync/community). L'utente può attivare la modalità **"Mai"** (mai
> sync) e usare l'app 100% offline. PWA ancora supportata per utenti web-only.

### 2.1 Layer di dominio (`bike_analyzer/core/`)
Entità pure e calcolo: `models.py` (`GPSPoint`, `Segment`, `Pause`, `Ride`,
`AthleteProfile`, `CalendarEvent`, `RouteStatistics`), `session.py` (`SessionData`),
`pipeline.py` (`AnalysisPipeline`), `engine.py` (`AnalysisEngine` + `FitnessStateVector`),
`fitness_state.py`, `validators.py`, `calculators/` (funzioni pure: calorie, potenza,
fatica, performance, stress).

### 2.2 Layer analytics (`bike_analyzer/backend/analytics/`)
Struttura a tre livelli (Clean Architecture applicata):
- **`calculators/`** — funzioni pure, testabili in isolamento.
- **`services/`** — orchestrazione use-case (`ride_analysis_service`, `fitness_state_service`, `context_builder`).
- **`repositories/`** — astrazione accesso dati (ride, athlete, fitness state, training stress).

### 2.3 Pattern chiave
- **Calculators puri**: zero DB/API/side-effect.
- **Domain events**: pub/sub (`RideCreated`, `AthleteUpdated`, `BadgeEarned`, `TrainingGenerated`).
- **Dual-mode DB**: gli adapter repository gestiscono sia SQLite che PostgreSQL.
- **RAG boundary**: l'AI Coach non vede dati grezzi, solo stati interpretati dal Knowledge Layer.

---

## 3. Logica di calcolo — scelte programmatiche rilevanti ⭐

Questa sezione evidenzia le **decisioni logiche** che definiscono il comportamento
dell'app. Ogni formula è tratta dai documenti tecnici verificati.

### 3.1 Kernel fisico condiviso (`core/physics/`)
> **Regola ferrea:** nessun algoritmo duplica la fisica. Tutti importano dal kernel
> `core.physics` (dal 2026-07-12 BM2 delega qui, eliminando il forward model duplicato).

| Funzione | Usata da | File |
|---|---|---|
| `cycling_forces()` | EnergyModel, PowerModel | `core/physics/power.py` (via `__init__`) |
| `instantaneous_power()` | PowerModel | `core/physics/power.py` |
| `required_speed_for_power()` | PowerModel | `core/physics/validation.py`, `power.py` |
| costanti | tutto | `core/physics/constants.py` |

### 3.2 Calorie — modello fisico + fallback MET
Somma contributi con correzione per efficienza meccanica (`CALORIE_EFFICIENCY_FACTOR`, default ~25%):
- **Resistenza rotolamento**: `Crr · m · g · cos θ`
- **Resistenza aerodinamica**: `½ · ρ · CdA · v²`
- **Gravità**: `m · g · sin θ`
- **Fallback**: tabelle **MET** quando mancano dati di potenza/pendenza. Benchmark di riferimento: ~30 kcal/km.

### 3.3 Potenza (Coggan) — `power_model.py`
- **NP** (Normalized Power): media mobile 30s, elevata^4, radice 4ª.
- **IF** = NP / FTP · **VI** = NP / avg power · **EF** = NP / avg HR.
- **TSS** = `IF² · durata_ore · 100` · **FTP stimato** = test 20min × 0.95.
- **Aerobic decoupling**: scompenso significativo se > 5%.
- **Zone**: modello 7-zone Coggan; **Power Profile** best effort 5s/1min/5min/20min.

### 3.4 Carico di allenamento — EWMA
- **ATL** (acuto) = EWMA 7 giorni · **CTL** (cronico) = EWMA 42 giorni.
- **TSB** (forma) = `CTL − ATL` · **Monotony / Strain** per rischio sovraccarico.

### 3.5 Fatigue Score (0–10) — scelta di pesatura esplicita ⭐
```
score = min(10, (durata·0.30 + intensità·0.30 + velocità·0.20
                 + dislivello·0.10 + peso·0.10) · 3)
```
**Logica:** durata e intensità dominano (30% ciascuna); peso minimo (10%) perché
rumoroso. Recupero stimato a fasce: 8 / 16 / 24 / 48 h. Recovery hours estimator
in `calculators/fatigue.py`.

### 3.6 Performance Index (normalizzato per esperienza) ⭐
```
indice = clamp( v_media_kmh / v_riferimento(experience) · 100 , 0, 120 )
```
Velocità di riferimento **esplicita per livello** (scelta logica fondante):
Beginner 18 · Intermediate 24 · Advanced 30 · Elite 36 km/h.
Questo rende il punteggio *comparabile tra atleti diversi* anziché assoluto.

### 3.7 Route Difficulty (0–100) multi-fattore ⭐
```
difficoltà = clamp( 100 · (0.3·norm(distanza) + 0.3·norm(dislivello)
                 + 0.25·norm(pendenza) + 0.15·rugosità) / capacità , 0, 100 )
```
- **Roughness**: asphalt 1.0 · gravel 1.25 · dirt 1.5 · trail 1.8.
- **Capacità atleta** (amplifica/diminuische): Beginner ×1.3 · Intermediate ×1.0 · Advanced ×0.8 · Elite ×0.65.
- Categorie: <20 Facile · <45 Moderato · <70 Impegnativo · ≥70 Estremo.

### 3.8 Athlete State — `FitnessStateVector`
Snapshot fisiologico (CTL/ATL/TSB) combinato con recupero e raccomandazioni. Il
sistema **non guarda la singola uscita**: calcola lo stato presente da
`passato + distribuzione temporale + recupero + risposta personale`.

### 3.9 Load Management — logica di ridistribuzione ⭐
Obiettivo settimanale visto come target distribuito. Se una uscita viene ridotta:
```
km_rimanenti ÷ uscite_disponibili = nuovo carico consigliato
```
Sopra questo livello matematico si applicano fatica, recupero e risposta individuale.

### 3.10 Problem-decomposition (approccio AI) ⭐
Problemi complessi (es. "ho saltato un allenamento, che faccio?") sono scomposti in
sottoprobлемi risolti da **regole matematiche + algoritmi di ottimizzazione + AI che
spiega/sceglie/comunica**. L'AI **non inventa** la soluzione: sceglie fra strategie
predefinite usando i dati (Soluzione A: recupera volume; B: mantieni piano; C: cambia
tipo). Costruisce più combinazioni adattandosi a ciò che l'utente può realmente fare.

### 3.11 Proactive Assistant — soglia segnale/rumore ⭐
L'assistente interviene **solo** quando il valore del messaggio supera la soglia di
disturbo. Non comunica statistiche minori o info già note; comunica rischio,
recupero insufficiente, cambi cambio piano, problemi in corsa.

---

## 4. BikeMaster 2.0 (BM2) — Simulation Engine

Sottosistema **parallelo ma cablato** via `bm2_routes.py` montato in `app_factory.py`.
Filosofia type-safe: `Quantity` + `UnitRegistry` (analisi dimensionale); algoritmi puri
che restituiscono `ModelResult` (formula + input usati + `precision` + `confidence`).

### 4.1 I 9 algoritmi (`ALL_ALGORITHMS` → `MODEL_REGISTRY`)
Tutti ereditano da `Algorithm` (`bm2/algorithms/base.py`) e rispettano il template
method `run(ctx, extra) → ModelResult`. **Vietato** dentro `_compute`: DB, API, globali.

| Algoritmo | Unità | Formula chiave | Confidence base |
|---|---|---|---|
| MovementModel | m/s | `v=durata/distanza`, `a=d(v)/d(t)` | 0.95 (≥2 pt) |
| EnergyModel | kcal | `P=(Crr·m·g + m·g·sinθ + ½ρ·CdA·v²)·v; kcal=P·t/(η·4184)` | 0.85 (dislivello), 0.70 |
| PowerModel | W | `P=(Crr·m·g + m·g·slope + ½ρ·CdA·v²)·v/η`; `v_ftp` risolto numericamente | 0.95 (power meter), 0.50–0.75 (FTP stimato) |
| PerformanceModel | score | `clamp(v_kmh/v_ref·100, 0,120)` | 0.70 (0.85 Advanced/Elite) |
| FatigueModel | 0–10 | v. §3.5 | 0.75 (0.85 con HR max) |
| RecoveryModel | 0–100 | `clamp(100 − fatica·6 − sonno_carenza·4 + hrv_bonus, 0,100)` | 0.70 (0.40 senza sonno/HRV) |
| RouteDifficultyModel | 0–100 | v. §3.7 | — |
| NutritionModel | g | `carb=intensità·60·ore; acqua=0.6·ore; proteine=0.3·kg` | 0.70 |
| TrainingLoadModel | score | `TSS=(t·NP·IF)/(FTP·3600)·100; CTL=EMA42; ATL=EMA7; TSB=CTL−ATL` | 0.80 (≥7gg), 0.60 (1–7gg), 0.30 |

### 4.2 Orchestration & Simulation
- `Orchestrator` (`orchestrator.py`): esegue algoritmi multipli su `AnalysisContext`.
- `SimulationEngine` (`simulation.py`): scenari what-if, preset, **analisi di sensibilità**,
  `parse_override_from_text` (estrazione override da linguaggio naturale).
- `AIOrchestrator` (`agents.py`): agenti sorgente dati (`GPSAgent`, `AthleteAgent`,
  `EnvironmentAgent`, `SensorAgent`, `StravaAgent`, `GarminAgent`) + RAG su `knowledge_base/`.
- Validazione fisica: `core/physics/validation.py` + `POST /api/v1/bm2/validate` (MAE/RMSE/bias/R²).

### 4.3 Pipeline Engine (BM2_ENGINE_ARCHITECTURE)
Pipeline a **Engine specializzati**, non REST diretti. Dependency direction rigorosa:
un Engine non legge output "a monte". Il **Data Layer è un outbox condiviso**, non un
canale di comunicazione tra Engine.

```
RawGPSPoint → Measurement → NormalizedMovementPoint → Analysis → SessionSummary
                                            └→ Territory → TerritorySegment
                                                            ↓
                                              Knowledge Layer → AI Coach
```
Error handling: ogni Engine degrada senza lanciare eccezioni non gestite (es. Territory
fallisce → prosegue senza segmenti; Knowledge fallisce → AI Coach risponde "dati non
disponibili", **non inventa**). Versionamento contratti JSON `NomeContratto.v{MAJOR}`.

### 4.4 Nuovi moduli (2026-07-16, non ancora documentati altrove)
- `bike_analyzer/backend/analytics/load_manager/` — `calculators.py`, `chronic_load.py`,
  `config.py`, `models.py`, `training_stress_calculator.py`: nuova astrazione di
  carico acuto/cronico (EWMA configurable) separata dal `training_load.py` legacy.
- `bike_analyzer/backend/analytics/adaptation_rules.py` — regole di **adattamento
  dinamico** (skip ride → ridistribuzione; ride lunga → riduzione; recupero insufficiente
  → deload; miglioramento → incremento graduale). Implementa la logica di §3.9/§1.3.

---

## 5. AI Coach & Knowledge Base

- **LLM**: Groq (`GROQ_API_KEY`, `GROQ_MODEL` default `llama-3.3-70b-versatile`).
- **RAG**: embeddings locali `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dim) con
  fallback TF-IDF/BM25; store `db/vector_db.py` o PGVector (`knowledge_chunks.embedding`).
- **BM25 engine** in `knowledge_base.py`: `k1=1.5`, `b=0.75`, LRU cache su mtime dir,
  chunking max 1200 char / overlap 200.
- **Principio**: l'AI Coach legge **solo** stati interpretati dal Knowledge Layer.
- **Persistenza chat**: `chat_history` con retention `AI_COACH_CHAT_RETENTION_DAYS` (90).
- Output in **italiano** per default.

---

## 6. Storage locale & architettura local-first ⭐

Riferimento centrale: `docs/local-data-storage.md`. **Il device è la sorgente di verità.**

### 6.1 Livelli di storage sul dispositivo
| Livello | Dove | Contenuto |
|---|---|---|
| Local Storage | `localStorage` (web/WebView) | `bikemaster_token`, `bikemaster_user`, `bikemaster_refresh_token`, flag OAuth |
| In-memory | Pinia `trackingStore` | stato live tracking (`routePoints`, metriche), volatile |
| GPX locale | file/blob | uscita salvata prima dell'upload (offline-safe) |
| Backend embedded | `localhost` (Tauri) | FastAPI/Axum + SQLite file locale (dati primari) |
| IndexedDB | `bikemaster-local` | cache attività `rides` + `meta` (offline-first) |
| Native | Android SharedPreferences / file; iOS plugin Swift | sessione, GPX |

### 6.2 Scelte logiche di rilievo
- **Ripristino sessione**: `router.beforeEach` sincronizza Pinia da `localStorage` prima
  di valutare l'auth → sessione ripristinata al reload. Su `401` → `clearAuth()` + toast.
- **Offline-first**: uscite GPS mai perse per mancanza di rete. GPX scritto localmente,
  poi caricato. Se sync cloud attiva e rete assente → **coda locale**, reinvio automatico.
- **IndexedDB resiliente**: `localRideCache.ts` degrada a no-op se `indexedDB` assente
  (SSR/test); `useRides.fetchSummary()` cade sul fallback cache → vuoto senza rompersi.
- **Sicurezza**: JWT in `localStorage` (non HttpOnly) → esposti a XSS (da monitorare;
  opzione futura: cookie HttpOnly + refresh via `security.py`). Dati GPS grezzi cancellati
  al logout/disinstallazione (GDPR diritto all'oblio).

---

## 7. Frontend (Vue 3 + Vite + TypeScript)

- Composition API `<script setup>`, TypeScript `strict`, Pinia, Vue Router 4 (auth guards),
  Chart.js, Leaflet (+ heatmap), PWA (`vite-plugin-pwa` + `sw.js`), Capacitor 5 (Android/iOS),
  Vitest (unit) + Playwright (E2E).
- **Stores**: `auth.ts` (JWT/sessione), `ui.ts` (tema/lingua), `trackingStore.ts` (GPS live).
- **Composables**: `useRides`, `useToast`, `usePWA`, `useI18n`, `useChart`.
- **Native**: Android `BikeTrackingService.kt` (foreground service Kotlin) + plugin Capacitor;
  iOS `BikeTrackingPlugin.swift`.
- **PWA**: install prompt + service worker (navigate fix), offline support.
- 20+ componenti (Dashboard, Rides, Tracking, Import, Athlete, Coach, Knowledge, Heatmap,
  Badges, Calendar, GranfondoPlanner, Admin, Login, RideDetail, SpeedMap, Weather, ecc.).

---

## 8. Sicurezza, monitoring & deploy

### 8.1 Security
- JWT HS256 (python-jose) + bcrypt; **key rotation** (`SECRET_KEY` + `SECRET_KEY_PREVIOUS`).
- Rate limiting slowapi per-IP + proxy-aware (`X-Forwarded-For`).
- Header: CSP, HSTS, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy.
- CORS configurable, wildcard vietato in produzione.
- Audit log JSONL (`audit_log.py`) + `/admin/audit-logs`.
- Docker hardened: multi-stage, non-root, read-only fs, no-new-privileges, healthcheck.

### 8.2 Observability
Sentry (opzionale), Prometheus (`/metrics`), Grafana, OpenTelemetry/Zipkin (tracing gRPC OTLP,
saltato in dev).

### 8.3 Deploy
Docker Compose, Render (`render.yaml`), Fly.io, Railway, Vercel, Kubernetes (Helm in `docker/helm`),
Azure (`azure.yaml`). CI GitHub Actions: test → lint → security (Trivy) → build.

### 8.4 Configurazione (variabili chiave)
`DATABASE_URL` (sqlite default), `DATABASE_URL_ASYNC`, `SECRET_KEY*`, `ENVIRONMENT`,
`CORS_ORIGINS`, `GROQ_API_KEY`, `REDIS_URL`, `SENTRY_DSN`, OAuth client/secret
(Strava/Garmin/Google Fit/Google Maps), `WEATHER_API_KEY`.
Tutta la config passa da `backend/settings.py` (`get_settings()`), mai da `config.py` legacy.

---

## 9. AetherMap (progetto R&D separato) ⭐

`aethermap/` è **indipendente** da BikeMaster: motore cartografico "dal nulla" (cube-sphere
+ S2/H3, data model "database del mondo", pipeline IA "ricercatore", rendering WebGL, digital
twin). Condivide **solo lo stack** (Vue + FastAPI) ma **non è importato** dal backend.

- **Fasi**: 1 (earth model) → 2 (data model) → {3 IA, 4 rendering} → 5 (digital twin).
- **Decisioni vincolanti**: hardware web+Python; risoluzione adattiva per zona (LOD semantico);
  digital twin real-time con latenza tollerata (stato eventualmente coerente); interoperabilità
  GeoJSON/3D Tiles/CityGML; storage Python/Parquet + S2; **S2 primario** (geometria/LOD),
  **H3** per analisi; retention per-oggetto (`stale_after`).
- **Codice**: `aethermap/src/aethermap/` (`core/coordinates.py`, `ai/`, `render/`, `twin/`).
- **Demo**: `cd aethermap/src && python -m aethermap.ai.demo|.render.demo|.twin.demo`.
- Agenti dedicati: `.kilo/agent/aethermap-*.md`. **Non rimuovere senza consenso esplicito.**

---

## 10. Testing & qualità (verificato 2026-07-13)

- Backend: **108 file** `test_*.py` / **1674** test (`pytest --cov`, pytest-asyncio).
  Coverage `core/calculators/*` e `core/fitness_state` = 100% (metrica informativa globale).
- Frontend: **47 file** / **318** test Vitest; Playwright E2E 17 spec in `tests/e2e`.
- CI: backend pytest, frontend vitest, lint (Ruff + ESLint/vue-tsc), Trivy, build.
- BM2: `test_bm2_*` verdi; validazione fisica contro potenza misurata (MAE/RMSE/R²).

---

## 11. Sintesi delle scelte logiche programmatiche (riepilogo) ⭐

| # | Scelta | Dove | Perché |
|---|---|---|---|
| 1 | Stratificazione intelligenza vs strumenti esistenti | §1.1 | onboarding zero, valore unico su consiglio |
| 2 | Clean Architecture + calculators puri | §2 | testabilità, dominio indipendente da I/O |
| 3 | Kernel fisico unico `core/physics` | §3.1 | niente duplicazione, `bm2` delega qui |
| 4 | Fatigue pesata (durata+intensità 30%) | §3.5 | durata/intensità dominano il costo |
| 5 | Performance normalizzata per experience | §3.6 | confronto equo tra livelli |
| 6 | Route difficulty con roughness+capacità | §3.7 | superficie e livello atleta modellati |
| 7 | Athlete State = funzione del passato | §3.8 | non la singola uscita, ma la risposta |
| 8 | Load redistribution matematica + adattamento | §3.9, §4.4 | regole esplicite, non black-box |
| 9 | AI sceglie tra strategie, non inventa | §3.10 | affidabilità, spiegabilità |
| 10 | Proactive assistant a soglia segnale | §3.11 | non disturba se il valore è basso |
| 11 | Knowledge Layer boundary per AI Coach | §2, §4.3 | AI vede solo stati interpretati |
| 12 | Local-first: device = sorgente verità | §6 | offline totale, dati primari in locale |
| 13 | IndexedDB cache resiliente (no-op fallback) | §6.2 | non rompe in SSR/test |
| 14 | Engine pipeline + outbox, no DB-traversal | §4.3 | disaccoppiamento tra Engine |
| 15 | ModelResult con precision+confidence | §4.1 | ogni output porta incertezza |
| 16 | AetherMap separato, solo stack condiviso | §9 | R&D isolato, nessun accoppiamento |

---

*Questo documento è una **sintesi unificante** della documentazione esistente; i file
sorgente citati restano intatti e fanno autorità in caso di dettaglio. Per approfondimenti
specifici seguire i rimandi di sezione e l'indice del §0.*
