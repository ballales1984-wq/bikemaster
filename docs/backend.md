# Backend

## Tech Stack

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

---

## Architecture

```
bike_analyzer/
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
│   ├── api/                         # FastAPI Presentation Layer
│   ├── analytics/                   # Analytics Engine (calculators + services + repositories)
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
```

---

## External Integrations

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

## Security & Monitoring

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

## Phone GPS Tracking

- **Android**: Kotlin foreground service (`BikeTrackingService.kt`) + Capacitor plugin
- **iOS**: Swift plugin (`BikeTrackingPlugin.swift`) + Capacitor config
- Live tracking via `RideTracking.vue` + `trackingStore.ts`
- Incremental GPX writing in background
- Auto-pause detection < 3 km/h
- BLE sensor support (HR, Cadence, Power)

---

## Traffic Safety Analysis

- **Safety Analyzer** — Risk score computation (0-1) based on road type weights, cycling infrastructure bonus, incidents penalty
- **Overpass Client** — OpenStreetMap queries for bike lanes and road types
- **Incident Fetcher** — Area incident data

---

## Configuration

Key environment variables (see [configuration.md](./configuration.md) for the full list):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./rides.db` | Database connection |
| `DATABASE_URL_ASYNC` | `sqlite+aiosqlite:///./rides.db` | Async engine URL |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `SECRET_KEY` | *(required in prod)* | JWT signing key (32+ chars) |
| `ENVIRONMENT` | `development` | Environment mode |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `GROQ_API_KEY` | — | Groq LLM API key |
| `REDIS_URL` | — | Redis connection URL |
| `STRAVA_CLIENT_ID` | — | Strava OAuth client ID |
| `STRAVA_CLIENT_SECRET` | — | Strava OAuth secret |
| `STRAVA_REDIRECT_URI` | `http://localhost:8000/api/v1/import/strava/callback` | Strava callback |
| `GARMIN_CONSUMER_KEY` | — | Garmin OAuth key |
| `GARMIN_CONSUMER_SECRET` | — | Garmin OAuth secret |
| `GOOGLE_FIT_CLIENT_ID` | — | Google Fit OAuth client ID |
| `GOOGLE_FIT_CLIENT_SECRET` | — | Google Fit OAuth secret |
| `GOOGLE_MAPS_API_KEY` | — | Google Static Maps API key |
| `WEATHER_API_KEY` | — | OpenWeatherMap API key |
