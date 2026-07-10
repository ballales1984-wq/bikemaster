# API Documentation - BikeMaster v1.3

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

The API supports multiple authentication methods:
- **JWT Token** — `Authorization: Bearer <token>` (via `/auth/login`)
- **Google OAuth2** — `/auth/google` → `/auth/google/callback`
- **Strava OAuth2 + PKCE** — `/import/strava/auth` → `/import/strava/callback`

Public endpoints (no auth required) are marked with `[PUBLIC]`.

---

## Health

### Health Check
```http
GET /health
```

### Health Check (Detailed)
```http
GET /health/detailed
[PUBLIC]
```

---

## Authentication

### Login (JWT)
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=mypassword
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_id": "1",
  "email": "user@example.com"
}
```

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "Mario Rossi"
}
```

### Google OAuth URL
```http
GET /auth/google
[PUBLIC]
```
Redirects to Google OAuth2 consent page.

### Google OAuth Callback
```http
POST /auth/google/callback
Content-Type: application/json

{
  "code": "4/0AX4...",
  "state": "optional_state"
}
[PUBLIC]
```

### Strava OAuth URL
```http
GET /import/strava/auth
Authorization: Bearer <token>
```
Returns authorization URL + state + code_verifier (PKCE).

### Strava OAuth Callback
```http
POST /import/strava/callback
Authorization: Bearer <token>
Content-Type: application/json

{
  "code": "strava_code",
  "code_verifier": "verifier_value"
}
```
Exchanges the authorization code for tokens and stores them in `strava_tokens`.

---

## Rides CRUD

### Create Ride
```http
POST /rides
Authorization: Bearer <token>
Content-Type: application/json

{
  "date": "2024-01-15",
  "distance_km": 25.5,
  "duration_minutes": 65,
  "avg_speed_kmh": 22.9,
  "weight_kg": 70,
  "calories": 650,
  "heart_rate_avg": 145,
  "elevation_gain_m": 150,
  "gps_points": [
    {"lat": 45.4408, "lon": 12.3155, "timestamp": "2024-01-15T09:00:00"}
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "date": "2024-01-15",
  "distance_km": 25.5,
  "duration_minutes": 65,
  "avg_speed_kmh": 22.9,
  "calories": 650,
  "calories_per_km": 0,
  "fatigue_score": 0
}
```

### List Rides
```http
GET /rides?page=1&page_size=20&sort=date
[PUBLIC]
```

**Response:**
```json
{
  "rides": [...],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

### Get Ride Detail
```http
GET /rides/1
Authorization: Bearer <token>
```
Returns ride with fatigue score, calories per km, and full details.

### Update Ride
```http
PUT /rides/1
Authorization: Bearer <token>
Content-Type: application/json
```

### Delete Ride
```http
DELETE /rides/1
Authorization: Bearer <token>
```

**Response:**
```json
{"deleted": true}
```

### Ride Count
```http
GET /rides/count
[PUBLIC]
```

### Analyze Multiple Rides
```http
POST /rides/analyze
Content-Type: application/json

{
  "ride_ids": [1, 2, 3]
}
[PUBLIC]
```

### Analyze Single Ride
```http
POST /rides/1/analyze
Authorization: Bearer <token>
```

---

## Import

### Upload GPX File
```http
POST /import/gpx
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <file.gpx>
```

### Upload FIT File
```http
POST /import/fit
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <file.fit>
```

### Batch Upload
```http
POST /import/multiple
Authorization: Bearer <token>
Content-Type: multipart/form-data

files: [<file1.gpx>, <file2.fit>]
```

### Google Fit Auth URL
```http
GET /import/google-fit/auth
[PUBLIC]
```

### Google Fit Token Exchange
```http
POST /import/google-fit/token
Content-Type: application/json

{
  "code": "google_auth_code",
  "redirect_uri": "http://localhost:8000/api/v1/import/google-fit/callback"
}
[PUBLIC]
```

### Import from Google Fit
```http
POST /import/google-fit
Authorization: Bearer <token>
```

### Connect Strava (OAuth2 + PKCE)
```http
GET /import/strava/auth
Authorization: Bearer <token>
```

### Strava OAuth Callback
```http
POST /import/strava/callback
Authorization: Bearer <token>
Content-Type: application/json

{
  "code": "strava_code",
  "code_verifier": "verifier_value"
}
```

### Sync All Strava Activities
```http
POST /import/strava/sync
Authorization: Bearer <token>
```
Query param `background=false` runs the import inline and returns `{imported, total_fetched, rides}`.

### Disconnect Strava
```http
DELETE /import/strava/disconnect
Authorization: Bearer <token>
```

---

## Export

### JSON Export
```http
GET /rides/export/json
```

Returns `rides.json` file with all rides array.

### CSV Export
```http
GET /rides/export/csv
```

Returns `rides.csv` file with headers and data rows.

---

## Charts

### Speed Chart
```http
GET /charts/speed/1
```

Returns PNG image of speed chart.

### Elevation Chart
```http
GET /charts/elevation/1
```

Returns PNG image of elevation chart.

### Distance Chart
```http
GET /charts/distance/1
```

Returns PNG image of distance chart.

### Duration Chart
```http
GET /charts/duration
```

Returns PNG image summarizing ride durations.

---

## Athletes

### Create Athlete
```http
POST /athletes
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Mario Rossi",
  "age": 35,
  "weight_kg": 75,
  "height_cm": 175,
  "years_active": 3,
  "weekly_sessions": 4,
  "ftp_watts": 250
}
```

### List Athletes
```http
GET /athletes
[PUBLIC]
```

### Get Athlete
```http
GET /athletes/1
Authorization: Bearer <token>
```

### Update Athlete
```http
PUT /athletes/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "weight_kg": 74,
  "monthly_hours": 25,
  "ftp_watts": 255
}
```

### Save Athlete Metrics
```http
POST /athletes/1/metrics
Authorization: Bearer <token>
```

---

## Scores & Benchmark

### Athlete Scores
```http
GET /scores/athlete/1
Authorization: Bearer <token>
```

**Response:**
```json
{
  "athlete": {"id": 1, "name": "Mario Rossi", "experience_level": "Amateur"},
  "scores": {
    "performance_score": 67,
    "endurance_score": 72,
    "efficiency_score": 81,
    "experience_level": "Amateur"
  }
}
```

### Compare to Benchmark
```http
POST /benchmark/compare
Content-Type: application/json

{
  "distance_km": 25.5,
  "avg_speed_kmh": 22.9,
  "duration_hours": 1.08
}
[PUBLIC]
```

**Response:**
```json
{
  "percentile": 65,
  "category": "Amateur",
  "comparison": {
    "vs_benchmark": "+12%",
    "benchmark_avg_speed": 20.5,
    "benchmark_distance": 25.0
  }
}
```

---

## AI Coach

### Workout Recommendations
```http
GET /coach/workout?athlete_id=1
Authorization: Bearer <token>
```

### Recovery Recommendations
```http
GET /coach/recovery?fatigue_score=6.5&ride_id=1
[PUBLIC]
```

### Historical Trends
```http
GET /coach/trends
Authorization: Bearer <token>
```

### Full Report
```http
GET /coach/full
Authorization: Bearer <token>
```

### Chat with AI Coach
```http
POST /coach/chat
Content-Type: application/json

{
  "message": "Come posso migliorare la mia resistenza?",
  "athlete_id": 1
}
[PUBLIC]
```

### Chat History
```http
GET /coach/history?athlete_id=1
[PUBLIC]
```

---

## Knowledge Base

### List Topics
```http
GET /knowledge
[PUBLIC]
```

**Response:**
```json
{
  "topics": ["cardio", "training", "recovery", "nutrition"]
}
```

### Semantic Search
```http
GET /knowledge/search?q=intervals
[PUBLIC]
```

**Response:**
```json
{
  "results": [
    {
      "topic": "training",
      "section": "hiit",
      "content": "High-intensity intervals improve VO2max...",
      "similarity": 0.85
    }
  ]
}
```

### Knowledge Base Stats
```http
GET /knowledge/stats
[PUBLIC]
```

### Reload Knowledge Index
```http
POST /knowledge/reload
[PUBLIC]
```

---

## Training

### Training Load (RSS/TSS)
```http
GET /training/load
Authorization: Bearer <token>
```

### Training Status
```http
GET /training/status
Authorization: Bearer <token>
```

### Training Summary
```http
GET /training/summary
Authorization: Bearer <token>
```

### Training Goals
```http
GET /training/goals
Authorization: Bearer <token>
```

### Generate Workout
```http
GET /training/workouts/generate?athlete_id=1&type=endurance
Authorization: Bearer <token>
```

### Granfondo Plan
```http
GET /training/granfondo/plan?target_date=2024-10-15&distance_km=150
Authorization: Bearer <token>
```

---

## Weather

### Current Weather
```http
GET /weather?lat=45.44&lon=12.31
[PUBLIC]
```

### Weather Forecast
```http
GET /weather/forecast?lat=45.44&lon=12.31&days=7
[PUBLIC]
```

---

## Maps

### Generate Folium Map
```http
POST /rides/1/map
Authorization: Bearer <token>
```

### Google Static Map
```http
GET /rides/1/map/google?colored=true&zoom=14&size=640x480
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| colored | boolean | false | Color by speed (green >=25, yellow 15-25, red <15) |
| zoom | integer | 13 | Map zoom (1-21) |
| size | string | 640x480 | Image dimensions (max 640x640 free tier) |

**Response:** PNG image. Requires `GOOGLE_MAPS_API_KEY`.

**Error Responses:**
| Status | Code | Description |
|:---:|:---|:---|
| 500 | NO_API_KEY | GOOGLE_MAPS_API_KEY not configured |
| 404 | RIDE_NOT_FOUND | Ride ID does not exist |
| 500 | NO_GPS_POINTS | Ride has no GPS data |

### Nearby Places
```http
GET /maps/places/nearby?lat=45.44&lon=12.31&radius=1000
[PUBLIC]
```

### Search Places
```http
GET /maps/places/search?q=rifugio&lat=45.44&lon=12.31
[PUBLIC]
```

---

## Traffic Safety

### Analyze Route Safety
```http
POST /traffic/analyze
Content-Type: application/json

{
  "gps_points": [
    {"lat": 45.44, "lon": 12.31},
    {"lat": 45.45, "lon": 12.32}
  ],
  "incidents": []
}
[PUBLIC]
```

**Response:**
```json
{
  "risk_score": 0.72,
  "label": "low_risk",
  "advice": "Percorso sicuro",
  "has_bike_infrastructure": true,
  "route_length_km": 5.2,
  "dominant_road_types": [["residential", 3], ["cycleway", 2]]
}
```

### Fetch Bike Lanes
```http
GET /traffic/bike-lanes?lat=45.44&lon=12.31&radius=5000
[PUBLIC]
```

### Fetch Road Data
```http
GET /traffic/road-data?lat=45.44&lon=12.31&radius=5000
[PUBLIC]
```

---

## Admin

### System Stats
```http
GET /admin/stats
[PUBLIC]
```

**Response:**
```json
{
  "rides_count": 150,
  "total_km": 3250.5,
  "total_duration_hours": 125.3,
  "db_size_bytes": 45216
}
```

### Database Backup
```http
GET /admin/backup
Authorization: Bearer <token>
```

Returns `backup_YYYYMMDD_HHMMSS.db` file.

### Create Indexes
```http
POST /admin/indexes
[PUBLIC]
```

### Reset Demo Data
```http
POST /admin/reset-demo
[PUBLIC]
```

---

## Common Use Cases

### Import Garmin Ride
```bash
# 1. Upload FIT file
curl -X POST -F "file=@ride.fit" http://localhost:8000/api/v1/import/fit \
  -H "Authorization: Bearer <token>"

# 2. Check imported ride
curl http://localhost:8000/api/v1/rides/1 \
  -H "Authorization: Bearer <token>"

# 3. Get map
curl http://localhost:8000/api/v1/rides/1/map \
  -H "Authorization: Bearer <token>"
```

### Import from Strava
```bash
curl -X POST http://localhost:8000/api/v1/import/strava \
  -H "Authorization: Bearer <token>"
```

### Generate Weekly Report
```bash
# 1. Get recent rides
curl "http://localhost:8000/api/v1/rides?page=1&page_size=50"

# 2. Export CSV
curl http://localhost:8000/api/v1/rides/export/csv > weekly_rides.csv
```

### Evaluate Progress
```bash
# 1. Get athlete scores
curl http://localhost:8000/api/v1/scores/athlete/1 \
  -H "Authorization: Bearer <token>"

# 2. Get trends
curl http://localhost:8000/api/v1/coach/trends \
  -H "Authorization: Bearer <token>"
```

### Chat with AI Coach
```bash
curl -X POST http://localhost:8000/api/v1/coach/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Come posso migliorare la mia resistenza?", "athlete_id": 1}'
```
