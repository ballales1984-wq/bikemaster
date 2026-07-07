# BikeMaster - Sistema di Analisi Intelligente delle Performance Ciclistiche

GPS-based cycling performance intelligence system. Importa le tue uscite da file GPX/FIT, analizza le metriche di potenza, stima calorie e affaticamento, visualizza i percorsi su mappe interattive e accedi a tutto tramite una REST API completa.

---

## Indice

1. [Caratteristiche](#caratteristiche)
2. [Stack Tecnologico](#stack-tecnologico)
3. [Quick Start](#quick-start)
4. [Configurazione](#configurazione)
5. [Architettura Repository](#architettura-repository)
6. [Modelli di Dato](#modelli-di-dato)
7. [API Reference](#api-reference)
8. [Motore Analitico](#motore-analitico)
9. [Dashboard](#dashboard)
10. [AI Coach](#ai-coach)
11. [Integrazioni Esterne](#integrazioni-esterne)
12. [Sicurezza Stradale](#sicurezza-stradale)
13. [Phone GPS Tracking](#phone-gps-tracking)
14. [Deployment](#deployment)
15. [Sviluppo](#sviluppo)
16. [Testing](#testing)
17. [Roadmap](#roadmap)

---

## Caratteristiche

- **Ingestione GPS** - Parsing file GPX (gpxpy) e Garmin FIT (fitparse)
- **Analisi percorso** - Distanza, velocità, elevazione, accelerazioni, soste
- **Stima calorie** - Modello fisico (resistenza aria + attrito) + MET
- **Punteggio affaticamento** - Formula ponderata con raccomandazioni di recupero
- **Mappe interattive** - Percorsi colorati per velocita con Folium/Leaflet
- **Knowledge Base** - Documenti sportivi indicizzati per RAG (BM25 + PGVector)
- **AI Coach** - Consigli di allenamento e recupero basati su Groq/LLM
- **Google Fit** - Importazione automatica attivita ciclistiche
- **Google Maps** - Mappe statiche con API key
- **Strava** - Import/export attivita con OAuth2 + PKCE
- **Garmin Connect** - Sincronizzazione attivita con OAuth2
- **Calendario** - Pianificazione eventi di allenamento
- **Dashboard Web** - UI dark-themed con statistiche e lista uscite (Vue 3 + Vite + TS)
- **Heatmap GPS** - Visualizzazione densita percorsi
- **Sistema Badge** - Medaglie e achievements
- **Piano Granfondo** - Generatore piani con tapering
- **Servizio Meteo** - Consigli meteo per uscite
- **Training Stress** - TSS, ATL/CTL/TSB, EWMA
- **Traffic Safety** - Analisi sicurezza percorsi (infrastruttura ciclabile, incidenti)
- **Event Bus** - Sistema eventi dominio (RideCreated, BadgeEarned, ecc.)
- **Phone GPS Tracking** - Registrazione uscite direttamente dal telefono mobile (Android)
- **REST API** - 40+ endpoint documentati
- **Esportazione** - JSON e CSV
- **JWT Auth** - Login e protezione endpoint
- **Google OAuth2** - Login social con Google
- **Rate Limiting** - Protezione API per-IP
- **Background Tasks** - Queue asincrona per operazioni pesanti
- **Cache Redis** - Caching con fallback graceful
- **PWA** - Progressive Web App con install prompt

---

## Stack Tecnologico

| Layer | Tecnologia |
|---|---|
| Backend | FastAPI 0.110+, Python 3.11+ |
| Core | Domain layer (models, pipeline, engine, fitness state) |
| Database | SQLite (dev) + PostgreSQL (prod, asyncpg) |
| ORM | SQLAlchemy 2.0 (async + sync) |
| Migrations | Alembic |
| Vector DB | PGVector (similarity search) |
| Cache | Redis (opzionale, fallback in-memory) |
| Maps | Folium / Leaflet.js / Google Static Maps / OSM |
| Analytics | NumPy, Pandas, Matplotlib, SciPy, scikit-learn, statsmodels |
| Parsers | gpxpy, fitparse |
| Auth | python-jose, passlib, bcrypt, Google OAuth2 |
| AI/LLM | Groq SDK + OpenAI SDK |
| Rate Limit | slowapi |
| Config | Pydantic Settings v2 |
| Testing | pytest, pytest-asyncio, Playwright |
| Frontend | Vue 3 + Vite + TypeScript + Chart.js + Leaflet |
| Mobile | Android Kotlin (Capacitor) |

---

## Quick Start

### Prerequisiti
- Python 3.11 o superiore
- pip
- Browser web

### Installazione

```bash
git clone https://github.com/ballales1984-wq/bikemaster.git
cd bikemaster
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Avvio

```bash
# API + Dashboard (default)
python main.py api

# Solo frontend standalone
python main.py web

# CLI demo analytics
python main.py cli
```

Apri http://localhost:8000 per la dashboard.

### Docker

```bash
docker compose up -d
```

---

## Configurazione

Copia `.env.example` in `.env` e configura:

```env
# Database
DATABASE_URL=sqlite:///./rides.db        # o postgresql://...
DATABASE_URL_ASYNC=sqlite+aiosqlite:///./rides.db  # async engine

# API
API_HOST=0.0.0.0
API_PORT=8000

# Google
GOOGLE_MAPS_API_KEY=your_key_here        # Opzionale
GOOGLE_FIT_CLIENT_ID=your_key_here       # Opzionale
GOOGLE_FIT_CLIENT_SECRET=your_key_here   # Opzionale
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org

# Strava
STRAVA_CLIENT_ID=your_key_here           # Opzionale
STRAVA_CLIENT_SECRET=your_key_here       # Opzionale
STRAVA_REDIRECT_URI=http://localhost:8000/api/v1/auth/strava/callback

# Garmin
GARMIN_CONSUMER_KEY=your_key_here        # Opzionale
GARMIN_CONSUMER_SECRET=your_key_here     # Opzionale

# AI Coach
GROQ_API_KEY=your_key_here               # Opzionale per AI Coach
OPENAI_API_KEY=your_key_here             # Opzionale per Vector DB

# Security (OBBLIGATORIO in produzione)
SECRET_KEY=your_secret_key               # Min 32 caratteri
SECRET_KEY_PREVIOUS=prev_key_rotation    # Opzionale per rotazione

# Redis (opzionale, fallback in-memory)
REDIS_URL=redis://localhost:6379/0
```

---

## Architettura Repository

```
bikeMaster/
├── main.py                          # Entrypoint applicazione
├── requirements.txt                 # Dipendenze Python
├── pyproject.toml                   # Build system
├── Dockerfile / docker-compose.yml   # Containerizzazione
├── azure.yaml / render.yaml         # Deploy config
│
├── bike_analyzer/                   # Package Python
│   ├── __init__.py
│   ├── main.py                      # CLI wrapper
│   ├── core/                        # Domain Layer (Clean Architecture)
│   │   ├── models.py                # Entita dominio (Ride, GPSPoint, Athlete, ecc.)
│   │   ├── pipeline.py              # AnalysisPipeline: GPS → processing → metrics
│   │   ├── engine.py                # AnalysisEngine: orchestratore con FitnessState
│   │   └── fitness_state.py         # FitnessStateVector: CTL/ATL/TSB snapshot
│   └── backend/
│       ├── config.py                # Configurazione legacy (.env)
│       ├── settings.py              # Pydantic Settings v2 (centralizzata)
│       ├── security.py              # JWT auth + security headers
│       ├── redis_client.py          # Client Redis + cache
│       ├── task_queue.py            # Background task queue
│       ├── event_bus.py             # Domain event bus (pub/sub)
│       │
│       ├── core/                    # Pure domain logic
│       ├── auth/                    # OAuth2 providers (Google, Strava, Garmin)
│       ├── events/                  # Domain events & event bus
│       │   ├── __init__.py          # Event definitions + publish/subscribe
│       ├── traffic/                 # Traffic & road safety analysis
│       │   ├── safety_analyzer.py   # Risk score computation
│       │   ├── overpass_client.py   # OpenStreetMap data fetching
│       │   └── incident_fetcher.py  # Road incident data
│       │
│       ├── api/                     # FastAPI layer
│       │   ├── app_factory.py       # FastAPI application factory
│       │   ├── routes.py            # 40+ endpoint API
│       │   ├── schemas.py           # Pydantic DTOs
│       │   └── async_db_facade.py   # Async DB facade
│       │
│       ├── analytics/               # Analytics engine (Clean Architecture)
│       │   ├── analytics.py         # Summary, export, report, charts
│       │   ├── analytics_trends.py  # Trend analysis (fitness, monthly, projection)
│       │   ├── advanced.py          # 14 modelli matematici avanzati
│       │   ├── power_model.py       # Power metrics (NP, IF, TSS, CP, FTP)
│       │   ├── calories.py          # Calcolo calorie (fisica + MET)
│       │   ├── fatigue.py           # Modello fatigue + recovery
│       │   ├── performance.py       # Score engine (performance/endurance/efficiency)
│       │   ├── benchmark.py         # Confronto percentile per categoria
│       │   ├── ai_coach.py          # AI Coach (Groq + RAG + memoria)
│       │   ├── knowledge_base.py    # RAG engine BM25 + LRU cache
│       │   ├── dashboard.py         # Statistiche aggregate dashboard
│       │   ├── training_load.py     # Carico allenamento (RSS, TSS)
│       │   ├── training_stress.py   # Training Stress Score + EWMA
│       │   ├── badges.py            # Sistema badge/heatmap
│       │   ├── granfondo_planner.py # Piano granfondo con tapering
│       │   ├── calculators/         # Pure functions (testable in isolation)
│       │   │   ├── calories.py      # Calorie estimation
│       │   │   ├── power.py         # NP, IF, TSS calculation
│       │   │   ├── fatigue.py       # Fatigue score formula
│       │   │   ├── performance.py   # Performance/endurance scores
│       │   │   └── stress.py        # EWMA, stress calculations
│       │   ├── services/            # Use case orchestration
│       │   │   ├── ride_analysis_service.py  # Full ride analysis pipeline
│       │   │   ├── fitness_state_service.py  # Fitness state vector computation
│       │   │   └── context_builder.py        # Analysis context assembly
│       │   └── repositories/        # Data access abstraction
│       │       ├── ride_repository.py    # Ride CRUD (sync + async)
│       │       ├── athlete_repository.py # Athlete CRUD
│       │       ├── fitness_state_repository.py # Fitness state persistence
│       │       └── training_stress_repository.py
│       │
│       ├── db/                      # Data access layer
│       │   ├── database.py          # SQLite CRUD layer (sync)
│       │   ├── async_db.py          # Async DB layer (PostgreSQL + SQLite)
│       │   ├── postgres_db.py       # PostgreSQL full ORM
│       │   ├── models.py            # SQLAlchemy ORM models (async)
│       │   └── vector_db.py         # TF-IDF + cosine similarity fallback
│       │
│       ├── database/                # Vector database
│       │   └── vectordb.py          # PGVector wrapper (embedding storage + search)
│       │
│       ├── ingestion/               # Data ingestion
│       │   ├── gps_parser.py        # Parser GPX/FIT
│       │   ├── google_fit.py        # Google Fit OAuth2
│       │   ├── strava_client.py     # Strava API (OAuth2 + PKCE)
│       │   └── garmin_client.py     # Garmin Connect API (OAuth2)
│       │
│       ├── maps/                    # Map rendering
│       │   ├── map_renderer.py      # Render Folium (percorso colorato)
│       │   ├── google_maps.py       # Google Static Maps API
│       │   ├── osm_maps.py          # OpenStreetMap tiles
│       │   └── serpapi_maps.py      # SerpApi luoghi vicini
│       │
│       ├── weather/
│       │   └── weather_service.py   # Servizio meteo
│       │
│       ├── models/                  # Dataclass domain models
│       │   ├── models.py            # Ride, GPSPoint, Segment, Pause, AthleteProfile
│       │   └── __init__.py
│       │
│       ├── processing/              # GPS data processing
│       │   ├── processing.py        # Pulizia GPS, pausa, segmentazione
│       │   ├── segment_detector.py  # Segment detection avanzato
│       │   └── __init__.py
│       │
│       └── utils/
│           ├── dates.py             # Utilità date
│           └── logger.py            # Logging configurato
│
├── frontend/                        # Vue 3 + Vite + TypeScript SPA
│   ├── package.json                 # Vue 3, Chart.js, Leaflet, Capacitor, Pinia
│   ├── vite.config.js
│   ├── capacitor.config.json        # Android build config
│   ├── index.html                   # Entrypoint Vite
│   ├── dist/                        # Build output
│   ├── android/                     # Android app (Kotlin)
│   │   └── app/src/main/
│   │       ├── .../tracking/BikeTrackingService.kt   # Foreground service
│   │       └── .../plugins/BikeTrackingPlugin.kt      # Capacitor plugin
│   └── src/
│       ├── main.ts                  # App Vue mount
│       ├── App.vue                  # Root component
│       ├── index.css                # Global dark theme styles
│       ├── shims-vue.d.ts           # TypeScript Vue shims
│       ├── types/index.d.ts         # TypeScript type declarations
│       ├── router/index.ts          # Vue Router config
│       ├── components/              # 20+ componenti Vue
│       │   ├── HeaderTabs.vue       # Navigazione tab
│       │   ├── RidesPanel.vue       # Lista uscite con filtri
│       │   ├── ChartsPanel.vue      # Grafici Chart.js
│       │   ├── ImportPanel.vue      # Upload GPX/FIT
│       │   ├── AthletePanel.vue     # Profilo atleta
│       │   ├── AthleteSettings.vue  # Impostazioni atleta
│       │   ├── CoachPanel.vue       # AI Chat
│       │   ├── KnowledgePanel.vue   # Ricerca knowledge base
│       │   ├── HeatmapPanel.vue     # Heatmap GPS interattiva
│       │   ├── BadgesPanel.vue      # Sistema badge
│       │   ├── CalendarPanel.vue    # Calendario allenamento
│       │   ├── GranfondoPlanner.vue # Piano granfondo
│       │   ├── AdminPanel.vue       # Pannello admin
│       │   ├── LoginForm.vue        # Form login JWT
│       │   ├── RideDetail.vue       # Dettaglio uscita
│       │   ├── RideMetricsPanel.vue # Metriche real-time tracking
│       │   ├── RideMapPanel.vue     # Mappa percorso
│       │   ├── SpeedMap.vue         # Mappa velocita
│       │   ├── StatsSummary.vue     # Riepilogo statistiche
│       │   ├── WeatherPanel.vue     # Consigli meteo
│       │   ├── DashboardPanel.vue   # Vista dashboard
│       │   ├── RidesView.vue        # Vista lista uscite
│       │   ├── PWAInstallPrompt.vue # Prompt installazione PWA
│       │   ├── ToastContainer.vue   # Notifiche toast
│       │   ├── ErrorBoundary.vue    # Gestione errori
│       │   └── ConfirmModal.vue     # Dialog conferma
│       ├── stores/                  # Pinia state management
│       │   ├── auth.ts              # Auth state
│       │   └── trackingStore.ts     # GPS tracking state
│       ├── composables/             # Composable functions
│       │   ├── useAuth.ts           # Autenticazione
│       │   ├── useChart.ts          # Grafici
│       │   └── useRides.ts          # Gestione uscite
│       ├── utils/
│       │   ├── api.ts               # API client
│       │   └── routeMap.ts          # Route mapping utilities
│       └── views/
│           └── RideTracking.vue     # Pagina tracking GPS live
│
├── tests/                           # Suite test automatici (51+ file)
├── knowledge_base/                  # Documenti indicizzati per RAG
├── docs/                            # Documentazione sviluppatore
├── .github/workflows/ci.yml         # CI/CD GitHub Actions
├── .github/workflows/android-release.yml  # CI Android release
├── ROADMAP.md                       # Roadmap progetto
├── PROJECT_STATUS.md                # Stato corrente del progetto
└── requirements.txt
```

---

## Modelli di Dato

### GPSPoint
Punto GPS individuale con latitudine, longitudine, timestamp, altitudine e velocita.

| Campo | Tipo | Descrizione |
|---|---|---|
| lat | float | Latitudine WGS84 |
| lon | float | Longitudine WGS84 |
| timestamp | datetime | Istante del rilevamento |
| altitude | Optional[float] | Altitudine in metri |
| speed | Optional[float] | Velocita in km/h |
| power | Optional[float] | Potenza in watt |
| heart_rate | Optional[float] | Frequenza cardiaca |
| cadence | Optional[float] | Cadenza |

### Ride
Rappresenta una sessione ciclistica completata.

| Campo | Tipo | Descrizione |
|---|---|---|
| id | Optional[int] | Identificativo univoco DB |
| athlete_id | Optional[int] | FK al profilo atleta |
| date | str | Data uscita (ISO) |
| distance_km | float | Distanza totale km |
| duration_minutes | float | Durata in minuti |
| avg_speed_kmh | float | Velocita media km/h |
| weight_kg | float | Peso atleta (default 70kg) |
| calories | float | Calorie stimate |
| heart_rate_avg | Optional[float] | FC media |
| elevation_gain_m | Optional[float] | Dislivello positivo |
| external_source | Optional[str] | Fonte import (strava, garmin) |
| external_id | Optional[str] | ID sorgente esterna |
| title | Optional[str] | Nome uscita |
| gps_points | Optional[list[GPSPoint]] | Array completo punti |

### AthleteProfile
Profilo completo dell'atleta per calcoli personalizzati.

| Campo | Tipo | Descrizione |
|---|---|---|
| id | Optional[int] | Identificativo |
| name | str | Nome |
| age | int | Eta |
| weight_kg | float | Peso kg |
| height_cm | Optional[float] | Altezza cm |
| fat_percentage | Optional[float] | Massa grassa % |
| years_active | int | Anni di attivita |
| weekly_sessions | int | Sessioni settimanali |
| monthly_hours | float | Ore mese |
| annual_hours | float | Ore anno |
| experience_level | str | Livello (Beginner->Elite) |
| goals | Optional[str] | Obiettivi |
| preferred_terrain | Optional[str] | Terreno preferito |
| weekly_volume_km | float | Volume km settimana |
| ftp_watts | Optional[float] | Functional Threshold Power |
| best_segments | Optional[str] | Segmenti preferiti |
| medical_notes | Optional[str] | Note mediche |
| equipment | Optional[str] | Attrezzatura |

### FitnessStateVector
Stato fisiologico corrente dell'atleta.

| Campo | Tipo | Descrizione |
|---|---|---|
| atl | float | Acute Training Load (7-day) |
| ctl | float | Chronic Training Load (42-day) |
| tsb | float | Training Stress Balance |
| fitness | float | Livello fitness |
| fatigue | float | Livello fatica |
| form | float | Forma corrente |
| recovery_hours_needed | float | Ore recupero stimate |
| weekly_tss | float | TSS ultimi 7 giorni |
| monthly_tss | float | TSS ultimi 30 giorni |
| trend_7d | str | Trend 7 giorni |
| trend_30d | str | Trend 30 giorni |
| risk_indicators | list[str] | Indicatori di rischio |
| recommendation | str | Raccomandazione |

### Entity Figlie
- `CalendarEvent` - Evento di allenamento pianificato
- `Segment` - Segmento tra due GPSPoint
- `Pause` - Sosta rilevata durante la corsa
- `RouteStatistics` - Statistiche aggregate percorso

---

## API Reference

Base URL: `/api/v1`

### Health & Auth
| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/health/detailed` | Health dettagliato |
| POST | `/auth/login` | Login JWT |
| POST | `/auth/register` | Registrazione |
| GET | `/auth/google` | URL OAuth Google |
| POST | `/auth/google/callback` | Exchange token Google |
| GET | `/auth/strava` | URL OAuth Strava |
| POST | `/auth/strava/callback` | Exchange token Strava |

### Rides CRUD
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| POST | `/rides` | Yes | Crea uscita |
| GET | `/rides` | No | Elenca uscite (paginate) |
| GET | `/rides/{id}` | Yes | Dettaglio uscita (+fatigue + cal/km) |
| PUT | `/rides/{id}` | Yes | Aggiorna uscita |
| DELETE | `/rides/{id}` | Yes | Elimina uscita |
| GET | `/rides/count` | No | Conteggio uscite |
| POST | `/rides/analyze` | No | Multi-ride summary |
| POST | `/rides/{id}/analyze` | Yes | Analisi singola |
| GET | `/rides/{id}/report` | Yes | Report testuale |

### Import
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| POST | `/import/gpx` | Yes | Upload GPX |
| POST | `/import/fit` | Yes | Upload FIT |
| POST | `/import/multiple` | Yes | Batch upload |
| GET | `/import/google-fit/auth` | No | URL OAuth Google |
| POST | `/import/google-fit/token` | No | Exchange token |
| POST | `/import/google-fit` | Yes | Import da Google Fit |
| POST | `/import/strava` | Yes | Import da Strava |
| POST | `/import/strava/sync` | Yes | Sincronizza tutte Strava |

### Export
| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/rides/export/json` | Export JSON |
| GET | `/rides/export/csv` | Export CSV |

### Charts
| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/charts/speed/{id}` | Grafico velocita (PNG) |
| GET | `/charts/elevation/{id}` | Grafico elevazione (PNG) |
| GET | `/charts/distance/{id}` | Grafico distanza (PNG) |

### Athletes
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| POST | `/athletes` | Yes | Crea profilo |
| GET | `/athletes` | No | Lista atleti |
| GET | `/athletes/{id}` | Yes | Dettaglio |
| PUT | `/athletes/{id}` | Yes | Aggiorna |
| POST | `/athletes/{id}/metrics` | Yes | Salva metriche |

### Scores & Benchmark
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| GET | `/scores/athlete/{id}` | Yes | Punteggi atleta |
| POST | `/benchmark/compare` | No | Confronto benchmark |

### AI Coach
Integrazione con Groq (LLM) per:
- Raccomandazioni di allenamento personalizzate
- Consigli di recupero basati su fatigue score
- Analisi trend storici
- Chat conversazionale con storico
- Vector DB (PGVector) per RAG avanzato con embedding OpenAI

Dipendenze: `GROQ_API_KEY` e `OPENAI_API_KEY` in `.env`.

#### Knowledge Base senza OpenAI

Se `OPENAI_API_KEY` non ha quota disponibile (HTTP 429), il sistema:
1. **Cache embedding su file**: gli embedding OpenAI sono salvati in `.chroma_db/embeddings_cache.json` e riutilizzati senza chiamate API ripetute.
2. **Circuit breaker con cooldown**: dopo `OPENAI_EMBEDDING_MAX_FAILURES` 429 consecutivi, OpenAI viene disabilitato per `OPENAI_EMBEDDING_COOLDOWN_SECONDS` secondi, poi ritentato in background.
3. **Fallback semantico locale**: se `sentence-transformers` è installato (`pip install sentence-transformers`), viene usato il modello `all-MiniLM-L6-v2` per embedding semantici; altrimenti TF-IDF con normalizzazione L2 e vocabolario condiviso su tutto il corpus.
4. **Log ridotti**: il logger `httpx`/`openai` rispetta `OPENAI_LOG_LEVEL` (default `WARNING`) per evitare spam di DEBUG in produzione.

Configurazioni disponibili in `.env`:

```env
# Log verbosity for openai/httpx
OPENAI_LOG_LEVEL=WARNING

# Circuit breaker cooldown after 429 (seconds)
OPENAI_EMBEDDING_COOLDOWN_SECONDS=300

# Failures before circuit breaker opens
OPENAI_EMBEDDING_MAX_FAILURES=3
```

---

## Integrazioni Esterne

### Strava
- OAuth 2.0 + PKCE authorization flow
- Import attivita ciclistiche con normalizzazione Ride
- Sincronizzazione batch con paginazione
- Storage token SQLite-backed con auto-refresh

### Garmin Connect
- OAuth 2.0 authorization flow
- Import attivita ciclistiche
- Supporto multipli sport type (road, MTB, gravel, virtual)
- Token storage con refresh automatico

### Google Fit
- OAuth2 per import automatico attivita ciclistiche
- Client dedicato con scope configurabile
- Test coverage 100%

---

## Sicurezza Stradale

Modulo `traffic/` per analisi sicurezza percorsi:

- **Safety Analyzer** — Calcolo risk score (0-1) basato su:
  - Tipo di strada (pesi: cycleway 0.9, motorway 0.05)
  - Infrastruttura ciclabile bonus (+15%)
  - Incidenti stradali (penalty per km)
- **Overpass Client** — Query OpenStreetMap per bike lanes e road types
- **Incident Fetcher** — Dati incidenti per area geografica

---

## Phone GPS Tracking

Registrazione uscite direttamente dal telefono Android:

- **BikeTrackingService.kt** — Foreground service con GPS persistente
- **BikeTrackingPlugin.kt** — Plugin Capacitor bridge nativo
- **RideTracking.vue** — Pagina Vue con mappa Leaflet live
- **trackingStore.ts** — Store Pinia stato reattivo
- Scrittura GPX incrementale in background
- Auto-pause rilevamento attivita < 3 km/h
- Supporto sensori BLE (HR, Cadence, Power)

---

## Deployment

### Docker

```bash
docker compose up -d
```

Configurazione hardened:
- Multi-stage build (frontend builder + production)
- Utente non-root (`bikemaster`)
- Read-only filesystem + tmpfs
- No-new-privileges security opt
- Health check automatico

### Docker Compose

```bash
docker compose up -d
docker compose logs -f
```

### Azure (azd)

```bash
azd up
```

### Render

```bash
render deploy
```

### GitHub Actions

CI/CD con 5 jobs:
- **test** — pytest + coverage → Codecov
- **lint** — ruff + mypy
- **frontend** — npm build
- **security** — Trivy vulnerability scan → CodeQL
- **build** — Docker build (dipende da tutti gli altri)

### Android Release

Workflow separato per build APK/AAB.

---

## Sviluppo

### Architettura Clean

```
core/           → Domain entities (GPSPoint, Ride, AthleteProfile, FitnessState)
backend/auth/   → Authentication providers
backend/events/ → Domain events
backend/traffic/→ Traffic safety analysis
backend/api/    → FastAPI routes + schemas
backend/db/     → Data access (sync + async)
backend/analytics/calculators/     → Pure metric functions
backend/analytics/services/        → Use case orchestration
backend/analytics/repositories/    → Data access abstraction
```

### Aggiunta endpoint

1. Aggiungi handler in `api/routes.py`
2. Aggiungi DTO in `api/schemas.py` se serve
3. Aggiungi test in `tests/`

### Convenzioni

- Nomi moduli in `snake_case`
- Type hints obbligatori
- Import lazy nelle route per evitare circular dependency
- Logging tramite `utils.logger.get_logger(__name__)`
- DB access tramite context manager o repository pattern
- Analytics: funzioni pure in `calculators/`, orchestrazione in `services/`

---

## Testing

```bash
pytest
```

Suite di 51+ test automatici:
- Unit test modelli e parsing
- Test API coverage
- Mock Google Maps / Strava / Garmin
- Power model e performance engine
- Benchmark
- Knowledge base
- AI Coach API
- Database backup
- Import batch
- Athlete profile
- Event bus
- Traffic client
- Repositories (sync + async)
- Analytics engine
- Core pipeline
- Google OAuth
- Vector DB
- Security
- Error paths

### Coverage: ~79%

---

## Roadmap

Stato progetto: **Late Beta / Early Production** — 145/145 base + 63/80 estensioni completate.

### Fasi completate

| # | Fase | Status |
|:---:|---|---|
| 1 | Fondamenta | ✅ |
| 2 | Analisi percorso | ✅ |
| 3 | Database | ✅ |
| 4 | Profilo atleta | ✅ |
| 5 | Performance engine | ✅ |
| 6 | Benchmark | ✅ |
| 7 | Knowledge Base | ✅ |
| 8 | AI Coach | ✅ |
| 9 | Google Fit | ✅ |
| 10 | Strava | ✅ |
| 11 | Garmin Connect | ✅ |
| 12 | Tracciamento Telefono (Android) | ✅ |
| 13 | Traffic Safety | ✅ |
| 14 | Architettura Clean | ✅ |
| 15 | Event Bus | ✅ |
| 16 | Vector DB (PGVector) | ✅ |
| 17 | UI/UX (Dashboard + PWA) | ✅ |
| 18 | Deployment (Docker + CI/CD) | ✅ |
| 19 | Testing & DevOps | 🔄 Parziale |
| 20 | Multi-utente + Tenant Isolation | ✅ |
| 21 | Deployment & Distribuzione | 🔄 In corso |
| 22 | Phone GPS Tracking Android | 🔄 Parziale |
| 23 | Event-Driven & Clean Architecture | 🔄 Parziale |
| 24 | Vector DB & AI RAG Avanzato | 🔄 Parziale |
| 25 | Frontend Testing & PWA | 🔄 In corso |

### Priorità — Prossimi 3-6 mesi

| Priorità | Miglioramento | Impatto | Difficoltà |
|:---:|---|---|:---:|
| **1** | Frontend testing suite attiva (Vitest + Playwright E2E) | Molto alto | Media |
| **2** | PostgreSQL in produzione + connection pooling | Alto | Media |
| **3** | Anomaly detection uscite + Weekly/Monthly training plan LLM | Alto | Media |
| **4** | iOS mobile app (Capacitor iOS) | Alto | Media |
| **5** | PWA completa + offline support | Alto | Media |
| **6** | Ruff + mypy + pre-commit linting | Medio-Alto | Bassa |
| **7** | Coverage test >90% | Medio | Alta |

---

## Contribuire

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/awesome`)
3. Commit modifiche (`git commit -m 'feat: aggiungi feature'`)
4. Push al branch (`git push origin feature/awesome`)
5. Apri Pull Request

---

## License

MIT - Vedi file LICENSE per dettagli.
