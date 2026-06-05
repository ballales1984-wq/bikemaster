# Developer Documentation - BikeMaster

## Architecture

BikeMaster follows a layered architecture with separation of concerns:

```
┌─────────────────────────────────────┐
│           Presentation              │
│  (Dashboard HTML/JS + API Routes)    │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│         Business Logic              │
│  (Analytics, Performance, AI Coach) │
├─────────────────────────────────────┤
│          Data Access                │
│      (SQLite Database Layer)         │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│         Domain Models               │
│    (Ride, GPSPoint, Athlete)         │
└─────────────────────────────────────┘
```

## Tech Stack

| Component | Technology | Version |
|------------|------------|----------|
| Backend | FastAPI | >=0.110.0 |
| Database | SQLite | built-in |
| Frontend | HTML/JS + Folium | - |
| Maps | Folium, Leaflet.js | >=0.16.0 |
| Analytics | NumPy, Pandas, Matplotlib | >=1.26.4, >=2.2.0 |
| Parsers | gpxpy, fitparse | >=1.6.2, >=1.2.0 |
| AI | Groq SDK | >=0.4.0 |

## Backend Extension

### Add New Endpoint

1. Modify `bike_analyzer/backend/api/routes.py`:
```python
@router.get("/new/feature")
async def new_feature(parameter: str):
    # Logic here
    return {"result": result}
```

2. Register router in `app_factory.py` (already included via `include_router`)

### Add Analysis

1. Create function in `analytics/`:
```python
# bike_analyzer/backend/analytics/new_analysis.py
def calculate_metric(ride: Ride) -> float:
    # Implementation
    return value
```

2. Expose via API:
```python
@router.get("/rides/{ride_id}/new-metric")
async def get_new_metric(ride_id: int):
    ride = Ride(**get_ride(ride_id))
    return {"metric": calculate_metric(ride)}
```

### Add Data Model

Modify `bike_analyzer/backend/models/models.py`:
```python
@dataclass
class NewModel:
    field1: str
    field2: int
    # ...
```

## Testing

### Test Structure
```
tests/
├── test_analytics.py       # Basic analytics tests
├── test_models.py          # Data model tests
├── test_database.py        # Database operation tests
├── test_performance.py     # Performance engine tests
├── test_edge_cases.py      # Edge case tests
└── test_ai_coach.py        # AI coach tests
```

### Write Tests
```python
# tests/test_new_module.py
import pytest
from bike_analyzer.backend.analytics.new_module import function_to_test

def test_basic_function():
    assert function_to_test(input) == expected

def test_edge_case():
    with pytest.raises(ValueError):
        function_to_test(invalid_input)
```

### Run Tests
```bash
pytest                    # All tests
pytest -v                 # Verbose output
pytest --cov=bike_analyzer # With coverage
pytest tests/test_models.py # Single file
```

## Database

### Table Schema

**rides**
| Column | Type | Description |
|---------|------|-------------|
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
| gps_points | TEXT (JSON) | GPS points |
| created_at | TEXT | Created timestamp |

**athletes**
| Column | Type | Description |
|---------|------|-------------|
| id | INTEGER PK | Primary key |
| name | TEXT | Athlete name |
| age | INTEGER | Age |
| weight_kg | REAL | Weight kg |
| height_cm | REAL | Height cm |
| fat_percentage | REAL | Body fat % |
| years_active | INTEGER | Active years |
| weekly_sessions | INTEGER | Weekly sessions |
| monthly_hours | REAL | Monthly hours |
| annual_hours | REAL | Annual hours |
| experience_level | TEXT | Experience level |

**metrics**
| Column | Type | Description |
|---------|------|-------------|
| id | INTEGER PK | Primary key |
| athlete_id | INTEGER FK | Athlete reference |
| ride_id | INTEGER FK | Ride reference |
| fatigue_score | REAL | Fatigue score |
| recovery_hours | REAL | Recovery hours |
| calories_per_km | REAL | Calories per km |
| efficiency_score | REAL | Efficiency score |

### Database Operations
```python
from bike_analyzer.backend.db.database import (
    init_db, save_ride, get_ride, get_all_rides,
    delete_ride, save_athlete, get_athlete,
    create_indices, backup_database
)

# Initialize
init_db()

# Save ride
ride_id = save_ride({
    "date": "2024-01-15",
    "distance_km": 25.5,
    "duration_minutes": 65
})

# Get ride
ride = get_ride(ride_id)

# Backup
backup_path = backup_database()
```

## Frontend

### Dashboard
Frontend is integrated in FastAPI and served at `/web/`:
- `bike_analyzer/backend/static/index.html` — Main page
- `bike_analyzer/backend/static/app.js` — JavaScript logic
- `bike_analyzer/backend/static/styles.css` — Dark theme styles

### JavaScript API Client
```javascript
const API_BASE = '/api/v1';

async function fetchRides() {
    const response = await fetch(`${API_BASE}/rides`);
    return response.json();
}

async function importGpx(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE}/import/gpx`, {
        method: 'POST',
        body: formData
    });
    return response.json();
}
```

## Deployment

### Environment Variables
| Variable | Default | Description |
|-----------|---------|-------------|
| DATABASE_URL | sqlite:///./rides.db | Database connection |
| API_HOST | 0.0.0.0 | API server host |
| API_PORT | 8000 | API server port |
| MAP_DEFAULT_ZOOM | 13 | Default map zoom |
| GOOGLE_MAPS_API_KEY | - | Google Maps API key |

### Docker
```dockerfile
# Custom Dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py", "api"]
```

### Azure Developer CLI
```bash
azd up        # Full deployment
azd deploy    # App-only deployment
```

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1-110 | ✅ | Core completed (130/135 steps) |
| 136-145 | ⏳ | Test coverage (in progress) |

See [ROADMAP.md](../ROADMAP.md) for full details.