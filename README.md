# BikeMaster

GPS-based cycling performance intelligence system. Import rides from GPX/FIT files, analyze power metrics, estimate calories and fatigue, visualize routes on interactive maps, and access everything through a REST API.

## Features

- **GPS ingestion** — Parse GPX and Garmin FIT files
- **Performance analytics** — Distance, speed, elevation, accelerations, pauses
- **Calorie estimation** — Physics + MET-based models
- **Fatigue scoring** — Weighted formula with recovery recommendations
- **Interactive maps** — Speed-colored routes via Folium/Leaflet
- **REST API** — 30+ endpoints for rides, analysis, charts, import, export, scores, benchmark, AI coach
- **Dashboard** — Dark-themed web UI with stats, ride list, and route map
- **Data export** — JSON and CSV formats

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.10+ |
| Database | SQLite (PostgreSQL-ready) |
| Maps | Folium, Leaflet.js |
| Analytics | NumPy, Pandas, Matplotlib |
| Parsers | gpxpy, fitparse |

## Quick Start

```bash
git clone https://github.com/ballales1984-wq/bikemaster.git
cd bikemaster
pip install -r requirements.txt
python main.py api
```

### Docker

```bash
docker compose up -d
# Open http://localhost:8000
```

Open [http://localhost:8000](http://localhost:8000) for the dashboard.

## Usage Modes

```bash
# API server (default) — dashboard + REST API
python main.py api

# Web server — standalone frontend
python main.py web

# CLI — demo analytics on sample data
python main.py cli
```

## API Endpoints

### Rides
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/rides` | Create ride |
| GET | `/api/v1/rides` | List rides (paginated) |
| GET | `/api/v1/rides/{id}` | Get ride details |
| DELETE | `/api/v1/rides/{id}` | Delete ride |
| POST | `/api/v1/rides/analyze` | Multi-ride summary |
| POST | `/api/v1/rides/{id}/analyze` | Single ride analysis |

### Import
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/import/gpx` | Upload GPX file |
| POST | `/api/v1/import/fit` | Upload FIT file |
| POST | `/api/v1/import/multiple` | Batch upload |
| GET | `/api/v1/import/google-fit/auth` | Get Google Fit OAuth URL |
| POST | `/api/v1/import/google-fit/token` | Exchange OAuth code for token |
| POST | `/api/v1/import/google-fit` | Import cycling activities from Google Fit |

### Export
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/rides/export/json` | Export as JSON |
| GET | `/api/v1/rides/export/csv` | Export as CSV |

### Charts
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/charts/speed/{id}` | Speed chart PNG |
| GET | `/api/v1/charts/elevation/{id}` | Elevation chart PNG |
| GET | `/api/v1/rides/{id}/map/google` | Google Static Map (requires GOOGLE_MAPS_API_KEY) |

### Athletes
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/athletes` | Create athlete profile |
| GET | `/api/v1/athletes/{id}` | Get athlete |
| PUT | `/api/v1/athletes/{id}` | Update athlete |
| POST | `/api/v1/athletes/{id}/metrics` | Save metrics |

### Scores
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/scores/athlete/{id}` | Get athlete scores |

### Benchmark
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/benchmark/compare` | Compare ride to benchmark |

### AI Coach
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/coach/workout` | Workout recommendations |
| GET | `/api/v1/coach/recovery` | Recovery recommendations |
| GET | `/api/v1/coach/trends` | Historical trends analysis |

### Knowledge Base
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/knowledge` | List topics |
| GET | `/api/v1/knowledge/search?q=...` | Search knowledge base |

## Generate Sample Data

```bash
python scripts/generate_sample_ride.py
```

## Run Tests

```bash
pytest
```

## Project Structure

```
bike_analyzer/
├── __init__.py          # Package facade
├── main.py              # Entry point
└── backend/
    ├── api/             # FastAPI routes + embedded dashboard
    ├── analytics/       # Calories, fatigue, charts, exports
    ├── db/              # SQLite CRUD layer
    ├── ingestion/       # GPX and FIT parsers
    ├── maps/            # Folium route renderer
    └── models/          # Domain models (Ride, GPSPoint, Segment)
frontend/                # Standalone dashboard
scripts/                 # Sample data generator
tests/                   # Unit tests
```

## Configuration

Copy `.env.example` to `.env` and set values:

```env
DATABASE_URL=sqlite:///./rides.db
API_HOST=0.0.0.0
API_PORT=8000
GOOGLE_MAPS_API_KEY=your_api_key_here
```

## Deployment

### Docker

```bash
docker build -t bikemaster .
docker run -p 8000:8000 bikemaster
```

### Docker Compose

```bash
docker-compose up -d
```

### Azure

```bash
azd up
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the 100-step development plan.

## License

MIT
