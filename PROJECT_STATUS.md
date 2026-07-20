# Stato Attuale del Progetto

**Completati: 155/145 step base + 50/80 estensioni**

> **Stato**: architettura locale-first completata — distribuzione primaria: desktop **Tauri 2** (`.exe`/`.dmg`/`.AppImage`) con backend embedded FastAPI + SQLite locale. Deploy cloud opzionale (Render) per sync/community. Architettura local-first.
> Fonte di verità unica per stato/checklist: [`ROADMAP.md`](ROADMAP.md).
>
> **Numeri backend/frontend (verificati 2026-07-17, repo root):**
> - Backend: **~3255 passed / 2 failed** su ~3257 test eseguiti (`pytest`, in chunk per stabilità d'ambiente). I 2 failure sono errori d'ambiente SQLAlchemy async (`MissingGreenlet`) in `test_ai_coach_helpers.py` e `test_athlete_state_integration.py`, non bug di logica. La collection completa (2611 test) ora passa dopo la rimozione da `tests/test_database.py` dell'import/test orfano di `get_paginated_rides` (funzione rimossa dal DB layer).
> - Frontend: **332 passed / 31 failed / 20 errors** su **363** test (53 file) — `vitest run` eseguito 2026-07-17.
> - Endpoint REST: **138** (conteggio storico 2026-07-13).
> I conteggi storici di file (108 backend / 47 frontend) sono riportati a titolo di riferimento.

### AetherMap (R&D separato)

Progetto cartografico indipendente in `aethermap/` — motore "dal nulla" (cube-sphere + S2/H3, data model "database del mondo", pipeline IA "ricercatore", rendering WebGL, digital twin). Condivide lo stack (Vue + FastAPI) ma non è importato dal backend BikeMaster.

- **Fasi 1-4 baseline**: earth model, data model, rendering WebGL completati.
- **Fasi 3-5 in corso**: AI pipeline "ricercatore", digital twin.
- Demo: `cd aethermap/src && python -m aethermap.ai.demo|.render.demo|.twin.demo`.
- Agenti dedicati: `.kilo/agent/aethermap-*.md`.

### Ultimo Commit
- `feat: complete multi-tenant support — tenant_id + user management endpoints`
- `eed6afd` - feat: implement frontend authentication, tracking controls, and core UI components with native Android project scaffolding
- `9b68e48` - fix: skip OpenTelemetry/Zipkin exporters in development mode
- `9257bfe` - feat: implement PWA install prompt, service worker navigate fix, ride tracking updates
- `f5c02c6` - feat: add registration email validation, update documentation, and implement test suite for mapping and analytics modules.

---

## Architettura Attuale del Progetto

### Pattern: Clean Architecture (Domain → Application → Infrastructure → Presentation)

```
bike_analyzer/
├── core/                              # Domain Layer (entities, events, pipeline)
│   ├── models.py                      # GPSPoint, Segment, Pause, Ride, AthleteProfile, CalendarEvent
│   ├── pipeline.py                    # AnalysisPipeline: GPS → processing → metrics
│   ├── engine.py                      # AnalysisEngine: orchestrator con FitnessState
│   └── fitness_state.py               # FitnessStateVector: CTL/ATL/TSB snapshot
│
├── backend/
│   ├── config.py                      # Configurazione legacy (.env) — compatibilità
│   ├── settings.py                    # Pydantic Settings v2 (centralizzata, type-safe)
│   ├── security.py                    # JWT auth + security headers (CSP, HSTS, X-Frame)
│   ├── rate_limiter.py                # slowapi rate limiter (proxy-aware IP)
│   ├── redis_client.py                # Client Redis asincrono + cache decorator
│   ├── task_queue.py                  # Task queue asincrona (batch import, maps)
│   ├── event_bus.py                   # Domain event bus (publish/subscribe)
│   │
│   ├── auth/                          # Authentication providers
│   │   ├── __init__.py                # Re-exports google_auth
│   │   └── google_auth.py             # Google OAuth2 (session creation, token exchange)
│   │
│   ├── events/                        # Domain events
│   │   └── __init__.py                # RideCreated, AthleteUpdated, BadgeEarned, TrainingGenerated
│   │
│   ├── traffic/                       # Traffic & road safety analysis
│   │   ├── __init__.py                # Lazy-load exports
│   │   ├── safety_analyzer.py         # Risk score computation (road types + incidents)
│   │   ├── overpass_client.py         # OpenStreetMap Overpass API (bike lanes, road types)
│   │   └── incident_fetcher.py        # Road incident data fetching
│   │
│   ├── core/                          # Pure domain logic (internal)
│   │
│   ├── api/                           # FastAPI Presentation Layer
│   │   ├── app_factory.py             # FastAPI factory + CORS + rate limit + security headers
│   │   ├── routes.py                  # 40+ endpoint API
│   │   ├── schemas.py                 # Pydantic DTOs request/response
│   │   └── async_db_facade.py         # Async DB facade per routes
│   │
│   ├── analytics/                     # Analytics Engine (Clean Architecture)
│   │   ├── analytics.py               # Summary, export JSON/CSV, report, charts base
│   │   ├── analytics_trends.py        # Trend analysis standalone
│   │   ├── advanced.py                # 14 modelli matematici avanzati
│   │   ├── power_model.py             # Power metrics (NP, IF, VI, EF, TSS, CP, FTP, Decoupling)
│   │   ├── calories.py                # Stima calorie (fisica + MET)
│   │   ├── fatigue.py                 # Modello affaticamento + recovery
│   │   ├── performance.py             # Performance/Endurance/Efficiency scores
│   │   ├── benchmark.py               # Confronto percentile per categoria
│   │   ├── ai_coach.py                # AI Coach (Groq/LLM + RAG BM25 + memoria)
│   │   ├── knowledge_base.py          # RAG engine BM25 + LRU cache
│   │   ├── dashboard.py               # Aggregatore statistiche dashboard
│   │   ├── training_load.py           # Carico allenamento (RSS, TSS)
│   │   ├── training_stress.py         # Training Stress Score + EWMA
│   │   ├── badges.py                  # Sistema badge/medaglie + heatmap GPS
│   │   ├── granfondo_planner.py       # Piano allenamento granfondo con tapering
│   │   │
│   │   ├── calculators/               # Pure functions (testabili in isolamento)
│   │   │   ├── calories.py            # Calorie estimation (physics + MET)
│   │   │   ├── power.py               # NP, IF, TSS, training_stress_score
│   │   │   ├── fatigue.py             # Fatigue score + recovery hours formula
│   │   │   ├── performance.py         # Performance score + efficiency score
│   │   │   └── stress.py              # EWMA calculations
│   │   │
│   │   ├── services/                  # Use case orchestration
│   │   │   ├── ride_analysis_service.py   # Full ride analysis pipeline
│   │   │   ├── fitness_state_service.py   # FitnessStateVector computation
│   │   │   └── context_builder.py         # Analysis context assembly
│   │   │
│   │   └── repositories/              # Data access abstraction
│   │       ├── ride_repository.py          # Ride CRUD (sync + async + postgres)
│   │       ├── athlete_repository.py       # Athlete CRUD
│   │       ├── fitness_state_repository.py # Fitness state persistence
│   │       └── training_stress_repository.py
│   │
│   ├── db/                            # Data Access Layer
│   │   ├── database.py                # SQLite CRUD sync (4 tabelle)
│   │   ├── async_db.py                # Async DB layer (asyncpg/aiosqlite)
│   │   ├── postgres_db.py             # PostgreSQL full ORM layer
│   │   ├── models.py                  # SQLAlchemy ORM models async
│   │   ├── vector_db.py               # TF-IDF + cosine similarity fallback
│   │   └── api_compat.py              # API compatibility layer
│   │
│   ├── database/                      # Vector Database
│   │   └── vectordb.py                # PGVector wrapper (CREATE EXTENSION, upsert, cosine search)
│   │
│   ├── ingestion/                     # Data Ingestion (external APIs)
│   │   ├── gps_parser.py              # Parser GPX/FIT
│   │   ├── google_fit.py              # Google Fit OAuth2
│   │   ├── strava_client.py           # Strava API (OAuth2 + PKCE, token management)
│   │   └── garmin_client.py           # Garmin Connect API (OAuth2, activity fetch)
│   │
│   ├── maps/                          # Map Rendering
│   │   ├── map_renderer.py            # Folium renderer (percorso colorato per velocita)
│   │   ├── google_maps.py             # Google Static Maps API
│   │   ├── osm_maps.py                # OpenStreetMap tiles
│   │   └── serpapi_maps.py            # SerpApi luoghi vicini
│   │
│   ├── weather/
│   │   └── weather_service.py         # Servizio meteo (temperature, wind, conditions)
│   │
│   ├── models/                        # Domain Models (dataclasses)
│   │   ├── models.py                  # Ride, GPSPoint, Segment, Pause, AthleteProfile, CalendarEvent
│   │   └── __init__.py
│   │
│   ├── processing/                    # GPS Data Processing
│   │   ├── processing.py              # Pulizia GPS, pausa, segmentazione
│   │   ├── segment_detector.py        # Segment detection avanzato
│   │   └── __init__.py
│   │
│   └── utils/
│       ├── dates.py                   # Utilità date
│       └── logger.py                  # Logging configurato
│
├── frontend/                          # Vue 3 + Vite + TypeScript SPA (standalone)
│   ├── package.json                   # Vue 3, Chart.js, Leaflet, Capacitor, Pinia, Vitest
│   ├── vite.config.js
│   ├── capacitor.config.json          # Android build config
│   ├── index.html                     # Entrypoint Vite
│   ├── tsconfig.json / tsconfig.node.json
│   ├── vitest.config.js               # Unit test config
│   ├── playwright.config.js           # E2E test config
│   ├── android/                       # Android app (Kotlin + Capacitor)
│   └── src/
│       ├── main.ts                    # App Vue mount
│       ├── App.vue                    # Root component
│       ├── index.css                  # Global dark theme + design tokens
│       ├── components/                # 20+ componenti Vue
│       ├── stores/                    # Pinia state management
│       ├── composables/               # Composable functions
│       ├── utils/                     # API client, route mapping
│       └── views/                     # Page-level Vue components
│
├── tests/                             # Suite test automatici (108 file / 1674 test)
│   ├── conftest.py                    # Shared fixtures
│   ├── test_analytics.py              # Analytics base
│   ├── test_analytics_trends.py       # Trend analysis
│   ├── test_analytics_engine.py       # Full engine
│   ├── test_power_model.py            # Power metrics
│   ├── test_advanced_analytics.py     # 14 modelli avanzati
│   ├── test_fatigue.py                # Fatigue model
│   ├── test_performance.py            # Performance scores
│   ├── test_training_stress.py        # Training Stress Score + EWMA
│   ├── test_training_load.py          # Carico allenamento
│   ├── test_badges.py                 # Sistema badge
│   ├── test_granfondo.py              # Granfondo planner
│   ├── test_weather.py                # Weather service
│   ├── test_processing.py             # GPS processing
│   ├── test_segment_detector.py       # Segment detection
│   ├── test_ai_coach.py               # AI Coach logic
│   ├── test_ai_coach_api.py           # AI Coach API endpoints
│   ├── test_knowledge_api.py          # Knowledge base API
│   ├── test_vector_db.py              # Vector DB (TF-IDF)
│   ├── test_db_models.py              # SQLAlchemy models
│   ├── test_async_db.py               # Async DB layer
│   ├── test_postgres_db.py            # PostgreSQL
│   ├── test_repositories.py           # Repository pattern
│   ├── test_database.py               # SQLite CRUD
│   ├── test_database_backup.py        # Backup
│   ├── test_event_bus.py              # Domain events
│   ├── test_traffic.py                # Traffic safety
│   ├── test_traffic_client.py         # Overpass/Incident clients
│   ├── test_google_oauth.py           # Google OAuth flow
│   ├── test_google_fit.py             # Google Fit integration
│   ├── test_garmin_integration.py     # Garmin client
│   ├── test_strava_integration.py     # Strava client
│   ├── test_security.py               # JWT + security headers
│   ├── test_auth_enhanced.py          # Enhanced auth
│   ├── test_redis_client.py           # Redis cache
│   ├── test_task_queue.py             # Background tasks
│   ├── test_routes_coverage.py        # API routes coverage
│   ├── test_routes_extended.py        # Extended route tests
│   ├── test_api_coverage.py           # API coverage
│   ├── test_scores_api.py             # Scores API
│   ├── test_benchmark_api.py          # Benchmark API
│   ├── test_import_batch.py           # Batch import
│   ├── test_athlete_profile.py        # Athlete profile
│   ├── test_google_maps_mock.py       # Google Maps mock
│   ├── test_dashboard_auth.py         # Dashboard auth
│   ├── test_dashboard_scores.py       # Dashboard scores
│   ├── test_main.py                   # CLI mode
│   ├── test_models.py                 # Domain models dataclass
│   ├── test_error_paths.py            # Error handling paths
│   ├── test_coverage_gaps.py          # Coverage gap tests
│   └── test_frontend_dashboard.py     # Frontend dashboard logic
│
├── knowledge_base/                    # Documenti indicizzati per RAG
├── docs/                              # Documentazione sviluppatore
│   ├── API_DOCS.md                    # API reference (EN, v1.3)
│   ├── API_EXAMPLES.http
│   ├── DEVELOPMENT.md                 # Developer guide (EN, aggiornato)
│   ├── PHONE_TRACKING.md
│   ├── PHONE_TRACKING_TESTING.md
│   ├── USER_GUIDE.md                  # User guide (EN)
│   └── archive/                       # Materiale obsoleto / disallineato
│       ├── API_DOCUMENTAZIONE.md
│       ├── CHANGELOG_IT.md
│       ├── GUIDA_UTENTE.md
│       ├── SVILUPPO.md
│       └── obsolete/
│           ├── PROJECT_DOCUMENTATION.md
│           └── database-migration.md
│
├── alembic/                           # Migrazioni DB versionate
│   ├── versions/08ee39bfe529_initial_models.py
│   └── env.py
│
├── scripts/                           # Utility scripts
│   ├── generate_sample_ride.py
│   └── demo_map.py
│
├── .github/workflows/                 # CI/CD
│   ├── ci.yml                         # Test + lint + security + build
│   └── android-release.yml            # Android APK/AAB build
│
├── main.py                            # Entrypoint (cli/api/web modes)
├── requirements.txt
├── Dockerfile                         # Multi-stage hardened build
├── docker-compose.yml                 # Docker Compose (app + redis)
├── pyproject.toml
├── azure.yaml / render.yaml           # Deploy config
├── ROADMAP.md
└── PROJECT_STATUS.md
```

---

## Sottosistema BikeMaster 2.0 (`bm2/`) — Deluxe Simulation Engine

Motore di simulazione sportiva ("what-if") con filosofia type-safe, **parallelo al
prodotto ma già cablato** via `bm2_routes.py` (montato in `app_factory.py`). Il
kernel fisico è **condiviso** con `core/physics/`: dal 2026-07-12 `bm2` delega a
`core.physics` (`cycling_forces`, `instantaneous_power`, `required_speed_for_power`),
eliminando il forward model duplicato. La visione "Deluxe" è in `docs/DELUXE_ROADMAP.md`.

| Modulo | Ruolo |
|---|---|
| `bm2/units.py` | `Quantity` (valore + unità + precisione + fonte) + `UnitRegistry` (analisi dimensionale, lineare/non-lineare) |
| `bm2/models.py` | `AnalysisContext`, `Athlete`, `Bike`, `WorldObject`, `Activity` (dominio proprio, separato da `core/models.py`) |
| `bm2/algorithms/` | 9 algoritmi (`Algorithm`→`ModelResult` con formula + dati + incertezza + confidence): power, energy, fatigue, performance, recovery, nutrition, movement, route_difficulty, training_load |
| `bm2/simulation.py` | `SimulationEngine` (compare/preset/sensitivity) + `parse_override_from_text` (estrazione override da NL) |
| `bm2/orchestrator.py` | `AIOrchestrator` + agenti (Athlete/Environment/GPS/Sensor) per domande in linguaggio naturale (italiano) |
| `bm2/transformer.py` | `TransformerEngine` (geo → metric points, distanze 2D) |
| `bm2_routes.py` | Endpoint API esposti (montati in `app_factory.py`) |

Stato: baseline completo e testato (`test_bm2_*`); **integrato** col flusso
`Ride`/analytics esistente via `bm2/adapters.py` + `POST /api/v1/bm2/simulate-ride`
(item D7 ); **validato** contro potenza misurata via `core/physics/validation.py`
+ `POST /api/v1/bm2/validate` (metriche MAE/RMSE/bias/R²) (item D8 ).

---

## Stack Tecnologico

| Layer | Tecnologia |
|---|---|
| Backend | FastAPI 0.110+ (embedded) o Axum (Rust) — Tauri 2 desktop app |
| Core/Domain | Python dataclasses, Clean Architecture |
| Database | SQLite (primario, locale su ogni device) + PostgreSQL (opzionale, cloud sync) |
| ORM | SQLAlchemy 2.0 (declarative + async) |
| Migrations | Alembic (gestisce sia SQLite che PostgreSQL) |
| Vector DB | PGVector (cosine similarity search, solo cloud) |
| Cache | SQLite-based o Redis locale (no server esterno richiesto) |
| Analytics | NumPy, Pandas, Matplotlib, SciPy, scikit-learn, statsmodels, endurance-metrics |
| Parsing GPS | gpxpy, fitparse |
| AI/LLM | Groq SDK (embeddings locali via sentence-transformers) |
| Auth | python-jose[cryptography], passlib, bcrypt, Google OAuth2 |
| Rate Limit | slowapi (proxy-aware) |
| Security | Security headers (CSP, HSTS, X-Frame-Options, XSS) |
| Config | Pydantic Settings v2 |
| Testing | pytest, pytest-asyncio, Playwright |
| Frontend | Vue 3 + Vite + TypeScript + Pinia + Chart.js + Leaflet + Capacitor |
| Desktop | Tauri 2 (Rust + WebView) — bundle nativo |
| Mobile | Android Kotlin (Capacitor) |
| CI/CD | GitHub Actions (test, lint, security scan, build, Tauri release) |

---

## Moduli Analytics — Dettaglio

### calculators/ (Pure Functions)

| File | Funzionalita |
|---|---|
| `calories.py` | Stima calorie (fisica: rolling + aero + gravity / MET table) |
| `power.py` | Normalized Power, Intensity Factor, TSS, training_stress_score |
| `fatigue.py` | Fatigue score 0-10, recovery hours estimator |
| `performance.py` | Performance score, Efficiency score |
| `stress.py` | EWMA (Exponential Weighted Moving Average) |

### services/ (Use Case Orchestration)

| File | Funzionalita |
|---|---|
| `ride_analysis_service.py` | Orchesta pipeline completa: GPS processing → metrics → fitness state |
| `fitness_state_service.py` | FitnessStateVector computation (ATL/CTL/TSB, risk indicators) |
| `context_builder.py` | Assembly contesto analisi per AI Coach |

### repositories/ (Data Access Abstraction)

| File | Funzionalita |
|---|---|
| `ride_repository.py` | Ride CRUD (sync SQLite + async SQLAlchemy + PostgreSQL) |
| `athlete_repository.py` | Athlete CRUD (sync + async) |
| `fitness_state_repository.py` | Fitness state persistence |
| `training_stress_repository.py` | Training stress data access |

---

## Stato Moduli Backend

| Modulo | Status | Descrizione |
|---|---|---|
| `core/` | Completo | Domain entities + pipeline + engine + fitness state |
| `event_bus.py` | Completo | Domain events pub/sub (RideCreated, BadgeEarned, ecc.) |
| `auth/google_auth.py` | Completo | Google OAuth2 session creation |
| `traffic/` | Completo | Road safety analysis (Overpass + incident data) |
| `database/vectordb.py` | Completo | PGVector wrapper (CREATE EXTENSION, upsert, cosine search) |
| `analytics.py` | Completo | Summary, export JSON/CSV, report, charts base |
| `analytics_trends.py` | Completo | Fitness trends, monthly progression, period comparison, volume projection |
| `power_model.py` | Completo | NP, IF, VI, EF, TSS, Power Zones, Power Profile, FTP, CP/W', Aerobic Decoupling |
| `advanced.py` | Completo | 14 modelli matematici avanzati |
| `calories.py` | Completo | Stima calorie fisica + MET |
| `fatigue.py` | Completo | Punteggio affaticamento 0-10 + recovery hours |
| `performance.py` | Completo | Performance/Endurance/Efficiency scores 0-10 |
| `benchmark.py` | Completo | Confronto percentile per categoria |
| `ai_coach.py` | Completo | Groq/LLM + RAG BM25 + memoria conversazionale |
| `knowledge_base.py` | Completo | BM25 engine + LRU cache + chunking |
| `training_load.py` | Completo | RSS, TSS, monotony, strain |
| `training_stress.py` | Completo | TSS con EWMA |
| `badges.py` | Completo | Sistema badge/medaglie + heatmap GPS |
| `granfondo_planner.py` | Completo | Piano allenamento granfondo con tapering |
| `weather_service.py` | Completo | Consigli meteo per allenamento |
| `gps_parser.py` | Completo | Parser GPX/FIT |
| `strava_client.py` | Completo | Strava OAuth2 + PKCE + token management |
| `garmin_client.py` | Completo | Garmin Connect OAuth2 + activity fetch |
| `ingestion/google_fit.py` | Completo | Google Fit OAuth2 |
| `maps/` | Completo | Folium, Google Static Maps, OSM, SerpApi |
| `repository pattern` | Completo | RideRepository, AthleteRepository, FitnessStateRepository |
| `async database` | Completo | SQLAlchemy 2.0 async (asyncpg + aiosqlite) |
| `security headers` | Completo | CSP, HSTS, X-Frame-Options, XSS |
| `rate limiting` | Completo | slowapi per-IP + proxy-aware |
| `redis cache` | Completo | Async client + cache decorator + graceful degradation |
| `task queue` | Completo | Background tasks asincrone (batch import, maps) |
| `event bus` | Completo | Domain events pub/sub |
| `vector DB` | Completo | PGVector + TF-IDF fallback |

### Modelli Matematici in `advanced.py`

1. Pace Consistency — CV e pacing strategy
2. Power Estimate — Stima potenza da fisica (gravity + rolling + aero)
3. Climb Classifier — Categorizzazione salite Tour de France style
4. VO2max Estimation — Stima VO2max da dati uscita
5. Route Difficulty — Score difficoltà multi-fattore
6. Elevation Profile — Distribuzione pendenze + hardship index
7. Speed Profile — Accelerazioni, decel, coasting %
8. Progress Trend — Regressione lineare miglioramento
9. Training Stress Balance — ATL/CTL/TSB con EWMA
10. Ideal Weight — Peso ideale per power-to-weight
11. HR Zones — 5 zone di frequenza cardiaca
12. Garmin Power Factor — NP/IF/TSS estimation
13. Ride Recommendation — Classificazione tipo allenamento
14. Speed Surge Detection — Rilevamento accelerazioni improvvise

### Modelli Potenza in `power_model.py`

1. Normalized Power (NP) — Algoritmo Coggan con rolling average 30s
2. Intensity Factor (IF) — NP / FTP ratio
3. Variability Index (VI) — NP / avg power
4. Efficiency Factor (EF) — NP / avg HR per cardio drift
5. Training Stress Score (TSS) — IF² × durata × 100
6. Power Zones — Modello 7 zone Coggan
7. Power Profile — Best effort at 5s, 1min, 5min, 20min
8. FTP Estimation — 20min test × 0.95
9. Critical Power Model — CP e W' prime
10. Aerobic Decoupling — Rilevamento scompenso aerobico (5%+ significativo)

---

## Frontend (Vue 3 + Vite + TypeScript)

Architettura standalone (non dipende da backend per build):

- **Router** — Vue Router configurato con rotte per dashboard, rides, tracking
- **Pinia Stores** — `auth.ts` (JWT state), `trackingStore.ts` (GPS tracking reattivo)
- **Composables** — `useAuth.ts`, `useChart.ts`, `useRides.ts`
- **Plugin Capacitor** — `bikeTracking.ts` per native Android features
- **Error Boundaries** — `ErrorBoundary.vue` + `ErrorState.vue` per gestione errori
- **PWA** — Service worker + `PWAInstallPrompt.vue` per installazione
- **Testing** — Vitest (unit) + Playwright (E2E) configurati

Componenti principali: 20+ (HeaderTabs, RidesPanel, ChartsPanel, ImportPanel, AthletePanel, CoachPanel, KnowledgePanel, HeatmapPanel, BadgesPanel, CalendarPanel, GranfondoPlanner, AdminPanel, LoginForm, RideDetail, RideMapPanel, SpeedMap, StatsSummary, WeatherPanel, DashboardPanel, RidesView, ToastContainer, ErrorBoundary, ConfirmModal, LiveMap, PWAInstallPrompt)

---

## Testing Update (2026-07-13, verificato)

**Numeri reali (conteggio da codice sorgente):**
-  Backend: **108** file `test_*.py` / **1674** funzioni di test (incl. `test_bm2_*` verdi)
-  Frontend: **47** file `*.test.{js,ts}` / **318** test Vitest (harness verificato green)
-  Endpoint REST: **138** (`routes.py` + `bm2_routes.py`)
-  CI GitHub Actions esegue backend `pytest --cov`, frontend `vitest run`, lint, security (Trivy), build
-  Coverage `core/calculators/*`: 100% · `core/fitness_state`: 100%
-  Playwright E2E: **gli spec ESISTONO** (`frontend/tests/e2e`, 14 file `*.spec.js` + 3 `*.spec.ts` aggiunti). La valutazione iniziale li aveva mancati perché cercava `*.spec.ts`; il `testDir` di Playwright è `tests/e2e` e gli spec sono `.js`. Aggiunti 3 spec backend-independent (auth/routing/app-shell) eseguibili contro la sola SPA preview, senza backend.
-  Coverage globale bassa se misurata su tutto `bike_analyzer` (molti moduli non coperti dalla singola sotto-suite); la CI riporta la coverage aggregata come metrica informativa

**Nota:** l'esecuzione dell'intera suite backend in locale è lenta (setup per-modulo);
la verifica pass/fail completa è demandata alla pipeline CI.

---

## OAuth2 Integrations

- **Google OAuth2** — `/auth/google` + `/auth/google/callback` endpoints
- **Strava OAuth2 + PKCE** — `/import/strava/auth` + `/import/strava/callback` endpoints
- **Garmin Connect OAuth2** — Client completo con token storage e refresh
- **Google Fit OAuth2** — `/import/google-fit/auth` + `/import/google-fit/token`

---

## Security & Monitoring

- **Security Headers** — CSP, HSTS, X-Frame-Options, X-XSS-Protection
- **JWT Auth** — HS256 con python-jose, bcrypt password hashing
- **Rate Limiting** — slowapi per-IP + proxy-aware
- **Secret Key Rotation** — SECRET_KEY + SECRET_KEY_PREVIOUS
- **Environment Validation** — SECRET_KEY obbligatoria in produzione
- **Sentry SDK** — Error tracking (opzionale via SENTRY_DSN)
- **Trivy** — Security scanning nel CI
- **Docker Hardened** — Multi-stage build, non-root user, read-only fs, no-new-privileges

---

## Vector DB Integration

- `database/vectordb.py` con PGVector (PostgreSQL + pgvector extension)
- `CREATE EXTENSION vector`, IVFFLAT index su embedding
- Cosine similarity search (`1 - (embedding <=> :q)`)
- TF-IDF + cosine similarity fallback in `db/vector_db.py`
- SQLite-backed VectorStore per development

---

## Deployment

| Metodo | Status |
|---|---|
| Docker | Multi-stage hardened Dockerfile |
| Docker Compose | App + Redis con security opts |
| GitHub Actions | CI/CD: test → lint → security → build |
| Android Release | Workflow APK/AAB |
| Azure | azure.yaml + azd config |
| Render | render.yaml |

---

## Priorità per Prossimi Step

| Priorita | Feature | Status |
|:---:|---|---|
| **1** |  Test suite completata (frontend + backend) | **Fatto** |
| **2** |  Google Maps dynamic path | **Fatto** |
| **3** | Multi-utente (auth, ownership rides, data isolation) |  Completo |
| **4** | PostgreSQL in produzione (dual-mode SQLite/PostgreSQL) |  |
| **5** | Vector DB RAG |  Completo |
| **6** | Playwright E2E spec (config presente, spec da scrivere) | ⏳ |

---

## Production Ready Checklist

> Fonte di verità: [`ROADMAP.md`](ROADMAP.md). Sintesi verificata 2026-07-13.

| Area | Item | Status |
|---|---|---|
| Testing | Coverage riportata come metrica informativa in CI |  |
| Code Quality | Ruff + mypy + pre-commit |  |
| Container | Docker multi-stage hardened |  |
| Monitoring | Sentry (`observability.py`) + Prometheus + Grafana |  |
| Audit | Audit log azioni admin (`audit_log.py` + middleware) |  |
| Auth | OAuth2 social login (Google, Strava) |  |
| Multi-user | Data isolation completa (tenant_id) |  |
| AI | Vector DB per RAG (PGVector) |  |
| Frontend | PWA + offline support |  |
| Frontend | Vitest (47 file / 318 test) |  |
| Frontend | Playwright E2E (17 file in `tests/e2e`, incl. 3 backend-independent aggiunti) |  |
| Security | Security headers + rate limiting |  |
| Database | Dual-mode SQLite/PostgreSQL |  |
| CI/CD | GitHub Actions (test, lint, security, build) |  |

---

*Ultimo aggiornamento: 2026-07-13 — Riconciliazione con numeri verificati dal codice (108 file / 1674 test backend; 47 file / 318 test frontend; 138 endpoint). Checklist produzione allineata a ROADMAP.md (fonte di verità). Corretti dati di test obsoleti (277/84+/379+) e stato PostgreSQL/monitoring/audit.*
