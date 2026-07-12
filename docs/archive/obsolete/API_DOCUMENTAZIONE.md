# Documentazione API - BikeMaster v1.0

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Attualmente l'API non richiede autenticazione. Per l'uso in produzione è consigliato aggiungere API key o JWT token.

---

## Rides

### Crea Ride
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

### Lista Rides
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

### Dettaglio Ride
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

---

## Importazione

### Upload File GPX
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

### Upload File FIT
```http
POST /import/fit
Content-Type: multipart/form-data

file: <file.fit>
```

### Upload Multiplo
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

## Esportazione

### Esporta JSON
```http
GET /rides/export/json
```

**Response:** File `rides.json` con array di tutte le rides.

### Esporta CSV
```http
GET /rides/export/csv
```

**Response:** File `rides.csv` con header e righe dati.

---

## Grafici

Tutti gli endpoint grafico restituiscono immagini PNG.

### Grafico Velocità
```http
GET /charts/speed/1
```

### Grafico Elevazione
```http
GET /charts/elevation/1
```

### Grafico Durata
```http
GET /charts/duration
```

### Mappa Interattiva
```http
GET /rides/1/map
```
**Response:** URL all'HTML della mappa Folium.

### Google Static Map
```http
GET /rides/1/map/google
```

---

## Atleti

### Crea Atleta
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

### Dettaglio Atleta
```http
GET /athletes/1
```

### Aggiorna Atleta
```http
PUT /athletes/1
Content-Type: application/json

{
  "weight_kg": 74,
  "weekly_sessions": 5
}
```

---

## Punteggi

### Punteggi Atleta
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

### Confronto Benchmark
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
  "advice": "Continua con questa routine, stai migliorando costantemente"
}
```

---

## Knowledge Base

### Lista Argomenti
```http
GET /knowledge
```

**Response:**
```json
{
  "topics": ["cardio", "training", "recovery"]
}
```

### Ricerca
```http
GET /knowledge/search?q=intervalli
```

**Response:**
```json
{
  "results": [
    {
      "topic": "training",
      "content": "Gli intervalli ad alta intensità..."
    }
  ]
}
```

---

## Admin

### Statistiche Sistema
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

### Backup Database
```http
GET /admin/backup
```
**Response:** File `backup_YYYYMMDD_HHMMSS.db`.

### Reset Demo
```http
POST /admin/reset-demo
```

---

## Casi d'Uso Comuni

### Importare e Analizzare un Percorso Garmin
```bash
# 1. Upload file FIT
curl -X POST -F "file=@ride.fit" http://localhost:8000/api/v1/import/fit

# 2. Verifica ride importata
curl http://localhost:8000/api/v1/rides/1

# 3. Ottieni mappa
curl http://localhost:8000/api/v1/rides/1/map
```

### Generare Report Settimanale
```bash
# 1. Lista ultime rides
curl "http://localhost:8000/api/v1/rides?page=1&page_size=50"

# 2. Esporta CSV
curl http://localhost:8000/api/v1/rides/export/csv > weekly_rides.csv
```

### Valutare Progressi
```bash
# 1. Punteggi atleta
curl http://localhost:8000/api/v1/scores/athlete/1

# 2. Trend storici
curl http://localhost:8000/api/v1/coach/trends
```