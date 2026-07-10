# Guida Utente BikeMaster

Sistema di intelligenza per le performance ciclistiche basato su GPS. Importa percorsi da file GPX/FIT, analizza metriche di potenza, stimare calorie e affaticamento, visualizza percorsi su mappe interattive, e accedi a tutto tramite API REST.

## Indice

- [Introduzione](#introduzione)
- [Installazione](#installazione)
- [Avvio Rapido](#avvio-rapido)
- [API Endpoints](#api-endpoints)
- [Modelli di Dati](#modelli-di-dati)
- [Come Funiona l'Analisi](#come-funiona-lanalisi)
- [Integrazione Google Fit](#integrazione-google-fit)
- [Mappe e Visualizzazioni](#mappe-e-visualizzazioni)
- [AI Coach e Knowledge Base](#ai-coach-e-knowledge-base)
- [Testing](#testing)
- [Deployment](#deployment)
- [Struttura del Progetto](#struttura-del-progetto)

## Introduzione

BikeMaster è un'applicazione completa per:
- **Importazione GPX/FIT** — Parsing di file da dispositivi Garmin, Wahoo, e app di fitness
- **Analisi Performance** — Distanza, velocità, elevazione, accelerazioni, pause
- **Stima Calorie** — Modelli fisici + MET
- **Punteggio Affaticamento** — Formula pesata con raccomandazioni di recupero
- **Mappe Interattive** — Percorsi colorati per velocità con Folium/Leaflet
- **API REST** — 40+ endpoint per gestione rides, analisi, grafici, import/export
- **Dashboard Web** — Interfaccia dark-themed con statistiche e mappe
- **Esportazione Dati** — Formati JSON e CSV

## Installazione

### Prerequisiti
- Python 3.10 o superiore
- pip (gestore pacchetti)

### Installazione Dipendenze
```bash
git clone https://github.com/ballales1984-wq/bikemaster.git
cd bikemaster
pip install -r requirements.txt
```

### Variabili d'Ambiente
Copia `.env.example` a `.env`:
```bash
cp .env.example .env
```

Modifica `.env` con le tue credenziali:
```env
DATABASE_URL=sqlite:///./rides.db
API_HOST=0.0.0.0
API_PORT=8000
GOOGLE_MAPS_API_KEY=la_tua_api_key_google_maps
```

## Avvio Rapido

### Modalità API Server (default)
```bash
python main.py api
# Oppure con reload per sviluppo
python main.py api --reload
```

### Modalità Web Frontend
```bash
python main.py web
```

### Modalità CLI
```bash
python main.py cli
```

Apri il browser su [http://localhost:8000](http://localhost:8000) per la dashboard.

## API Endpoints

### Health Check
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| GET | `/api/v1/health` | Stato base del servizio |
| GET | `/api/v1/health/detailed` | Stato dettagliato con statistiche DB |

### Rides (CRUD)
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| POST | `/api/v1/rides` | Crea nuova ride |
| GET | `/api/v1/rides` | Lista rides (paginata, ordinabile) |
| GET | `/api/v1/rides/{id}` | Dettaglio ride con analytics |
| DELETE | `/api/v1/rides/{id}` | Elimina ride |
| POST | `/api/v1/rides/analyze` | Analisi multi-ride |
| POST | `/api/v1/rides/{id}/analyze` | Analisi singola ride |

**Parametri query per `/api/v1/rides`:**
- `page` — Numero pagina (default: 1)
- `page_size` — Dimensione pagina (1-100, default: 20)
- `sort` — Ordinamento: `date`, `distance`, `duration` (default: `date`)

### Importazione
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| POST | `/api/v1/import/gpx` | Upload file GPX |
| POST | `/api/v1/import/fit` | Upload file FIT |
| POST | `/api/v1/import/multiple` | Upload multiplo (GPX/FIT) |
| GET | `/api/v1/import/google-fit/auth` | URL OAuth Google Fit |
| POST | `/api/v1/import/google-fit/token` | Scambio codice OAuth |
| POST | `/api/v1/import/google-fit` | Importa attività Google Fit |
| GET | `/api/v1/import/strava/auth` | URL OAuth Strava (PKCE) |
| POST | `/api/v1/import/strava/callback` | Scambio codice OAuth Strava |
| POST | `/api/v1/import/strava/sync` | Importa/sincronizza attività Strava |
| DELETE | `/api/v1/import/strava/disconnect` | Disconnetti Strava |

### Esportazione
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| GET | `/api/v1/rides/export/json` | Esporta in JSON |
| GET | `/api/v1/rides/export/csv` | Esporta in CSV |

### Grafici
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| GET | `/api/v1/charts/speed/{id}` | Grafico velocità PNG |
| GET | `/api/v1/charts/elevation/{id}` | Grafico elevazione PNG |
| GET | `/api/v1/charts/duration` | Grafico durata PNG |
| GET | `/api/v1/charts/distance/{id}` | Grafico distanza PNG |
| GET | `/api/v1/rides/{id}/map` | Mappa interattiva Folium |
| GET | `/api/v1/rides/{id}/map/google` | Google Static Map PNG |

### Atleti
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| POST | `/api/v1/athletes` | Crea profilo atleta |
| GET | `/api/v1/athletes/{id}` | Dettaglio atleta |
| PUT | `/api/v1/athletes/{id}` | Aggiorna profilo atleta |
| POST | `/api/v1/athletes/{id}/metrics` | Salva metriche atleta |

### Punteggi
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| GET | `/api/v1/scores/athlete/{id}` | Punteggi atleta (performance, endurance, efficiency) |

### Benchmark
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| POST | `/api/v1/benchmark/compare` | Confronto atleta vs benchmark |

### AI Coach
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| GET | `/api/v1/coach/workout` | Raccomandazioni allenamento |
| GET | `/api/v1/coach/recovery` | Raccomandazioni recupero |
| GET | `/api/v1/coach/trends` | Analisi trend storici |

### Knowledge Base
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| GET | `/api/v1/knowledge` | Lista argomenti disponibili |
| GET | `/api/v1/knowledge/search?q=...` | Ricerca nella knowledge base |

### Admin
| Metodo | Endpoint | Descrizione |
|--------|----------|-----------|
| GET | `/api/v1/admin/backup` | Backup database |
| POST | `/api/v1/admin/indexes` | Crea indici DB |
| GET | `/api/v1/admin/stats` | Statistiche sistema |
| POST | `/api/v1/admin/reset-demo` | Reset dati demo |
| GET | `/api/v1/rides/count` | Conteggio rides |

## Modelli di Dati

### Ride
```python
@dataclass
class Ride:
    id: Optional[int]           # ID univoco
    athlete_id: Optional[int]     # Riferimento atleta
    date: str                     # Data (ISO format)
    distance_km: float            # Distanza in km
    duration_minutes: float       # Durata in minuti
    avg_speed_kmh: float          # Velocità media km/h
    weight_kg: float              # Peso atleta (default: 70kg)
    calories: float               # Calorie consumate
    heart_rate_avg: Optional[float]# Frequenza cardiaca media
    elevation_gain_m: Optional[float] # Metri di salita
    gps_points: Optional[List[GPSPoint]] # Lista punti GPS
    created_at: Optional[str]     # Timestamp creazione
```

### GPSPoint
```python
@dataclass
class GPSPoint:
    lat: float                  # Latitudine
    lon: float                  # Longitudine
    timestamp: datetime         # Timestamp punto
    altitude: Optional[float]   # Altitudine in metri
    speed: Optional[float]      # Velocità in m/s
```

### AthleteProfile
```python
@dataclass
class AthleteProfile:
    id: Optional[int]
    name: str                       # Nome atleta
    age: int = 30                   # Età
    weight_kg: float = 70.0         # Peso (kg)
    height_cm: Optional[float]        # Altezza (cm)
    fat_percentage: Optional[float]   # Massa grassa (%)
    years_active: int = 1             # Anni di attività
    weekly_sessions: int = 3          # Sessioni settimanali
    monthly_hours: float = 0.0        # Ore mensili
    annual_hours: float = 0.0         # Ore annuali
    experience_level: str = "Beginner"  # Beginner, Amateur, Intermediate, Advanced, Elite
```

## Come Funiona l'Analisi

### Processori Principali

1. **GPS Parser** (`ingestion/gps_parser.py`)
   - Parse file GPX con `gpxpy`
   - Parse file FIT con `fitparse`
   - Converte punti in oggetti Ride

2. **Analytics** (`analytics/analytics.py`)
   - `calculate_summary()` — Statistiche aggregate su più rides
   - `analyze_ride()` — Analisi singola ride
   - `build_segments()` — Segmentazione percorso
   - `calculate_pauses()` — Rilevamento pause
   - `calculate_accelerations()` — Rilevamento accelerazioni/rallentamenti

3. **Calorie** (`analytics/calories.py`)
   - Metodo fisico: `estimate_calories(ride, method="physics")`
   - Metodo MET: `estimate_calories(ride, method="met")`

4. **Fatigue** (`analytics/fatigue.py`)
   - `calculate_fatigue_score(ride)` — Punteggio affaticamento 0-10
   - `estimate_recovery_hours(ride)` — Ore recupero stimte
   - `get_recovery_recommendation(ride)` — Raccomandazioni testuali

5. **Performance** (`analytics/performance.py`)
   - `calculate_performance_score(ride)` — Punteggio prestazioni
   - `calculate_endurance_score(rides)` — Punteggio resistenza
   - `calculate_efficiency_score(ride)` — Punteggio efficienza
   - `get_experience_level(profile)` — Livello esperienza atleta

## Integrazione Google Fit

### Flusso OAuth2
1. Richiedi URL autorizzazione: `GET /api/v1/import/google-fit/auth?client_id=...`
2. Reindirizzi utente a Google per autorizzazione
3. Ricevi callback con codice di autorizzazione
4. Scambia codice per token: `POST /api/v1/import/google-fit/token`
5. Importa dati: `POST /api/v1/import/google-fit` con access_token

### Scope Richiesti
- `https://www.googleapis.com/auth/fitness.activity.read`
- `https://www.googleapis.com/auth/fitness.body.read`

## Mappe e Visualizzazioni

### Folium (Offline)
- `create_route_map(points)` — Genera HTML mappa interattiva
- Colorazione per velocità (blu→rosso)
- Markers start/end

### Google Static Maps (Online)
- Richiede `GOOGLE_MAPS_API_KEY` in `.env`
- `create_google_static_map(points, api_key)` — PNG mappa
- Markers posizione iniziale/finale

### Grafici Matplotlib
- Velocità nel tempo
- Elevazione nel tempo
- Distanza percorsa
- Durata attività

## AI Coach e Knowledge Base

### Knowledge Base (`/knowledge_base/`)
File markdown con contenuti sportivi:
- `training.md` — Teoria allenamento
- `recovery.md` — Recupero e riposo
- `cardio.md` — Teoria cardiovascolare

### AI Coach (`analytics/ai_coach.py`)
- `generate_workout_recommendations(rides, athlete)` — Piano allenamento
- `generate_recovery_recommendations(ride, fatigue)` — Piano recupero
- `analyze_historical_trends(rides)` — Trend storici

## Testing

```bash
# Esegui tutti i test
pytest

# Con coverage
pytest --cov=bike_analyzer

# Test specifico
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
# Apri http://localhost:8000
```

### Azure
```bash
azd up
```

## Struttura del Progetto

```
bike_analyzer/
├── __init__.py              # Package facade
├── main.py                  # Entry point unificato
└── backend/
    ├── api/
    │   ├── app_factory.py   # Configurazione FastAPI
    │   ├── routes.py        # 40+ endpoint API
    │   └── schemas.py       # Pydantic models
    ├── analytics/
    │   ├── analytics.py     # Statistiche base
    │   ├── calories.py      # Stima calorie
    │   ├── fatigue.py       # Punteggio affaticamento
    │   ├── performance.py   # Punteggi prestazioni
    │   ├── benchmark.py     # Confronto atleti
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
    │   └── models.py        # Domain models (Ride, GPSPoint, etc.)
    └── processing/
        └── processing.py    # Segmentazione/processing
frontend/
    └── dashboard.py         # Standalone dashboard
scripts/
    ├── generate_sample_ride.py   # Generatore dati demo
    └── demo_map.py              # Demo mappe
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

## Contribuire

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/nuova-funzionalita`)
3. Commit changes (`git commit -m 'Aggiungi nuova funzionalità'`)
4. Push branch (`git push origin feature/nuova-funzionalita`)
5. Apri Pull Request

## Troubleshooting

### Problemi Comuni

**Errore: "No GPS points for this ride"**
- Verificare che il file GPX/FIT sia valido
- Controllare che abbia punti di tracciamento

**Errore: "GOOGLE_MAPS_API_KEY not configured"**
- Aggiungere la chiave API in `.env`
- Verificare che l'API Google Static Maps sia abilitata

**Database errors**
- Eseguire `POST /api/v1/admin/indexes` per ottimizzare le query