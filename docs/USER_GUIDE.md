# BikeMaster User Guide

Lifestyle health intelligence system. Import activities from GPX/FIT files, track health variables (energy, macros, hydration, glucose, VO2, breathing, HR, sleep, stress), analyze performance metrics, estimate calories and fatigue, visualize routes on interactive maps, and access everything through a REST API.

## Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Data Models](#data-models)
- [How Analytics Work](#how-analytics-work)
- [Google Fit Integration](#google-fit-integration)
- [Maps and Visualizations](#maps-and-visualizations)
- [AI Coach and Knowledge Base](#ai-coach-and-knowledge-base)
- [Testing](#testing)
- [Deployment](#deployment)
- [Project Structure](#project-structure)

## Introduction

BikeMaster is a complete application for:
- **GPS ingestion** — Parse GPX and Garmin FIT files
- **Performance analytics** — Distance, speed, elevation, accelerations, pauses
- **Calorie estimation** — Physics + MET-based models
- **Fatigue scoring** — Weighted formula with recovery recommendations
- **Interactive maps** — Speed-colored routes via Folium/Leaflet
- **REST API** — 40+ endpoints for rides, analysis, charts, import/export
- **Web dashboard** — Dark-themed UI with stats and route maps
- **Data export** — JSON and CSV formats

## Installation

### Prerequisites
- Python 3.10 or higher
- pip (package manager)

### Install Dependencies
```bash
git clone https://github.com/ballales1984-wq/bikemaster.git
cd bikemaster
pip install -r requirements.txt
```

### Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
DATABASE_URL=sqlite:///./rides.db
API_HOST=0.0.0.0
API_PORT=8000
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

## Quick Start

### API Server Mode (default)
```bash
python main.py api
# Or with reload for development
python main.py api --reload
```

### Web Frontend Mode
```bash
python main.py web
```

### CLI Mode
```bash
python main.py cli
```

Open browser at [http://localhost:8000](http://localhost:8000) for the dashboard.

## API Endpoints

### Health Check
| Method | Endpoint | Description |
|--------|----------|-----------|
| GET | `/api/v1/health` | Basic service status |
| GET | `/api/v1/health/detailed` | Detailed status with DB stats |

### Rides (CRUD)
| Method | Endpoint | Description |
|--------|----------|-----------|
| POST | `/api/v1/rides` | Create ride |
| GET | `/api/v1/rides` | List rides (paginated, sortable) |
| GET | `/api/v1/rides/{id}` | Get ride details with analytics |
| DELETE | `/api/v1/rides/{id}` | Delete ride |
| POST | `/api/v1/rides/analyze` | Multi-ride summary |
| POST | `/api/v1/rides/{id}/analyze` | Single ride analysis |

**Query params for `/api/v1/rides`:**
- `page` — Page number (default: 1)
- `page_size` — Page size (1-100, default: 20)
- `sort` — Sort field: `date`, `distance`, `duration` (default: `date`)

### Import
| Method | Endpoint | Description |
|--------|----------|-----------|
| POST | `/api/v1/import/gpx` | Upload GPX file |
| POST | `/api/v1/import/fit` | Upload FIT file |
| POST | `/api/v1/import/multiple` | Batch upload GPX/FIT |
| GET | `/api/v1/import/google-fit/auth` | Get Google Fit OAuth URL |
| POST | `/api/v1/import/google-fit/token` | Exchange OAuth code for token |
| POST | `/api/v1/import/google-fit` | Import cycling activities from Google Fit |

### Export
| Method | Endpoint | Description |
|--------|----------|-----------|
| GET | `/api/v1/rides/export/json` | Export as JSON |
| GET | `/api/v1/rides/export/csv` | Export as CSV |

### Charts
| Method | Endpoint | Description |
|--------|----------|-----------|
| GET | `/api/v1/charts/speed/{id}` | Speed chart PNG |
| GET | `/api/v1/charts/elevation/{id}` | Elevation chart PNG |
| GET | `/api/v1/charts/duration` | Duration chart PNG |
| GET | `/api/v1/charts/distance/{id}` | Distance chart PNG |
| GET | `/api/v1/rides/{id}/map` | Interactive Folium map |
| GET | `/api/v1/rides/{id}/map/google` | Google Static Map PNG |

### Athletes
| Method | Endpoint | Description |
|--------|----------|-----------|
| POST | `/api/v1/athletes` | Create athlete profile |
| GET | `/api/v1/athletes/{id}` | Get athlete |
| PUT | `/api/v1/athletes/{id}` | Update athlete |
| POST | `/api/v1/athletes/{id}/metrics` | Save metrics |

### Scores
| Method | Endpoint | Description |
|--------|----------|-----------|
| GET | `/api/v1/scores/athlete/{id}` | Get athlete scores (performance, endurance, efficiency) |

### Benchmark
| Method | Endpoint | Description |
|--------|----------|-----------|
| POST | `/api/v1/benchmark/compare` | Compare athlete to benchmark |

### AI Coach
| Method | Endpoint | Description |
|--------|----------|-----------|
| GET | `/api/v1/coach/workout` | Workout recommendations |
| GET | `/api/v1/coach/recovery` | Recovery recommendations |
| GET | `/api/v1/coach/trends` | Historical trends analysis |

### Knowledge Base
| Method | Endpoint | Description |
|--------|----------|-----------|
| GET | `/api/v1/knowledge` | List available topics |
| GET | `/api/v1/knowledge/search?q=...` | Search knowledge base |

### Admin
| Method | Endpoint | Description |
|--------|----------|-----------|
| GET | `/api/v1/admin/backup` | Database backup |
| POST | `/api/v1/admin/indexes` | Create DB indexes |
| GET | `/api/v1/admin/stats` | System stats |
| POST | `/api/v1/admin/reset-demo` | Reset demo data |
| GET | `/api/v1/rides/count` | Count rides |

## Data Models

### Ride
```python
@dataclass
class Ride:
    id: Optional[int]
    athlete_id: Optional[int]
    date: str
    distance_km: float
    duration_minutes: float
    avg_speed_kmh: float
    weight_kg: float = 70.0
    calories: float = 0.0
    heart_rate_avg: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    gps_points: Optional[List[GPSPoint]] = None
    created_at: Optional[str] = None
```

### GPSPoint
```python
@dataclass
class GPSPoint:
    lat: float
    lon: float
    timestamp: datetime
    altitude: Optional[float] = None
    speed: Optional[float] = None
```

### AthleteProfile
```python
@dataclass
class AthleteProfile:
    id: Optional[int]
    name: str = ""
    age: int = 30
    weight_kg: float = 70.0
    height_cm: Optional[float] = None
    fat_percentage: Optional[float] = None
    years_active: int = 1
    weekly_sessions: int = 3
    monthly_hours: float = 0.0
    annual_hours: float = 0.0
    experience_level: str = "Beginner"  # Beginner, Amateur, Intermediate, Advanced, Elite
```

## How Analytics Work

### Main Processors

1. **GPS Parser** (`ingestion/gps_parser.py`) — Parse GPX/FIT files, convert to Ride objects
2. **Analytics** (`analytics/analytics.py`) — Statistics, segments, pauses, accelerations
3. **Calories** (`analytics/calories.py`) — Physics and MET-based calorie estimation
4. **Fatigue** (`analytics/fatigue.py`) — Fatigue scoring and recovery estimates
5. **Performance** (`analytics/performance.py`) — Performance, endurance, efficiency scores

### Key Functions

```python
# Session summary
summary = calculate_summary(rides)
# Returns: total_rides, total_km, total_calories, avg_speed, avg_fatigue

# Single ride analysis
analysis = analyze_ride(ride)
# Returns: segments, pauses, accelerations, statistics

# Calorie estimation
calories = estimate_calories(ride, method="physics")  # or "met"

# Fatigue scoring
score = calculate_fatigue_score(ride)
recovery = estimate_recovery_hours(ride)
```

## Google Fit Integration

### OAuth2 Flow
1. Get authorization URL: `GET /api/v1/import/google-fit/auth?client_id=...`
2. Redirect user to Google for authorization
3. Receive callback with authorization code
4. Exchange code for token: `POST /api/v1/import/google-fit/token`
5. Import data: `POST /api/v1/import/google-fit` with access_token

### Required Scopes
- `https://www.googleapis.com/auth/fitness.activity.read`
- `https://www.googleapis.com/auth/fitness.body.read`

## Maps and Visualizations

### Folium (Offline)
- `create_route_map(points)` — Generates interactive HTML map
- Color-coded by speed (blue→red)
- Start/end markers

### Google Static Maps (Online)
- Requires `GOOGLE_MAPS_API_KEY` in `.env`
- `create_google_static_map(points, api_key)` — PNG map
- Requires Google Static Maps API enabled

### Matplotlib Charts
- Speed over time
- Elevation over time
- Distance traveled
- Activity duration

## AI Coach and Knowledge Base

### Knowledge Base (`/knowledge_base/`)
Markdown files with sports content:
- `training.md` — Training theory
- `recovery.md` — Recovery and rest
- `cardio.md` — Cardiovascular theory

### AI Coach (`analytics/ai_coach.py`)
- `generate_workout_recommendations(rides, athlete)` — Training plan
- `generate_recovery_recommendations(ride, fatigue)` — Recovery plan
- `analyze_historical_trends(rides)` — Historical trends

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=bike_analyzer

# Specific test file
pytest tests/test_analytics.py
pytest tests/test_models.py
pytest tests/test_database.py
pytest tests/test_performance.py
pytest tests/test_edge_cases.py
```

## Deployment

### Docker
```bash
# Build
docker build -t bikemaster .

# Run
docker run -p 8000:8000 bikemaster
```

### Docker Compose
```bash
docker-compose up -d
# Open http://localhost:8000
```

### Azure
```bash
azd up
```

## Project Structure

```
bike_analyzer/
├── __init__.py              # Package facade
├── main.py                  # Unified entry point
└── backend/
    ├── api/
    │   ├── app_factory.py   # FastAPI configuration
    │   ├── routes.py        # 40+ API endpoints
    │   └── schemas.py       # Pydantic models
    ├── analytics/
    │   ├── analytics.py     # Basic statistics
    │   ├── calories.py      # Calorie estimation
    │   ├── fatigue.py       # Fatigue scoring
    │   ├── performance.py   # Performance scores
    │   ├── benchmark.py     # Athlete comparison
    │   ├── ai_coach.py      # AI recommendations
    │   └── knowledge_base.py# RAG system
    ├── db/
    │   └── database.py      # SQLite CRUD + backup
    ├── ingestion/
    │   ├── gps_parser.py    # GPX/FIT parsing
    │   └── google_fit.py    # Google Fit OAuth
    ├── maps/
    │   ├── map_renderer.py  # Folium renderer
    │   └── google_maps.py   # Google Static Maps
    ├── models/
    │   └── models.py        # Domain models
    └── processing/
        └── processing.py    # Route processing
frontend/
    └── dashboard.py         # Standalone dashboard
scripts/
    ├── generate_sample_ride.py   # Demo data generator
    └── demo_map.py              # Map demo
tests/
    ├── test_analytics.py
    ├── test_models.py
    ├── test_database.py
    ├── test_performance.py
    └── test_edge_cases.py
knowledge_base/
    ├── training.md
    ├── recovery.md
    └── cardio.md
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push branch (`git push origin feature/new-feature`)
5. Open Pull Request

## Troubleshooting

**Error: "No GPS points for this ride"**
- Verify GPX/FIT file is valid
- Check file has tracking points

**Error: "GOOGLE_MAPS_API_KEY not configured"**
- Add API key in `.env`
- Verify Google Static Maps API is enabled

**Database errors**
- Run `POST /api/v1/admin/indexes` to optimize queries