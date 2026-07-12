# BikeMaster — Project Documentation

> **Version:** 1.5.0
> **Date:** 2026-07-12
> **Stack:** Python 3.11 · FastAPI · Vue 3 · TypeScript · SQLite/PostgreSQL · Clean Architecture

---

## 1. Overview

**BikeMaster** is a GPS-based cycling performance intelligence system. It allows cyclists of all levels to:

- import routes from **GPX / FIT** files or external services (Strava, Garmin, Wahoo, Google Fit);
- analyze performance metrics: distance, speed, elevation, accelerations, pauses;
- estimate **calories** (physics + MET) and calculate a **fatigue score**;
- compare performance with **benchmark** percentiles by category;
- receive personalized advice from an **AI Coach** powered by Groq and a RAG knowledge base;
- visualize routes on interactive maps and dashboards.

### Architecture

**Monolithic modular** backend (FastAPI) + standalone frontend (Vue 3 SPA). The backend exposes a REST API under `/api/v1`, serves the built frontend assets, and uses a dual-mode database layer (SQLite for development, PostgreSQL for production).

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  Frontend Vue 3 (Vite + TS + Pinia)  │  FastAPI /api/v1    │
│  static/ (served by backend)         │  + SPA fallback      │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│  analytics/services/  │  core/engine.py  │  task_queue.py   │
├─────────────────────────────────────────────────────────────┤
│                    Domain Layer (core/)                      │
│  models.py  │  pipeline.py  │  fitness_state.py  │  session.py│
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                      │
│  db/  │  database/  │  repositories/  │  traffic/  │  auth/ │
│  ingestion/  │  maps/  │  weather/  │  events/  │  utils/   │
└─────────────────────────────────────────────────────────────┘
```

### Patterns

- **Clean Architecture**: Domain → Application → Infrastructure → Presentation
- **Pure calculators** in `analytics/calculators/` (no DB/API/side effects)
- **Service orchestration** in `analytics/services/`
- **Repository abstraction** in `analytics/repositories/`
- **Domain events** pub/sub in `events/`
- **Dual-mode DB** via repository adapters (sync SQLite + async SQLAlchemy + PostgreSQL)

---

## 3. Tech Stack

### Backend

| Component | Technology | Version |
|---|---|---|
| Framework | FastAPI | >= 0.110.0 |
| Language | Python | >= 3.11 |
| Server | Uvicorn | — |
| Config | Pydantic Settings v2 | >= 2.0.0 |
| Database (dev) | SQLite | built-in |
| Database (prod) | PostgreSQL + asyncpg | — |
| ORM | SQLAlchemy 2.0 | >= 2.0.27 |
| Migrations | Alembic | >= 1.13.0 |
| Vector DB | PGVector | >= 0.2.0 |
| Analytics | NumPy, Pandas, SciPy, scikit-learn, statsmodels | — |
| Charts | Matplotlib | >= 3.8 |
| Maps | Folium, Google Static Maps, OSM tiles | — |
| Parsers | gpxpy, fitparse | >= 1.6.2, >= 1.2.0 |
| AI / LLM | Groq SDK + sentence-transformers (local embeddings) | >= 0.4.0 |
| Auth | python-jose[cryptography], passlib, bcrypt | >= 3.3.0 |
| Rate Limit | slowapi | >= 0.1.9 |
| Cache | Redis (optional, graceful fallback) | >= 5.0.0 |
| Observability | Sentry, Prometheus, Grafana, OpenTelemetry/Zipkin | — |
| Security | CSP, HSTS, X-Frame-Options, X-XSS-Protection | — |

### Frontend

| Component | Technology |
|---|---|
| Framework | Vue 3 (Composition API + `<script setup>`) |
| Language | TypeScript (`strict: true`) |
| Build | Vite 5 |
| State | Pinia |
| Router | Vue Router 4 |
| Charts | Chart.js |
| Maps | Leaflet + leaflet.heat |
| PWA | vite-plugin-pwa + custom `sw.js` |
| Mobile | Capacitor 5 (Android + iOS) |
| Testing | Vitest (unit) + Playwright (E2E) |
| Lint | ESLint + vue-tsc |

---

## 4. Project Structure

```
bike_analyzer/
├── __init__.py
├── main.py                          # Unified CLI entrypoint (api/web/cli)
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
│       ├── fatigue.py
│       ├── performance.py
│       └── stress.py
├── backend/
│   ├── settings.py                  # Pydantic Settings v2 (centralized config)
│   ├── security.py                  # JWT auth + security headers
│   ├── rate_limiter.py              # slowapi rate limiter
│   ├── redis_client.py              # Async Redis client + cache decorator
│   ├── task_queue.py                # Async background task queue
│   ├── event_bus.py                 # Domain event pub/sub
│   ├── logging_config.py            # Structured logging + request ID
│   ├── observability.py             # Sentry + OpenTelemetry + Zipkin init
│   ├── monitoring.py                # Health checks DB/Redis/task queue
│   ├── audit_log.py                 # Admin audit log (JSONL)
│   ├── api/
│   │   ├── app_factory.py           # FastAPI factory + CORS + rate limit + security
│   │   ├── routes.py                # 40+ API endpoints
│   │   ├── schemas.py               # Pydantic DTOs
│   │   ├── bm2_routes.py            # BM2 subsystem routes
│   │   └── utils.py                 # API helpers
│   ├── analytics/                   # Analytics engine
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
│   │   ├── google_auth.py
│   │   └── ...
│   ├── db/                          # Data access layer (sync + async)
│   │   ├── database.py              # SQLite CRUD sync
│   │   ├── async_db.py              # Async DB layer (asyncpg/aiosqlite)
│   │   ├── postgres_db.py           # PostgreSQL ORM layer
│   │   ├── models.py                # SQLAlchemy ORM models async
│   │   └── api_compat.py            # API compatibility layer
│   ├── database/                    # Vector DB
│   │   └── vectordb.py              # PGVector wrapper
│   ├── events/                      # Domain events
│   ├── ingestion/                   # GPS parsers + external APIs
│   │   ├── gps_parser.py            # GPX/FIT parsing
│   │   ├── strava_client.py         # Strava OAuth2 + PKCE
│   │   ├── garmin_client.py         # Garmin Connect OAuth2
│   │   ├── wahoo_client.py          # Wahoo Fitness import
│   │   └── google_fit.py            # Google Fit OAuth2
│   ├── maps/                        # Map rendering
│   │   ├── map_renderer.py          # Folium renderer
│   │   ├── google_maps.py           # Google Static Maps
│   │   ├── osm_maps.py              # OpenStreetMap tiles
│   │   └── serpapi_maps.py          # SerpApi nearby places
│   ├── traffic/                     # Traffic safety analysis
│   │   ├── safety_analyzer.py
│   │   ├── overpass_client.py
│   │   └── incident_fetcher.py
│   ├── weather/                     # Weather service
│   │   └── weather_service.py
│   ├── models/                      # Domain dataclasses (sync with core/)
│   │   └── models.py
│   ├── processing/                  # GPS data processing
│   │   ├── processing.py
│   │   └── segment_detector.py
│   ├── static/                      # Backend-served static assets (SPA build)
│   │   ├── index.html
│   │   ├── sw.js
│   │   └── ...
│   └── utils/
│       ├── dates.py
│       └── logger.py
├── frontend/                        # Vue 3 + Vite + TypeScript SPA
│   ├── src/
│   │   ├── main.ts                  # App bootstrap
│   │   ├── App.vue                  # Root shell + overlay auth
│   │   ├── router/index.ts          # Auth guards + localStorage sync
│   │   ├── stores/                  # Pinia stores
│   │   │   ├── auth.ts              # JWT in localStorage
│   │   │   ├── ui.ts                # Theme, language, oauthLoading
│   │   │   └── trackingStore.ts     # GPS tracking state
│   │   ├── components/              # 30 Vue components
│   │   ├── views/                   # Page views
│   │   ├── composables/             # useRides, useToast, usePWA, useI18n, useChart
│   │   ├── utils/                   # api.ts, routeMap.ts
│   │   └── plugins/                 # bikeTracking.ts (Capacitor)
│   ├── android/                     # Android app (Kotlin + Capacitor)
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── vitest.config.js
│   └── playwright.config.js
├── tests/                           # 97 pytest files
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

## 5. Data Models

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
| `kb_embeddings` | Vector embeddings for PGVector RAG |

---

## 6. API Reference

**Base URL:** `http://localhost:8000/api/v1`

### Health

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Basic health check |
| GET | `/health/redis` | No | Redis health check |
| GET | `/health/detailed` | No | Detailed health + DB stats |

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | No | JWT login (form-urlencoded) |
| POST | `/auth/register` | No | User registration |
| GET | `/auth/google` | No | Google OAuth URL |
| POST | `/auth/google/callback` | No | Google token exchange |
| GET | `/auth/me` | Yes | Current user profile |

### Rides

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

## 7. Analytics Engine

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

## 8. AI Coach & Knowledge Base

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

## 9. Frontend

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

### Components (30)
- `LoginForm.vue`, `HeaderTabs.vue`, `RidesPanel.vue`, `ImportPanel.vue`
- `AthletePanel.vue`, `CoachPanel.vue`, `KnowledgePanel.vue`
- `DashboardPanel.vue`, `ChartsPanel.vue`, `StatsSummary.vue`
- `RideMapPanel.vue`, `SpeedMap.vue`, `HeatmapPanel.vue`
- `CalendarPanel.vue`, `GranfondoPlanner.vue`, `BadgesPanel.vue`
- `WeatherPanel.vue`, `AdminPanel.vue`, `LiveMap.vue`
- `ErrorBoundary.vue`, `ConfirmModal.vue`, `ToastContainer.vue`
- `PWAInstallPrompt.vue`, `LanguageSwitcher.vue`, `ControlsBar.vue`
- `RideDetail.vue`, `RideComparison.vue`, `RideMetricsPanel.vue`
- `Bm2Panel.vue`

### Native Mobile
- **Android**: Kotlin foreground service (`BikeTrackingService.kt`) + Capacitor plugin
- **iOS**: Swift plugin (`BikeTrackingPlugin.swift`) + Capacitor config

---

## 10. Testing

### Backend
- **97 pytest files** covering unit, integration, API, and error paths
- Run: `pytest` or `pytest --cov=bike_analyzer --cov-report=term`
- Frameworks: pytest, pytest-asyncio, pytest-cov

### Frontend
- **Vitest**: `npm run test` (321 tests)
- **Playwright**: `npm run test:e2e` or `npm run e2e:local`
- Frameworks: Vitest, @vue/test-utils, Playwright

### Key Test Modules
- Core models, pipeline, engine, fitness state
- Analytics calculators (100% coverage)
- Power model, fatigue, performance, stress
- AI Coach API, knowledge base API
- Strava/Garmin/Google Fit integrations
- Security, rate limiting, event bus
- Traffic safety, weather, anomaly detection
- Frontend: auth, routing, API client, components

---

## 11. External Integrations

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

## 12. Security & Monitoring

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

## 13. Deployment

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

## 14. Configuration

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

## 15. Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all tests pass before submitting a PR.

---

*Documentation generated for BikeMaster v1.5.0*
