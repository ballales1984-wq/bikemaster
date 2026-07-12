# Developer Documentation - BikeMaster

## Architecture Overview

BikeMaster follows **Clean Architecture** with clear separation of concerns across four layers:

```
┌──────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                            │
│  api/routes.py (FastAPI)  │  frontend/ (Vue 3 SPA)            │
└───────────────────────────┬──────────────────────────────────────┘
                             │
┌───────────────────────────▼──────────────────────────────────────┐
│                    Infrastructure Layer                          │
│  db/  │  database/  │  repositories/  │  traffic/  │  auth/     │
│  analytics/services/  │  analytics/repositories/               │
└───────────────────────────┬──────────────────────────────────────┘
                             │
┌───────────────────────────▼──────────────────────────────────────┐
│                    Application Layer                             │
│  analytics/services/  │  core/engine.py  │  task_queue.py      │
└───────────────────────────┬──────────────────────────────────────┘
                             │
┌───────────────────────────▼──────────────────────────────────────┐
│                    Domain Layer (core/)                          │
│  models.py  │  session.py  │  pipeline.py  │  fitness_state.py │
│  validators.py  │  validation.py  │  calculators/             │
└──────────────────────────────────────────────────────────────────┘
```

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
- **`services/`** — Use case orchestration (ride analysis, fitness state, context builder)
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

---

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| Backend | FastAPI | >=0.110.0 |
| Core | Python dataclasses, Clean Architecture | - |
| Database (dev) | SQLite | built-in |
| Database (prod) | PostgreSQL + asyncpg | - |
| ORM | SQLAlchemy 2.0 | >=2.0.27 |
| Vector DB | PGVector | >=0.2.0 |
| Migrations | Alembic | >=1.13.0 |
| Analytics | NumPy, Pandas, SciPy, scikit-learn, statsmodels | - |
| Maps | Folium, Leaflet.js, Google Static Maps | >=0.16.0 |
| Traffic | OpenStreetMap Overpass API | - |
| Parsers | gpxpy, fitparse | >=1.6.2, >=1.2.0 |
| AI | Groq SDK (LLM) + sentence-transformers (embeddings locali) | >=0.4.0 |
| Auth | python-jose[cryptography], passlib, bcrypt | >=3.3.0, >=4.0.0 |
| Rate Limit | slowapi | >=0.1.9 |
| Config | Pydantic Settings v2 | >=2.0.0 |
| Cache | Redis (optional) | >=5.0.0 |
| Frontend | Vue 3 + Vite 5 + TypeScript + Pinia | - |
| Frontend charts | Chart.js | - |
| Frontend maps | Leaflet.js + leaflet.heat | - |
| Mobile | Android Kotlin + iOS Swift + Capacitor 5 | - |
| Testing | pytest, pytest-asyncio, Vitest, Playwright | - |

---

## Backend Extension

### Add New Pure Calculator

1. Create function in `core/calculators/` or `analytics/calculators/`:
```python
# bike_analyzer/core/calculators/new_metric.py
def calculate_new_metric(ride: Ride, params: dict) -> float:
    """Pure function — no DB, no API, no side effects."""
    return value
```

2. Import in pipeline or service as needed.

### Add New Analytics Service (Use Case)

1. Create service in `analytics/services/`:
```python
# bike_analyzer/backend/analytics/services/new_service.py
class NewAnalysisService:
    def __init__(self, ride_repo: RideRepository):
        self._ride_repo = ride_repo

    async def analyze(self, ride_id: int) -> dict:
        ride = await self._ride_repo.get_by_id(ride_id)
        # ... orchestration logic
        return result
```

### Add New Repository (Data Access)

1. Create repository in `analytics/repositories/`:
```python
# bike_analyzer/backend/analytics/repositories/new_repository.py
class NewRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    async def save(self, data: dict) -> int:
        if self._session_factory:
            return await self._save_async(data)
        return self._save_sync(data)
```

### Add New API Endpoint

1. Add handler in `api/routes.py`:
```python
@router.get("/new/feature")
async def new_feature(parameter: str):
    # Logic here
    return {"result": result}
```

2. Add Pydantic schema in `api/schemas.py` if request/response DTOs needed.

### Add New Domain Model

Modify `bike_analyzer/core/models.py`:
```python
@dataclass(frozen=True)
class NewModel:
    field1: str
    field2: int
```

### Add Domain Event

1. Define event class in `events/__init__.py`:
```python
class NewEvent:
    type = "new.event.type"
```

2. Subscribe handler:
```python
from bike_analyzer.backend.events import subscribe
subscribe("new.event.type", my_handler)
```

3. Publish from service:
```python
from bike_analyzer.backend.events import publish
await publish("new.event.type", {"data": value})
```

### Add New OAuth2 Provider

1. Create client in `auth/`:
```python
# bike_analyzer/backend/auth/new_provider.py
def get_oauth_url(...) -> str: ...
def exchange_code(...) -> dict: ...
def get_user_info(...) -> dict: ...
```

2. Add endpoints in `api/routes.py`.

---

## Frontend Development

### Project Structure

```
frontend/
├── src/
│   ├── main.ts                    # App entry point
│   ├── App.vue                    # Root component
│   ├── index.css                  # Global styles (dark theme + design tokens)
│   ├── router/index.ts            # Vue Router configuration
│   ├── components/                # 30 Vue components
│   │   ├── LoginForm.vue
│   │   ├── HeaderTabs.vue
│   │   ├── RidesPanel.vue
│   │   ├── ImportPanel.vue
│   │   ├── AthletePanel.vue
│   │   ├── CoachPanel.vue
│   │   ├── DashboardPanel.vue
│   │   ├── ...
│   ├── stores/                    # Pinia state management
│   │   ├── auth.ts
│   │   ├── ui.ts
│   │   └── trackingStore.ts
│   ├── composables/               # Reusable composables
│   │   ├── useAuth.ts
│   │   ├── useChart.ts
│   │   ├── useRides.ts
│   │   ├── useToast.ts
│   │   ├── usePWA.ts
│   │   └── useI18n.ts
│   ├── utils/
│   │   ├── api.ts                 # Fetch-based API client (apiGet/Post/Put/Delete/Upload)
│   │   └── routeMap.ts
│   ├── views/
│   │   ├── RidesView.vue
│   │   └── RideTracking.vue
│   └── plugins/
│       └── bikeTracking.ts        # Capacitor native bridge
├── android/
├── public/
├── package.json
├── vite.config.js
├── vitest.config.js
└── playwright.config.js
```

### Build and Run

```bash
cd frontend
npm install
npm run dev        # Development server (Vite)
npm run build      # Production build (dist/)
npm run preview    # Preview production build
npm run typecheck  # vue-tsc --noEmit
npm run lint       # eslint --fix
npm run test       # Vitest unit tests
npm run e2e        # Playwright E2E
npm run e2e:local  # Playwright with local config
npm run cap:sync   # Sync with Android/iOS (Capacitor)
npm run android:build  # Generate APK
```

### Add New Component

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
</script>

<template>
  <div class="my-component">
    <!-- Template -->
  </div>
</template>

<style scoped>
/* Scoped styles */
</style>
```

### Add New Store (Pinia)

```typescript
// src/stores/myStore.ts
import { defineStore } from 'pinia'

export const useMyStore = defineStore('myStore', {
  state: () => ({ count: 0 }),
  actions: {
    increment() { this.count++ }
  }
})
```

### Add New Composable

```typescript
// src/composables/useMyFeature.ts
import { ref, onMounted } from 'vue'

export function useMyFeature() {
  const data = ref(null)
  onMounted(() => { /* ... */ })
  return { data }
}
```

### Testing Frontend

```bash
# Unit tests (Vitest)
npm run test

# E2E tests (Playwright)
npm run test:e2e
```

---

## Testing

### Backend

```bash
pytest                    # All tests
pytest -v                 # Verbose output
pytest tests/test_power_model.py  # Single file
pytest tests/test_*.py --cov=bike_analyzer --cov-report=term  # With coverage
pytest tests/test_event_bus.py -v   # Specific module
```

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── test_models.py
├── test_analytics.py
├── test_power_model.py
├── test_fatigue.py
├── test_performance.py
├── test_training_stress.py
├── test_ai_coach.py
├── test_ai_coach_api.py
├── test_knowledge_api.py
├── test_event_bus.py
├── test_security.py
├── test_strava_integration.py
├── test_garmin_integration.py
├── test_google_fit.py
├── test_traffic_safety.py
├── test_weather_service.py
├── test_anomaly_detection.py
├── ... (97 test files total)
```

### Write New Test

```python
# tests/test_new_module.py
import pytest
from bike_analyzer.backend.analytics.calculators.new_metric import calculate

def test_basic_case():
    assert calculate(input_data) == expected

def test_edge_case():
    with pytest.raises(ValueError):
        calculate(invalid_data)
```

---

## Database

### Schema

**Table `rides`** — Cycling sessions
| Column | Type | Description |
|:---|:---|:---|
| id | INTEGER PK | Primary key |
| athlete_id | INTEGER FK | Athlete reference |
| date | TEXT | Activity date |
| distance_km | REAL | Distance km |
| duration_minutes | REAL | Duration minutes |
| avg_speed_kmh | REAL | Average speed |
| weight_kg | REAL | Athlete weight |
| calories | REAL | Calories burned |
| heart_rate_avg | REAL | Avg heart rate |
| elevation_gain_m | REAL | Elevation gain |
| gps_points | TEXT (JSON) | GPS points array |
| created_at | TEXT | Created timestamp |

**Table `athletes`** — Athlete profiles
| Column | Type | Description |
|:---|:---|:---|
| id | INTEGER PK | Primary key |
| name | TEXT | Athlete name |
| age | INTEGER | Age |
| weight_kg | REAL | Weight kg |
| height_cm | REAL | Height cm |
| fat_percentage | REAL | Body fat % |
| years_active | INTEGER | Active years |
| weekly_sessions | INTEGER | Weekly sessions |
| experience_level | TEXT | Beginner/Amateur/Elite |
| goals | TEXT | Training goals |
| ftp_watts | REAL | Functional Threshold Power |

**Additional tables**: `metrics`, `chat_history`, `calendar_events`, `strava_tokens`, `garmin_tokens`, `kb_embeddings`

### Migrations

Alembic configured for versioned migrations. Initial migration: `08ee39bfe529_initial_models.py`.

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|:---|:---|:---|
| DATABASE_URL | `sqlite:///./rides.db` | Database connection |
| DATABASE_URL_ASYNC | `sqlite+aiosqlite:///./rides.db` | Async engine URL |
| API_HOST | `0.0.0.0` | API server host |
| API_PORT | `8000` | API server port |
| SECRET_KEY | *(required in prod)* | JWT signing key (32+ chars) |
| SECRET_KEY_PREVIOUS | — | Previous key for rotation |
| ENVIRONMENT | `development` | Environment mode |
| CORS_ORIGINS | `*` | Allowed CORS origins |
| GROQ_API_KEY | — | Groq LLM API key |
| REDIS_URL | — | Redis connection URL |
| SENTRY_DSN | — | Sentry error tracking |
| STRAVA_CLIENT_ID | — | Strava OAuth client ID |
| STRAVA_CLIENT_SECRET | — | Strava OAuth secret |
| STRAVA_REDIRECT_URI | `http://localhost:8000/api/v1/import/strava/callback` | Strava callback |
| GARMIN_CONSUMER_KEY | — | Garmin OAuth key |
| GARMIN_CONSUMER_SECRET | — | Garmin OAuth secret |
| GOOGLE_FIT_CLIENT_ID | — | Google Fit OAuth client ID |
| GOOGLE_FIT_CLIENT_SECRET | — | Google Fit OAuth secret |
| GOOGLE_MAPS_API_KEY | — | Google Static Maps API key |
| WEATHER_API_KEY | — | OpenWeatherMap API key |

---

## Deployment

### Docker

```bash
docker build -t bikemaster .
docker run -p 8000:8000 bikemaster
```

### Docker Compose

```bash
docker compose up -d
docker compose logs -f
```

### Azure Developer CLI

```bash
azd up        # Full deployment
azd deploy    # App-only deployment
```

### Render

```bash
render deploy
```

See `docker/deploy/` for Fly.io, Railway, and Vercel guides.

---

## Roadmap

See [ROADMAP.md](../ROADMAP.md) for full details.
