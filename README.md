# BikeMaster

GPS-based cycling performance intelligence system. Import GPS data, analyze rides, and optimize your cycling performance with actionable insights.

## Features

- **GPS Route Processing**: Clean noisy GPS data, detect pauses, compute segment statistics
- **Performance Analytics**: Calorie estimation (MET & physics models), fatigue scoring, recovery recommendations
- **Interactive Maps**: Speed-colored route visualization with Folium (Strava-style)
- **REST API**: FastAPI endpoints for ride data management
- **Database Storage**: SQLite for ride persistence (PostgreSQL ready)

## Quick Start

```bash
pip install -r requirements.txt
python -m bike_analyzer.main
```

## Architecture

```
bike_analyzer/
├── backend/
│   ├── api/          # FastAPI endpoints
│   ├── ingestion/    # GPS data import (GPX, FIT)
│   ├── processing/   # GPS cleaning + routing
│   ├── analytics/    # Performance metrics, fatigue model
│   ├── maps/         # Folium route visualization
│   ├── models/       # Domain models (Ride, GPSPoint, Segment)
│   └── db/           # SQLite database layer
├── frontend/
│   └── dashboard/    # HTML output templates
└── tests/
```

## API Usage

```bash
uvicorn bike_analyzer.backend.api.app_factory:create_app --reload
```

```bash
curl -X POST http://localhost:8000/api/v1/rides/analyze \
  -H "Content-Type: application/json" \
  -d '[{"date": "2024-06-01", "distance_km": 25, "duration_minutes": 60, "avg_speed_kmh": 25}]'
```

## License

MIT License