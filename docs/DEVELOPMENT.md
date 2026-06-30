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
│  db/ (SQLAlchemy)  │  repositories/  │  traffic/  │  auth/     │
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
│  models.py  │  pipeline.py  │  fitness_state.py                │
└──────────────────────────────────────────────────────────────────┘
```

### Domain Layer (`core/`)

Pure Python dataclasses and logic independent of any infrastructure:

- **`models.py`** — Domain entities: `GPSPoint`, `Segment`, `Pause`, `Ride`, `AthleteProfile`, `CalendarEvent`, `RouteStatistics`
- **`pipeline.py`** — `AnalysisPipeline`: orchesta GPS processing → metric computation
- **`engine.py`** — `AnalysisEngine`: orchestratore principale con FitnessStateVector
- **`fitness_state.py`** — `FitnessStateVector`: snapshot stato fisiologico (CTL/ATL/TSB)

### Analytics Layer (`analytics/`)

Struttura Clean Architecture:

- **`calculators/`** — Pure functions testabili in isolamento (calories, power, fatigue, performance, stress)
- **`services/`** — Orchestrazione use case (ride analysis, fitness state computation, context builder)
- **`repositories/`** — Astrazione accesso dati (ride, athlete, fitness state, training stress)

### Infrastructure Layer

- **`db/`** — Data access: SQLite sync, async SQLAlchemy (asyncpg/aiosqlite), PostgreSQL ORM
- **`database/vectordb.py`** — PGVector wrapper for similarity search
- **`traffic/`** — Road safety analysis (Overpass API, incident data)
- **`auth/`** — OAuth2 providers (Google)
- **`ingestion/`** — External data sources (GPX/FIT parser, Google Fit, Strava, Garmin)

### Presentation Layer

- **`api/`** — FastAPI routes, schemas, app factory (CORS, rate limit, security headers)
- **`frontend/`** — Vue 3 + Vite + TypeScript standalone SPA

---

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| Backend | FastAPI | >=0.110.0 |
| Core | Python dataclasses, Clean Architecture | - |
| Database (dev) | SQLite | built-in |
| Database (prod) | PostgreSQL + asyncpg | - |
| ORM | SQLAlchemy 2.0 | >=2.0.27 |
| ORM (sync) | SQLite CRUD | - |
| Vector DB | PGVector | >=0.2.0 |
| Migrations | Alembic | >=1.13.0 |
| Analytics | NumPy, Pandas, SciPy, scikit-learn, statsmodels | >=1.26.4 |
| Maps | Folium, Leaflet.js, Google Static Maps | >=0.16.0 |
| Traffic | OpenStreetMap Overpass API | - |
| Parsers | gpxpy, fitparse | >=1.6.2, >=1.2.0 |
| AI | Groq SDK + OpenAI SDK (embeddings) | >=0.4.0, >=1.0.0 |
| Auth | python-jose[cryptography], passlib, bcrypt | >=3.3.0, >=4.0.0 |
| Rate Limit | slowapi | >=0.1.9 |
| Config | Pydantic Settings v2 | >=2.0.0 |
| Cache | Redis (optional) | >=5.0.0 |
| Frontend | Vue 3 + Vite + TypeScript + Pinia | - |
| Frontend charts | Chart.js | - |
| Frontend maps | Leaflet.js + leaflet.heat | - |
| Mobile | Android Kotlin + Capacitor | - |
| Testing | pytest, pytest-asyncio, Playwright | >=0.23.0 |

---

## Backend Extension

### Add New Pure Calculator

1. Create function in `analytics/calculators/`:
```python
# bike_analyzer/backend/analytics/calculators/new_metric.py
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

    # async + sync variants
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
│   ├── main.ts              # App entry point
│   ├── App.vue              # Root component
│   ├── index.css            # Global styles (dark theme + design tokens)
│   ├── router/index.ts      # Vue Router configuration
│   ├── components/          # 20+ reusable Vue components
│   │   ├── HeaderTabs.vue
│   │   ├── DashboardPanel.vue
│   │   ├── RidesPanel.vue
│   │   ├── RidesView.vue
│   │   ├── ...
│   ├── stores/              # Pinia state management
│   │   ├── auth.ts          # JWT authentication state
│   │   ├── trackingStore.ts # GPS live tracking state
│   ├── composables/         # Composable functions
│   │   ├── useAuth.ts       # Authentication composable
│   │   ├── useChart.ts      # Chart.js composable
│   │   ├── useRides.ts      # Rides CRUD composable
│   ├── utils/
│   │   ├── api.ts           # Fetch-based API client
│   │   └── routeMap.ts      # Route mapping utilities
│   ├── views/
│   │   └── RideTracking.vue # Live GPS tracking page
│   └── plugins/
│       └── bikeTracking.ts  # Capacitor native bridge
```

### Build and Run

```bash
cd frontend
npm install
npm run dev        # Development server (Vite)
npm run build      # Production build (dist/)
npm run preview    # Preview production build
npm run cap:sync   # Sync with Android (Capacitor)
npm run android:build  # Generate APK
```

### Add New Component

1. Create `.vue` file in `src/components/`:
```vue
<script setup lang="ts">
// Composition API with <script setup>
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

1. Create in `src/stores/`:
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

1. Create in `src/composables/`:
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
├── conftest.py                    # Shared fixtures (db, test client)
├── unit/                          # Unit tests per modulo
│   ├── test_models.py
│   ├── test_calories.py
│   ├── test_fatigue.py
│   ├── test_performance.py
│   ├── test_power_model.py
│   ├── test_advanced_analytics.py
│   ├── test_analytics_trends.py
│   ├── test_training_stress.py
│   ├── test_event_bus.py
│   ├── test_security.py
│   └── ...
├── api/                           # API endpoint tests
│   ├── test_routes_coverage.py
│   ├── test_ai_coach_api.py
│   ├── test_knowledge_api.py
│   └── ...
├── integration/                   # Integration tests
│   ├── test_strava_integration.py
│   ├── test_garmin_integration.py
│   ├── test_google_fit.py
│   ├── test_database.py
│   └── ...
└── frontend/                      # Frontend tests
    └── test_frontend_dashboard.py
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

### Schema (SQLAlchemy ORM — async)

**Table `rides`** — Uscite ciclistiche
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

**Table `athletes`** — Profili atleta
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

**Table `metrics`** — Metriche calcolate per ride

**Table `chat_history`** — Memoria conversazionale AI Coach

**Table `calendar_events`** — Eventi di allenamento pianificati

**Table `strava_tokens`** — OAuth tokens Strava

**Table `garmin_tokens`** — OAuth tokens Garmin

**Table `kb_embeddings`** — Vector embeddings per PGVector RAG (PostgreSQL)

### Migrations

Alembic configurato per migrazioni versionate. Initial migration: `08ee39bfe529_initial_models.py`.

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|:---|:---|:---|
| DATABASE_URL | sqlite:///./rides.db | Database connection |
| DATABASE_URL_ASYNC | sqlite+aiosqlite:///./rides.db | Async engine URL |
| API_HOST | 0.0.0.0 | API server host |
| API_PORT | 8000 | API server port |
| SECRET_KEY | (required in prod) | JWT signing key (32+ chars) |
| SECRET_KEY_PREVIOUS | - | Previous key for rotation |
| ENVIRONMENT | development | Environment mode |
| CORS_ORIGINS | * | Allowed CORS origins |
| GOOGLE_MAPS_API_KEY | - | Google Maps API key |
| GOOGLE_FIT_CLIENT_ID | - | Google Fit OAuth client ID |
| GOOGLE_FIT_CLIENT_SECRET | - | Google Fit OAuth secret |
| STRAVA_CLIENT_ID | - | Strava OAuth client ID |
| STRAVA_CLIENT_SECRET | - | Strava OAuth secret |
| STRAVA_REDIRECT_URI | http://localhost:8000/api/v1/auth/strava/callback | Strava callback |
| GARMIN_CONSUMER_KEY | - | Garmin OAuth key |
| GARMIN_CONSUMER_SECRET | - | Garmin OAuth secret |
| GROQ_API_KEY | - | Groq LLM API key |
| OPENAI_API_KEY | - | OpenAI API key (for embeddings) |
| REDIS_URL | - | Redis connection URL |
| SENTRY_DSN | - | Sentry error tracking |
| MAP_DEFAULT_ZOOM | 13 | Default map zoom level |
| MAX_SPEED_KM_H | 120 | Max speed validation |
| PAUSE_SPEED_THRESHOLD | 2 | Speed threshold for pause detection |
| FATIGUE_WEIGHT_DURATION | 0.30 | Duration weight in fatigue |
| FATIGUE_WEIGHT_HR | 0.30 | Heart rate weight in fatigue |
| FATIGUE_WEIGHT_SPEED | 0.20 | Speed weight in fatigue |
| FATIGUE_WEIGHT_ELEVATION | 0.10 | Elevation weight in fatigue |
| FATIGUE_WEIGHT_WEIGHT | 0.10 | Weight factor in fatigue |
| WEATHER_API_KEY | - | OpenWeatherMap API key |
| CALORIE_EFFICIENCY_FACTOR | 0.25 | Neuromuscular efficiency |
| CALORIE_BENCHMARK_KCAL_KM | 30 | Benchmark kcal per km |
| EVENT_BUS_STRICT_MODE | false | Strict mode for event bus |

---

## Deployment

### Environment Variables

See Configuration section above. All external service keys are optional (app degrades gracefully).

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

---

## Roadmap

| Phase | Status | Description |
|:---|:---:|:---|
| 1-80 | ✅ Done | Core analytics & database |
| 81-145 | ✅ Done | Advanced analytics, AI Coach, Maps, Weather |
| Clean Architecture | ✅ Done | Core layer, calculators/services/repositories |
| Traffic Safety | ✅ Done | Road risk analysis |
| Strava/Garmin | ✅ Done | External integrations |
| Vector DB | ✅ Done | PGVector + TF-IDF |
| Event Bus | ✅ Done | Domain events pub/sub |
| Phone GPS Tracking | ✅ Done | Android foreground service |
| Frontend Modern | ✅ Done | Vue 3 + Vite + TS + Pinia |
| CI/CD | ✅ Done | GitHub Actions + Trivy |
| Multi-user | ⏳ Todo | Data isolation + auth |
| PWA complete | ✅ Done | Offline + service worker |
| Coverage >92% | ✓ Report | Threshold removed; coverage non-blocking |
| Production monitoring | ❌ Todo | Prometheus + Grafana |

See [ROADMAP.md](../ROADMAP.md) for full details.
