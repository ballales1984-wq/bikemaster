# API Documentation - BikeMaster v1.0

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
The API currently does not require authentication. For production use, API key or JWT token is recommended.

---

## Rides

### Create Ride
```http
POST /rides
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
    {"lat": 45.4408, "lon": 12.3155, "timestamp": "2024-01-15T09:00:00Z"},
    {"lat": 45.4410, "lon": 12.3160, "timestamp": "2024-01-15T09:01:00Z"}
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

### Ride Details
```http
GET /rides/1
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
  "fatigue_score": 4.2,
  "calories_per_km": 25
}
```

### Delete Ride
```http
DELETE /rides/1
```

**Response:**
```json
{"deleted": true}
```

---

## Import

### Upload GPX File
```http
POST /import/gpx
Content-Type: multipart/form-data

file: <file.gpx>
```

**Response:**
```json
{
  "id": 1,
  "date": "2024-01-15",
  "distance_km": 25.5,
  "duration_minutes": 65,
  "avg_speed_kmh": 22.9
}
```

### Upload FIT File
```http
POST /import/fit
Content-Type: multipart/form-data

file: <file.fit>
```

### Batch Upload
```http
POST /import/multiple
Content-Type: multipart/form-data

files: [<file1.gpx>, <file2.fit>]
```

**Response:**
```json
{
  "imported": [...],
  "count": 2
}
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

All chart endpoints return PNG images.

### Speed Chart
```http
GET /charts/speed/1
```

### Elevation Chart
```http
GET /charts/elevation/1
```

### Duration Chart
```http
GET /charts/duration
```

### Interactive Map
```http
GET /rides/1/map
```

Returns URL to Folium HTML map.

### Google Static Map
```http
GET /rides/1/map/google
```

Returns PNG map image. Requires `GOOGLE_MAPS_API_KEY`.

---

## Athletes

### Create Athlete
```http
POST /athletes
Content-Type: application/json

{
  "name": "Mario Rossi",
  "age": 35,
  "weight_kg": 75,
  "height_cm": 175,
  "years_active": 3,
  "weekly_sessions": 4
}
```

### Get Athlete
```http
GET /athletes/1
```

### Update Athlete
```http
PUT /athletes/1
Content-Type: application/json

{
  "weight_kg": 74,
  "monthly_hours": 25
}
```

---

## Scores

### Athlete Scores
```http
GET /scores/athlete/1
```

**Response:**
```json
{
  "athlete": {
    "id": 1,
    "name": "Mario Rossi",
    "experience_level": "Amateur"
  },
  "scores": {
    "performance_score": 67,
    "endurance_score": 72,
    "efficiency_score": 81,
    "experience_level": "Amateur"
  }
}
```

---

## Benchmark

### Compare to Benchmark
```http
POST /benchmark/compare
Content-Type: application/json

{
  "distance_km": 25.5,
  "avg_speed_kmh": 22.9,
  "duration_hours": 1.08
}
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
```

### Recovery Recommendations
```http
GET /coach/recovery?fatigue_score=6.5&ride_id=1
```

### Historical Trends
```http
GET /coach/trends
```

**Response:**
```json
{
  "trend": "improving",
  "avg_distance_trend": 5.2,
  "avg_speed_trend": 1.8,
  "advice": "Continue with this routine, you're improving consistently"
}
```

---

## Knowledge Base

### List Topics
```http
GET /knowledge
```

**Response:**
```json
{
  "topics": ["cardio", "training", "recovery"]
}
```

### Search
```http
GET /knowledge/search?q=intervals
```

**Response:**
```json
{
  "results": [
    {
      "topic": "training",
      "content": "High-intensity intervals..."
    }
  ]
}
```

---

## Admin

### System Stats
```http
GET /admin/stats
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
```

Returns `backup_YYYYMMDD_HHMMSS.db` file.

### Create Indexes
```http
POST /admin/indexes
```

### Reset Demo
```http
POST /admin/reset-demo
```

---

## Common Use Cases

### Import Garmin Route
```bash
# 1. Upload FIT file
curl -X POST -F "file=@ride.fit" http://localhost:8000/api/v1/import/fit

# 2. Check imported ride
curl http://localhost:8000/api/v1/rides/1

# 3. Get map
curl http://localhost:8000/api/v1/rides/1/map
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
curl http://localhost:8000/api/v1/scores/athlete/1

# 2. Get trends
curl http://localhost:8000/api/v1/coach/trends
```