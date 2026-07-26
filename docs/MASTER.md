# BikeMaster — Complete Documentation

> **Version:** 1.5.0  
> **Date:** 2026-07-12  
> **Stack:** Python 3.11 · FastAPI · Vue 3 · TypeScript · SQLite/PostgreSQL · Tauri 2 · Clean Architecture

For topic-specific documentation, see [docs/README.md](./README.md).

### Piattaforma primaria (effective 2026-07-15)

**Tauri 2 desktop** (`.exe`/`.dmg`/`.AppImage`) — Rust + WebView, frontend Vue 3 bundle inside WebView, backend FastAPI embedded su `localhost`, SQLite come database primario locale. PWA supportata per utenti web-only. PostgreSQL opzionale per cloud sync/community.

Vedi anche [docs/ARCHITECTURE.md](./ARCHITECTURE.md) per Clean v2.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Features](#2-features)
3. [Tech Stack](#3-tech-stack)
4. [Architecture](#4-architecture)
5. [Project Structure](#5-project-structure)
6. [Data Models](#6-data-models)
7. [API Reference](#7-api-reference)
8. [Analytics Engine](#8-analytics-engine)
9. [AI Coach & Knowledge Base](#9-ai-coach--knowledge-base)
10. [Frontend](#10-frontend)
11. [Testing](#11-testing)
12. [External Integrations](#12-external-integrations)
13. [Security & Monitoring](#13-security--monitoring)
14. [Phone GPS Tracking](#14-phone-gps-tracking)
15. [Traffic Safety Analysis](#15-traffic-safety-analysis)
16. [Deployment](#16-deployment)
17. [Configuration](#17-configuration)
18. [Roadmap](#18-roadmap)
19. [Changelog](#19-changelog)
20. [Contributing](#20-contributing)

---

## 1. Overview

**BikeMaster** is a **lifestyle health intelligence** system. It defines health state as the dynamic balance of variables acquired from real life, and uses structured physical activity — starting with cycling — as the primary domain for analysis, recommendations, and optimization.

> **Official Mission:** The program defines health state as the balancing of variables acquired from your lifestyle. You choose what to eat, it analyzes, advises compatible quantities, proposes micro-corrections, and gives you the right amount of movement to maintain balance. We are similar in biology, but different in life — and the system respects both.

It allows people of all levels to:

- import routes from **GPX / FIT** files or external services (Strava, Garmin, Wahoo, Google Fit);
- analyze performance metrics: distance, speed, elevation, accelerations, pauses;
- estimate **calories** (physics + MET) and calculate a **fatigue score**;
- track health variables (energy, macros, hydration, glucose, VO2, breathing, HR, sleep, stress);
- compare performance with **benchmark** percentiles by category;
- receive personalized advice from an **AI Coach** powered by Groq and a RAG knowledge base;
- visualize routes on interactive maps and dashboards.

**Architecture:** Monolithic modular backend (FastAPI) + standalone frontend (Vue 3 SPA). The backend exposes a REST API under `/api/v1`, serves the built frontend assets, and uses a dual-mode database layer (SQLite for development, PostgreSQL for production).

---

## 2. Features

- **GPS Ingestion** — GPX (gpxpy) and Garmin FIT (fitparse) parsing
- **Route Analysis** — Distance, speed, elevation, accelerations, pause detection
- **Calorie Estimation** — Physics model (aerodynamic drag + rolling resistance) + MET tables
- **Fatigue Scoring** — Weighted 0-10 score with recovery recommendations
- **Interactive Maps** — Speed-colored routes with Folium/Leaflet
- **Knowledge Base** — Sports documents indexed for RAG (BM25 + PGVector)
- **AI Coach** — Training and recovery advice powered by Groq/LLM
- **Google Fit** — Automatic cycling activity import
- **Google Maps** — Static maps with API key support
- **Strava** — OAuth2 + PKCE connect from the dashboard, batch activity import & sync
- **Garmin Connect** — OAuth2 activity synchronization
- **Wahoo Fitness** — Cycling activity import
- **Calendar** — Training event planning
- **Web Dashboard** — Dark-themed UI with statistics and ride list (Vue 3 + Vite + TypeScript)
- **GPS Heatmap** — Route density visualization
- **Badges System** — Medals and achievements
- **Granfondo Planner** — Training plan generator with tapering
- **Weather Service** — Training weather advice
- **Training Stress** — TSS, ATL/CTL/TSB, EWMA
- **Traffic Safety** — Route safety analysis (cycling infrastructure, incidents)
- **Event Bus** — Domain event system (RideCreated, BadgeEarned, etc.)
- **PWA** — Progressive Web App with install prompt
- **Phone GPS Tracking** — Record rides directly from Android mobile
- **REST API** — 40+ documented endpoints
- **Export** — JSON and CSV
- **JWT Auth** — Login and endpoint protection
- **Google OAuth2** — Social login
- **Rate Limiting** — Per-IP API protection
- **Background Tasks** — Async queue for heavy operations
- **Redis Cache** — Caching with graceful fallback
- **AetherMap** — R&D cartographic engine (cube-sphere + S2/H3, WebGL rendering, digital twin)
- **Voice Commands** — 35+ Italian voice commands (Web Speech API) for navigation, nutrition, tracking, BM2
- **Geo Pipeline** — OSM + terrain enrichment for GPS routes (surface, highway, DEM, slope, GeoJSON)
- **Health Connect** — Android Health Connect + BLE sync (weight, HR, steps, exercise, height, body fat)

## BikeMaster 2.0 — Deluxe Simulation

> **Location:** `bike_analyzer/bm2/`
> **Docs:** `docs/BM2_*.md`
> **Status:** Production-ready simulation engine with what-if analysis

BM2 is BikeMaster's sport simulation engine. It provides:

- **Type-safe algorithms** with dimensional analysis (`Quantity` + `UnitRegistry`)
- **What-if simulation** — modify weight, bike, slope, wind and see impact on performance
- **Knowledge Layer** — fitness state, fatigue, recovery, route difficulty predictions
- **AI Coach integration** — answers based exclusively on Knowledge Layer data

### Core Components

| Component | Location | Purpose |
|---|---|---|
| Models | `bm2/models.py` | Athlete, Bike, Activity, WorldObject, AnalysisContext |
| Algorithms | `bm2/algorithms/` | 9 algorithms (Movement, Energy, Power, Fatigue, etc.) |
| Simulation | `bm2/simulation.py` | Scenario overrides, sensitivity analysis, presets |
| Knowledge | `bm2/knowledge.py` | Fitness, fatigue, recovery, route difficulty |
| Adapters | `bm2/adapters.py` | Bridge between existing domain and BM2 |
| Orchestrator | `bm2/orchestrator.py` | Multi-algorithm execution |
| Agents | `bm2/agents.py` | AI Coach orchestrator with RAG |

### Key Algorithms

| Algorithm | Output | Unit |
|---|---|---|
| MovementModel | avg/max speed, acceleration | m/s |
| EnergyModel | Calories | kcal |
| PowerModel | Estimated/sustainable power | W |
| FatigueModel | Fatigue score + recovery hours | score (0-10) |
| PerformanceModel | Normalized performance index | score |
| RouteDifficultyModel | Route difficulty score | score (0-100) |
| RecoveryModel | Readiness score | score (0-100) |
| NutritionModel | Carbs, water, proteins | g / L |
| TrainingLoadModel | TSS, CTL, ATL, TSB | score |

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/bm2/simulate-ride` | Run what-if simulation on ride |
| POST | `/api/v1/bm2/simulate-preset` | Run preset scenario |
| GET | `/api/v1/bm2/models` | List available algorithms |

### Documentation

See `docs/BM2_ENGINE_ARCHITECTURE.md`, `docs/BM2_ALGORITHMS.md`, `docs/BM2_TESTING_STRATEGY.md`, and `docs/BM2_INTEGRATION_GUIDE.md` for complete specifications.

---

## AetherMap (R&D Project)

`aethermap/` is an **independent** R&D cartographic engine: world-from-scratch cartography (cube-sphere + S2/H3), "world database" data model, AI "researcher" pipeline, WebGL rendering, digital twin. Shares the stack (Vue + FastAPI) but is **not imported** by the BikeMaster backend.

- **Phases:** 1 (earth model) → 2 (data model) → {3 AI, 4 rendering} → 5 (digital twin).
- **Key decisions:** web+Python hardware; adaptive LOD per zone; real-time digital twin with eventual consistency; GeoJSON/3D Tiles/CityGML interoperability; S2 primary (geometry/LOD), H3 for analysis; per-object retention (`stale_after`).
- **Code:** `aethermap/src/aethermap/` (`core/coordinates.py`, `ai/`, `render/`, `twin/`).
- **Demo:** `cd aethermap/src && python -m aethermap.ai.demo|.render.demo|.twin.demo`.
- **Agent docs:** `.kilo/agent/aethermap-*.md`. Do not remove without explicit consent.

---

## 3. Tech Stack

### Backend

| Layer | Technology |
|---|---|
| **Framework** | FastAPI 0.110+ |
| **Language** | Python 3.11+ |
| **Server** | Uvicorn |
| **Config** | Pydantic Settings v2 |
| **Database (dev)** | SQLite (sync) |
| **Database (prod)** | PostgreSQL + asyncpg |
| **ORM** | SQLAlchemy 2.0 (async + sync) |
| **Migrations** | Alembic |
| **Vector DB** | PGVector (cosine similarity) with TF-IDF / sentence-transformers fallback |
| **Analytics** | NumPy, Pandas, Matplotlib, SciPy, scikit-learn, statsmodels, endurance-metrics |
| **GPS Parsing** | gpxpy (GPX), fitparse (Garmin FIT) |
| **AI/LLM** | Groq SDK (only active AI key: `GROQ_API_KEY`); local embeddings via sentence-transformers (`all-MiniLM-L6-v2`) |
| **Auth** | python-jose (JWT HS256), passlib, bcrypt, Google/Strava/Garmin OAuth2 |
| **Rate limiting** | slowapi (proxy-aware, per-IP) |
| **Cache** | Redis 7 (optional, graceful in-memory fallback) |
| **Observability** | Sentry, Prometheus + Grafana + Alertmanager, OpenTelemetry/Zipkin tracing |
| **Security** | CSP, HSTS, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy |

### Frontend

| Layer | Technology |
|---|---|
| **Framework** | Vue 3 (Composition API + `<script setup>`) |
| **Language** | TypeScript (`strict: true`) |
| **Build** | Vite 5 |
| **State** | Pinia |
| **Router** | Vue Router 4 |
| **Charts** | Chart.js |
| **Maps** | Leaflet (+ heatmap plugin) |
| **PWA** | vite-plugin-pwa + custom `sw.js` |
| **Mobile** | Capacitor 5 (Android + iOS) |
| **Testing** | Vitest (unit) + Playwright (E2E) |
| **Lint/Typecheck** | ESLint + vue-tsc |

---

## 4. Architecture

BikeMaster follows **Clean Architecture** with four distinct layers. The primary distribution is **Tauri 2 desktop** (Rust + WebView) with embedded FastAPI backend and SQLite as the local-first primary store.

```
Presentation      API (FastAPI) · Frontend Vue · Android/iOS (Capacitor) · Tauri 2 (desktop)
        │
Application       Use cases: StartSession, PromoteSession, ImportActivity,
                  AnalyzeActivity, SyncHealth, CoachAdvise, PlanTraining
        │
Domain            Entities + UnifiedMetricsEngine (pure calculation logic)
        │
Infrastructure    Repositories · Ingestion (Strava/Garmin/Fit/GPX) ·
                  Tracking · Maps · Weather · Traffic · VectorDB
```

Dependencies point only inward. The `Application` layer orchestrates; the `Domain` layer calculates; the `Infrastructure` layer persists/retrieves.

> **Local-first (effective 2026-07-15):** the device is the source of truth. SQLite is the primary database for every user. PostgreSQL is optional/cloud-only for sync and community features. Users can run "Mai" (never sync) and use the app 100% offline. See §2 and §6 for details.

### Domain Layer (`core/`)

Pure Python dataclasses and logic independent of any infrastructure:

- **`models.py`** — Domain entities: `GPSPoint`, `Segment`, `Pause`, `Ride`, `AthleteProfile`, `CalendarEvent`, `RouteStatistics`
- **`session.py`** — `SessionData`: live/background stream (GPS + sensors + context)
- **`pipeline.py`** — `AnalysisPipeline`: orchestrates GPS processing → metric computation
- **`engine.py`** — `AnalysisEngine`: main orchestrator with `FitnessStateVector`
- **`fitness_state.py`** — `FitnessStateVector`: physiological state snapshot (CTL/ATL/TSB)
- **`validators.py`** — Business validators
- **`validation.py`** — Validation error classes
- **`calculators/`** — Pure metric functions: calories, power, fatigue, performance, stress

### Analytics Layer (`analytics/`)

Clean Architecture structure:

- **`calculators/`** — Pure functions testable in isolation
- **`services/`** — Use case orchestration (ride analysis, fitness state computation, context builder)
- **`repositories/`** — Data access abstraction (ride, athlete, fitness state, training stress)

### Infrastructure Layer

- **`db/`** — Data access: SQLite sync, async SQLAlchemy (asyncpg/aiosqlite), PostgreSQL ORM
- **`database/vectordb.py`** — PGVector wrapper for similarity search
- **`traffic/`** — Road safety analysis (Overpass API, incident data)
- **`auth/`** — OAuth2 providers (Google, Strava, Garmin, Wahoo)
- **`ingestion/`** — External data sources (GPX/FIT parser, Google Fit, Strava, Garmin, Wahoo)
- **`maps/`** — Map rendering (Folium, Google Static Maps, OSM, SerpApi)
- **`weather/`** — Weather service
- **`events/`** — Domain event bus (pub/sub)
- **`utils/`** — Date helpers, logging config

### Presentation Layer

- **`api/`** — FastAPI routes, schemas, app factory (CORS, rate limit, security headers, observability)
- **`frontend/`** — Vue 3 + Vite + TypeScript standalone SPA
- **`static/`** — Built frontend assets served by FastAPI (SPA fallback)

### Key Patterns

- **Pure calculators**: no DB, no API, no side effects
- **Service orchestration**: use case flow in `analytics/services/`
- **Repository abstraction**: sync + async + PostgreSQL adapters
- **Domain events**: pub/sub for RideCreated, AthleteUpdated, BadgeEarned, TrainingGenerated
- **Dual-mode DB**: repository adapters handle both SQLite and PostgreSQL

---

## 5. Project Structure

```
bike_analyzer/
├── __init__.py
├── main.py                          # Unified CLI entrypoint (api | web | cli)
├── core/                            # Domain layer
│   ├── models.py                    # GPSPoint, Segment, Pause, Ride, AthleteProfile...
│   ├── session.py                   # SessionData (live/background GPS+sensors)
│   ├── engine.py                    # AnalysisEngine orchestrator
│   ├── fitness_state.py             # FitnessStateVector: CTL/ATL/TSB snapshot
│   ├── pipeline.py                  # AnalysisPipeline: GPS → processing → metrics
│   ├── validators.py                # Business validators
│   ├── validation.py                # Validation error classes
│   └── calculators/                 # Pure metric functions
│       ├── calories.py
│       ├── power.py
│       └── ...
├── backend/
│   ├── settings.py                  # Pydantic Settings v2 (centralized config)
│   ├── security.py                  # JWT auth + security headers
│   ├── rate_limiter.py              # slowapi rate limiter
│   ├── redis_client.py              # Async Redis client + cache decorator
│   ├── task_queue.py                # Async background task queue
│   ├── event_bus.py                 # Domain event pub/sub
│   ├── audit_log.py                 # Admin audit log (JSONL)
│   ├── api/                         # FastAPI Presentation Layer
│   │   ├── app_factory.py           # FastAPI factory + CORS + rate limit + security + observability
│   │   ├── routes.py                # 40+ API endpoints
│   │   ├── schemas.py               # Pydantic DTOs
│   │   ├── bm2_routes.py            # BM2 subsystem routes
│   │   └── utils.py                 # API helpers
│   ├── analytics/                   # Analytics Engine (Clean Architecture)
│   │   ├── analytics.py             # Summary, export, report, charts
│   │   ├── advanced.py              # 14 advanced mathematical models
│   │   ├── power_model.py           # NP, IF, TSS, CP, FTP, decoupling
│   │   ├── calories.py              # Physics + MET calorie estimation
│   │   ├── fatigue.py               # Fatigue + recovery
│   │   ├── performance.py           # Performance/Endurance/Efficiency scores
│   │   ├── training_stress.py       # TSS + EWMA
│   │   ├── ai_coach.py              # AI Coach (Groq + RAG + memory)
│   │   ├── knowledge_base.py        # RAG engine (BM25 + LRU cache)
│   │   ├── training_plan_generator.py
│   │   ├── anomaly_detection.py
│   │   ├── multi_classifier.py
│   │   ├── vip_predictor.py
│   │   ├── inactivity_estimator.py
│   │   ├── ride_route_estimator.py
│   │   ├── calculators/             # Pure functions (reused by core/)
│   │   ├── services/                # Use case orchestration
│   │   └── repositories/            # Data access abstraction
│   ├── auth/                        # OAuth2 providers
│   ├── db/                          # Data access layer (sync + async)
│   ├── database/                    # Vector DB
│   ├── events/                      # Domain events
│   ├── ingestion/                   # GPS parsers + external APIs
│   ├── maps/                        # Map rendering
│   ├── traffic/                     # Traffic safety analysis
│   ├── weather/                     # Weather service
│   ├── models/                      # Domain dataclasses (sync with core/)
│   ├── processing/                  # GPS data processing
│   ├── static/                      # Backend-served static assets (SPA build)
│   └── utils/
├── frontend/                        # Vue 3 + Vite + TypeScript SPA
│   ├── src/
│   │   ├── main.ts                  # App bootstrap
│   │   ├── App.vue                  # Root shell + overlay auth
│   │   ├── router/index.ts          # Guard auth, sync localStorage
│   │   ├── stores/                  # Pinia state management
│   │   ├── components/              # 30 Vue components
│   │   ├── views/                   # Page views
│   │   ├── composables/             # useRides, useToast, usePWA, useI18n, useChart
│   │   ├── utils/                   # API client & utilities
│   │   └── plugins/                 # Capacitor native bridge
│   ├── android/                     # Android app (Kotlin + Capacitor)
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── vitest.config.js
│   └── playwright.config.js
├── tests/                           # 98 pytest files
├── knowledge_base/                  # RAG documents (Markdown)
├── docs/                            # Developer documentation
├── docker/                          # Container & deploy configs
├── alembic/                         # DB migrations
├── prometheus/                       # Metrics & alerts config
├── main.py                          # Unified entrypoint (api | web | cli)
├── requirements.txt
├── pyproject.toml
├── Dockerfile                       # Multi-stage hardened build
├── docker-compose.yml
├── .env.example
├── README.md
├── CHANGELOG.md
├── ROADMAP.md
└── PROJECT_STATUS.md
```

---

## 6. Data Models

### Core Entities

| Entity | Description |
|---|---|
| `GPSPoint` | Single GPS reading: lat, lon, timestamp, altitude, speed, power, hr, cadence |
| `Segment` | Consecutive points between pauses/accelerations |
| `Pause` | Detected stop (speed < threshold for > duration) |
| `Ride` | Completed cycling session (superset: `Activity`) |
| `AthleteProfile` | User profile: name, age, weight, height, FTP, goals, equipment |
| `FitnessStateVector` | CTL/ATL/TSB snapshot + recovery + recommendations |
| `SessionData` | Live/background stream: GPS + sensors + context |
| `CalendarEvent` | Planned training event |
| `RouteStatistics` | Aggregated route stats |

### Database Tables

| Table | Purpose |
|---|---|
| `rides` | Cycling sessions (JSON GPS points) |
| `athletes` | Athlete profiles |
| `metrics` | Calculated per-ride metrics |
| `chat_history` | AI Coach conversational memory |
| `calendar_events` | Planned training events |
| `strava_tokens` | Strava OAuth tokens |
| `garmin_tokens` | Garmin OAuth tokens |
| `wahoo_tokens` | Wahoo OAuth tokens |
| `kb_embeddings` | Vector embeddings for PGVector RAG |

### Ride Model

```python
@dataclass
class Ride:
    id: Optional[int]
    athlete_id: Optional[int]
    date: str                        # ISO format YYYY-MM-DD
    distance_km: float
    duration_minutes: float
    avg_speed_kmh: float
    weight_kg: float = 70.0
    calories: float = 0.0
    heart_rate_avg: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    gps_points: Optional[list[dict]] = None   # serializzati JSON nella colonna DB
    created_at: Optional[str] = None
    @property
    def duration_hours(self) -> float: ...
```

### AthleteProfile Model

```python
@dataclass
class AthleteProfile:
    id: Optional[int]
    name: str
    age: int = 30
    weight_kg: float = 70.0
    height_cm: Optional[float] = None
    fat_percentage: Optional[float] = None
    years_active: int = 1
    weekly_sessions: int = 3
    monthly_hours: float = 0.0
    annual_hours: float = 0.0
    experience_level: str = "Beginner"   # Beginner|Amateur|Intermediate|Advanced|Elite
    goals: Optional[str] = None
    preferred_terrain: Optional[str] = None
    weekly_volume_km: Optional[float] = None
    best_segments: Optional[str] = None
    medical_notes: Optional[str] = None
    equipment: Optional[str] = None
```

---

## 7. API Reference

**Base URL:** `http://localhost:8000/api/v1`

### Health & Auth

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Basic health check |
| GET | `/health/redis` | No | Redis health check |
| GET | `/health/detailed` | No | Detailed health + DB stats |
| POST | `/auth/login` | No | JWT login (form-urlencoded) |
| POST | `/auth/register` | No | User registration |
| GET | `/auth/google` | No | Google OAuth URL |
| POST | `/auth/google/callback` | No | Google token exchange |
| GET | `/auth/me` | Yes | Current user profile |

### Rides CRUD

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/rides` | Yes | Create ride |
| GET | `/rides` | No | List rides (paginated, sortable) |
| GET | `/rides/{id}` | Yes | Ride detail + analytics |
| PUT | `/rides/{id}` | Yes | Update ride |
| DELETE | `/rides/{id}` | Yes | Delete ride |
| GET | `/rides/count` | No | Ride count |
| POST | `/rides/analyze` | No | Multi-ride summary |
| POST | `/rides/{id}/analyze` | Yes | Single ride analysis |
| GET | `/rides/{id}/report` | Yes | Text report |

### Import

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/import/gpx` | Yes | GPX upload |
| POST | `/import/fit` | Yes | FIT upload |
| POST | `/import/multiple` | Yes | Batch upload |
| GET | `/import/google-fit/auth` | No | Google Fit OAuth URL |
| POST | `/import/google-fit/token` | No | Google Fit token exchange |
| POST | `/import/google-fit` | Yes | Import from Google Fit |
| GET | `/import/strava/auth` | Yes | Strava OAuth URL (PKCE) |
| POST | `/import/strava/callback` | Yes | Strava token exchange |
| POST | `/import/strava/sync` | Yes | Sync all Strava activities |
| DELETE | `/import/strava/disconnect` | Yes | Disconnect Strava |

### Export

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/rides/export/json` | No | JSON export |
| GET | `/rides/export/csv` | No | CSV export |

### Charts

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/charts/speed/{id}` | Yes | Speed chart PNG |
| GET | `/charts/elevation/{id}` | Yes | Elevation chart PNG |
| GET | `/charts/distance/{id}` | Yes | Distance chart PNG |
| GET | `/charts/duration` | Yes | Duration chart PNG |

### Maps

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/rides/{id}/map` | Yes | Folium interactive map HTML |
| GET | `/rides/{id}/map/google` | No | Google Static Maps PNG |
| GET | `/maps/places/nearby` | No | Nearby places |
| GET | `/maps/places/search` | No | Search places |

### Athletes

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/athletes` | Yes | Create profile |
| GET | `/athletes` | No | List athletes |
| GET | `/athletes/{id}` | Yes | Athlete detail |
| PUT | `/athletes/{id}` | Yes | Update athlete |
| POST | `/athletes/{id}/metrics` | Yes | Save metrics |

### Scores & Benchmark

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/scores/athlete/{id}` | Yes | Athlete scores |
| POST | `/benchmark/compare` | No | Benchmark comparison |

### AI Coach

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/coach/workout?athlete_id=` | Yes | Workout recommendations |
| GET | `/coach/recovery?fatigue_score=&ride_id=` | No | Recovery recommendations |
| GET | `/coach/trends` | Yes | Historical trends |
| GET | `/coach/full?athlete_id=` | Yes | Full report + charts |
| POST | `/coach/chat` | No | Conversational chat |
| GET | `/coach/history?athlete_id=` | No | Chat history |

### Training

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/training/load` | Yes | Training load (RSS/TSS) |
| GET | `/training/status` | Yes | Training status |
| GET | `/training/summary` | Yes | Training summary |
| GET | `/training/goals` | Yes | Training goals |
| GET | `/training/workouts/generate` | Yes | Generate workout |
| GET | `/training/granfondo/plan` | Yes | Granfondo plan |

### Weather

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/weather?lat=&lon=` | No | Current weather |
| GET | `/weather/forecast?lat=&lon=&days=` | No | Weather forecast |

### Traffic Safety

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/traffic/analyze` | No | Route safety analysis |
| GET | `/traffic/bike-lanes?lat=&lon=&radius=` | No | Fetch bike lanes |
| GET | `/traffic/road-data?lat=&lon=&radius=` | No | Fetch road data |

### Admin

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/admin/stats` | No | System stats |
| GET | `/admin/backup` | Yes | Database backup |
| POST | `/admin/indexes` | No | Create DB indexes |
| POST | `/admin/reset-demo` | No | Reset demo data |
| GET | `/admin/audit-logs` | Yes | Recent audit entries |

---

## 8. Analytics Engine

### Power Metrics
- Normalized Power (NP) — Coggan rolling average 30s
- Intensity Factor (IF) — NP / FTP
- Variability Index (VI) — NP / avg power
- Efficiency Factor (EF) — NP / avg HR
- Training Stress Score (TSS) — IF² × duration × 100
- Power Zones — Coggan 7-zone model
- Power Profile — Best efforts 5s/1min/5min/20min
- FTP Estimation — 20min test × 0.95
- Critical Power / W′
- Aerobic Decoupling — 5%+ threshold

### Training Load
- TSS, ATL/CTL/TSB (EWMA)
- Monotony / Strain
- Weekly / Monthly TSS

### Fatigue & Recovery
- Fatigue score 0-10 (weighted: duration 30%, HR% 30%, speed 20%, elevation 10%, weight 10%)
- Recovery hours estimator (8/16/24/48h)

### 14 Advanced Models
1. Pace Consistency
2. Power Estimate (physics)
3. Climb Classifier (Tour de France style)
4. VO2max Estimation
5. Route Difficulty (multi-factor)
6. Elevation Profile + hardship index
7. Speed Profile (accelerations/coasting)
8. Progress Trend (linear regression)
9. Training Stress Balance
10. Ideal Weight (power-to-weight)
11. HR Zones (5-zone)
12. Garmin Power Factor
13. Ride Recommendation
14. Speed Surge Detection

### Calorie Estimation
- Physics model: rolling resistance + aerodynamic drag + gravity + neuromuscular efficiency (25%)
- MET table fallback
- Benchmark: 30 kcal/km

---

## 9. AI Coach & Knowledge Base

### Knowledge Base
- 7 Markdown documents in `knowledge_base/` (~250 lines)
- BM25 search engine with k1=1.5, b=0.75
- LRU cache keyed on directory mtime
- Chunking: max 1200 chars, overlap 200
- Local embeddings via sentence-transformers (`all-MiniLM-L6-v2`) or TF-IDF fallback

### AI Coach
- Groq LLM integration (only active AI key required)
- Context: athlete profile + scores + RAG results + chat memory
- Conversational memory in `chat_history` DB table
- Output in Italian by default

---

## 10. Frontend

### Architecture
- **Vue 3** Composition API with `<script setup>`
- **TypeScript** strict mode
- **Pinia** for state management
- **Vue Router 4** with auth guards
- **Vite 5** build tool
- **PWA** via vite-plugin-pwa + custom `sw.js`

### Key Stores
- `auth.ts` — JWT, user, token validation, login/logout
- `ui.ts` — theme, language, oauthLoading
- `trackingStore.ts` — live GPS tracking state

### Native Mobile
- **Android**: Kotlin foreground service (`BikeTrackingService.kt`) + Capacitor plugin + Health Connect + BLE sensors (`HealthConnectManager.kt`, `BleManager.kt`)
- **iOS**: Swift plugin (`BikeTrackingPlugin.swift`) + Capacitor config

### Voice Commands
- **35+ Italian commands** via Web Speech API for navigation, nutrition (with kcal estimation + calendar auto-create + metabolism recalculation), tracking, BM2 simulation, and UI control.

---

## 11. Testing

### Backend
- **98 pytest files** covering unit, integration, API, and error paths
- Run: `pytest` or `pytest --cov=bike_analyzer --cov-report=term`
- Frameworks: pytest, pytest-asyncio, pytest-cov

### Frontend
- **Vitest**: `npm run test` (321 tests)
- **Playwright**: `npm run test:e2e` or `npm run e2e:local`
- Frameworks: Vitest, @vue/test-utils, Playwright

---

## 12. External Integrations

### Strava
- OAuth 2.0 + PKCE (popup flow)
- Connect from dashboard (`ImportPanel.vue`)
- Batch sync with pagination
- Token storage: `strava_tokens` table with auto-refresh

### Garmin Connect
- OAuth 2.0 authorization
- Activity fetch + normalization
- Token storage with refresh

### Wahoo Fitness
- Activity import client
- Automatic parsing

### Google Fit
- OAuth 2.0 authorization
- Cycling activity import

### Google Maps
- Static Maps API for route images
- Elevation data

---

## 13. Security & Monitoring

- **JWT Auth**: HS256 with python-jose, bcrypt passwords, key rotation (`SECRET_KEY_PREVIOUS`)
- **Rate Limiting**: slowapi per-IP + proxy-aware (`X-Forwarded-For`)
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy
- **CORS**: configurable origins, wildcard forbidden in production
- **Audit Logging**: JSONL persistence, `/admin/audit-logs` endpoint
- **Sentry**: error tracking (optional via `SENTRY_DSN`)
- **Prometheus**: `/metrics` endpoint via `prometheus-fastapi-instrumentator`
- **Grafana**: dashboard provisioning in `docker/`
- **OpenTelemetry**: distributed tracing (gRPC OTLP → Zipkin)
- **Docker Hardened**: multi-stage build, non-root user, read-only fs, no-new-privileges, healthcheck

---

## 14. Phone GPS Tracking

- **Android**: Kotlin foreground service (`BikeTrackingService.kt`) + Capacitor plugin + Health Connect (`HealthConnectManager.kt`) + BLE sensors (`BleManager.kt`)
- **iOS**: Swift plugin (`BikeTrackingPlugin.swift`) + Capacitor config
- Live tracking via `RideTracking.vue` + `trackingStore.ts`
- Incremental GPX writing in background
- Auto-pause detection < 3 km/h
- BLE sensor support (HR, Cadence, Power) + Health Connect (weight, HR, steps, exercise, height, body fat)

---

## 15. Traffic Safety Analysis

- **Safety Analyzer** — Risk score computation (0-1) based on road type weights, cycling infrastructure bonus, incidents penalty
- **Overpass Client** — OpenStreetMap queries for bike lanes and road types
- **Incident Fetcher** — Area incident data

---

## 16. Deployment

### Docker
```bash
docker compose up -d
```

### Render
- `render.yaml` present

### Fly.io
- See `docker/deploy/flyio.md`

### Railway
- See `docker/deploy/railway.md`

### Vercel
- See `docker/deploy/vercel.md`

### Kubernetes
- Helm chart at `docker/helm/bikemaster/`

---

## 17. Configuration

Key environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./rides.db` | Database connection |
| `DATABASE_URL_ASYNC` | `sqlite+aiosqlite:///./rides.db` | Async engine URL |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `SECRET_KEY` | *(required in prod)* | JWT signing key (32+ chars) |
| `SECRET_KEY_PREVIOUS` | — | Previous key for rotation |
| `ENVIRONMENT` | `development` | Environment mode |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `GROQ_API_KEY` | — | Groq LLM API key |
| `REDIS_URL` | — | Redis connection URL |
| `SENTRY_DSN` | — | Sentry error tracking |
| `STRAVA_CLIENT_ID` | — | Strava OAuth client ID |
| `STRAVA_CLIENT_SECRET` | — | Strava OAuth secret |
| `STRAVA_REDIRECT_URI` | `http://localhost:8000/api/v1/import/strava/callback` | Strava callback |
| `GARMIN_CONSUMER_KEY` | — | Garmin OAuth key |
| `GARMIN_CONSUMER_SECRET` | — | Garmin OAuth secret |
| `GOOGLE_FIT_CLIENT_ID` | — | Google Fit OAuth client ID |
| `GOOGLE_FIT_CLIENT_SECRET` | — | Google Fit OAuth secret |
| `GOOGLE_MAPS_API_KEY` | — | Google Static Maps API key |
| `WEATHER_API_KEY` | — | OpenWeatherMap API key |

---

## 18. Roadmap

Project status: **local-first architecture complete** — desktop Tauri 2 + SQLite primary + embedded FastAPI backend, with active BM2 and AetherMap tracks. For current test counts and endpoint numbers, see [`ROADMAP.md`](ROADMAP.md) and [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

### Completed Phases

| # | Phase | Status |
|:---:|---|---|
| 1 | Foundations | ✅ |
| 2 | Route Analysis | ✅ |
| 3 | Database | ✅ |
| 4 | Athlete Profile | ✅ |
| 5 | Performance Engine | ✅ |
| 6 | Benchmark | ✅ |
| 7 | Knowledge Base | ✅ |
| 8 | AI Coach | ✅ |
| 9 | Google Fit | ✅ |
| 10 | Strava | ✅ |
| 11 | Garmin Connect | ✅ |
| 12 | Wahoo | ✅ |
| 13 | Phone GPS Tracking (Android) | ✅ |
| 14 | Traffic Safety | ✅ |
| 15 | Clean Architecture | ✅ |
| 16 | Event Bus | ✅ |
| 17 | Vector DB (PGVector) | ✅ |
| 18 | UI/UX (Dashboard + PWA) | ✅ |
| 19 | Deployment (Docker + CI/CD) | ✅ |
| 20 | Testing & DevOps | ✅ |
| 21 | Multi-user + Tenant Isolation | ✅ |
| 22 | Frontend Testing & PWA | ✅ |
| 23 | iOS mobile app (Capacitor iOS) | ✅ |

### In Progress

| # | Phase | Status |
|:---:|---|:--:|
| 24 | Anomaly detection + LLM training plan | 🔄 In Progress |
| 25 | Test coverage >90% | 🔄 In Progress |

### Priorities — Next 3-6 Months

| Priority | Improvement | Impact | Difficulty |
|:---:|---|---|:---:|
| **1** | PostgreSQL in production + connection pooling | High | Medium |
| **2** | Voice input/output AI Coach + prompt engineering | High | Medium |
| **3** | Memory persistente conversazioni per utente | High | Medium |
| **4** | Design System + theme tokens | High | Medium |
| **5** | Test coverage >90% come metrica informativa | Medium | Low |
| **6** | Coverage test >90% come metrica informativa | Medium | Low |

---

## 19. Changelog

### v1.6.0 (2026-07-22) — Voice Commands Expansion + Geo Pipeline + Health Connect

**Added**
- **Voice commands expanded to 35+ Italian commands** — new commands in `frontend/src/services/voiceCommands.ts` covering athlete profile updates, calendar, rides, import, analytics, tracking, and UI control.
- **Nutrition voice logging with calendar integration** — `nutrition.log_meal` now auto-creates a calendar event and triggers `metabolism/recalculate`, returning intake/balance summary.
- **Backend Geo/MAP pipeline** (`bike_analyzer/backend/geo/`) — new module with `run_geo_pipeline()` enriching GPS points via OSM (surface, highway), terrain DEM sampling, slope computation, AetherMap worldstore/GeoJSON export.
- **Android Health Connect integration** — new `HealthConnectManager.kt`, `BleManager.kt`, `RunstarBleConnector.kt`/`RunstarDecoder.kt` for weight, heart rate, steps, exercise, height, body fat sync.

**Fixed**
- Audio stop FAB behavior in `VoiceAssistant.vue` and `autoRead` toggle in `CoachPanel.vue`.

### v1.5.0 (2026-07-10) — Milestone: Strava Integration (end-to-end)

**Added**
- **Strava import wired in the web UI** — new *Strava* provider section in `ImportPanel.vue` with **Connect Strava**, **Import from Strava** and **Disconnect Strava** buttons (section shown only when `providers.strava` is true).
- **Connect flow (OAuth2 + PKCE, popup-based)** — frontend opens the Strava authorize URL, polls the redirect for `?code=`, then POSTs `{code, code_verifier}` to `POST /api/v1/import/strava/callback`. No backend GET redirect handler required (same-origin: the API serves the Vue app).
- **`strava` key exposed in `GET /api/v1/import/providers`** so the UI renders only when `STRAVA_CLIENT_ID`/`STRAVA_CLIENT_SECRET` are configured.

**Fixed**
- Frontend bug: post-connect auto-import hung on "Importing your rides..." because `stravaSync()` early-returned while `importing` was still `true`; `importing` is now reset before the auto-sync runs.

### v1.4.1 (2026-07-09)

**Changed**
- Removed legacy `bike_analyzer/backend/config.py` (ROADMAP #234)
- All configuration now flows through `bike_analyzer/backend/settings.py` (`get_settings()`) and `os.getenv`
- Updated 20+ modules: `security.py`, `api/routes.py`, `api/app_factory.py`, `analytics/ai_coach.py`, `analytics/knowledge_base.py`, `analytics/training_plan_generator.py`, `db/database.py`, `db/postgres_db.py`, `database/vectordb.py`, `ingestion/*`, `maps/*`, `weather/weather_service.py`
- Added `secret_key_previous` support in `Settings` for JWT key rotation
- Added `_validate_secret_key` validator to reject placeholder secrets in production
- Updated test suite: `tests/test_config.py` now targets `settings.py`, added `tests/test_no_config_imports.py` (100 tests)

### v1.4.0 (2026-07-06)

**Added**
- Admin audit log module (`bike_analyzer/backend/audit_log.py`) with JSONL persistence
- Admin endpoint `GET /api/v1/admin/audit-logs` for reading recent audit entries
- Audit logging integrated in admin routes: backup, scheduled backup, indexes, stats, reset-demo, CEO analytics
- `tests/test_audit_log.py` (4 tests)
- iOS platform scaffolding: Capacitor iOS config, `BikeTrackingPlugin.swift`, `Info.plist`, `scripts/setup-ios.sh`
- Multi-lingua IT+EN: `LanguageSwitcher.vue`, `useI18n.ts` integration in `App.vue`, expanded `locales/it.json` and `locales/en.json`
- Training plan generator (`analytics/training_plan_generator.py`) with weekly/monthly plans and LLM enhancement
- Anomaly detection module, multi-class ride classifier, VIP predictor, inactivity estimator, ride route estimator
- API endpoints for analytics V2

**Fixed**
- Vitest `requestAnimationFrame` ReferenceError
- Ruff linting configuration
- mypy passes cleanly on `bike_analyzer` package

### v1.3.1 (2026-07-06)

**Added**
- Anomaly detection module, training plan generator, admin audit log
- iOS platform scaffolding
- Multi-lingua IT+EN
- PWA offline UX banner
- Documentation consolidation

**Fixed**
- Frontend test setup mocks
- PostgreSQL production readiness confirmed

### v1.2.1 (2026-06-30)
- Removed hard coverage threshold from pytest configuration
- Coverage now reported as non-blocking informational metric

### v1.2.0 (2026-06-23)
- Frontend authentication with JWT integration
- Tracking controls for GPS ride recording
- Native Android project scaffolding with Kotlin
- PWA install prompt with service worker navigate fix
- Ride tracking updates with live map integration
- Test coverage improvements

### v1.1.0
- Clean Architecture with Core domain layer
- Calculators/Services/Repositories separation
- Domain Events (RideCreated, AthleteUpdated, BadgeEarned, TrainingGenerated)
- Traffic Safety Module
- Strava Integration (OAuth2 + PKCE + batch import)
- Garmin Connect Integration
- Vector Database (PGVector wrapper with TF-IDF fallback)
- Google OAuth2 authentication
- Security hardening (CSP, HSTS, X-Frame-Options, rate limiting)

### v1.0.0
- Initial release: GPX/FIT parsing, performance scoring, benchmark, calorie estimation, charts/maps, TSS, badge system, granfondo planner, weather, knowledge base, AI Coach, Vue 3 frontend, PWA, Android app

---

## 20. Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all tests pass before submitting a PR.

---

*This document is the single source of truth for BikeMaster documentation. For development-specific details, see [docs/DEVELOPMENT.md](./DEVELOPMENT.md). For API-specific details, see [docs/API_DOCS.md](./API_DOCS.md). For roadmap details, see [ROADMAP.md](../ROADMAP.md).*
