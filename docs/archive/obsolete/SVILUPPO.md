# Documentazione Sviluppatori - BikeMaster

## Architettura

BikeMaster segue un'architettura a strati con separazione delle responsabilità:

```
┌─────────────────────────────────────┐
│           Presentazione             │
│  (Dashboard HTML/JS + API Routes)    │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│         Business Logic              │
│  (Analytics, Performance, AI Coach) │
├─────────────────────────────────────┤
│          Data Access                │
│      (SQLite Database Layer)          │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│         Domain Models              │
│    (Ride, GPSPoint, Athlete)       │
└─────────────────────────────────────┘
```

## Stack Tecnologico

| Componente | Tecnologia | Versione |
|------------|------------|----------|
| Backend | FastAPI | >=0.110.0 |
| Database | SQLite | integrato |
| Frontend | HTML/JS + Folium | - |
| Maps | Folium, Leaflet.js | >=0.16.0 |
| Analytics | NumPy, Pandas, Matplotlib | >=1.26.4, >=2.2.0 |
| Parsers | gpxpy, fitparse | >=1.6.2, >=1.2.0 |
| AI | Groq SDK | >=0.4.0 |

## Estensione Backend

### Aggiungere Nuovo Endpoint

1. Modifica `bike_analyzer/backend/api/routes.py`:
```python
@router.get("/nuova/funzionalita")
async def nuova_funzionalita(parametro: str):
    # Logica qui
    return {"result": risultato}
```

2. Registra router in `app_factory.py`:
```python
# Il router è già incluso tramite include_router
```

### Aggiungere Analisi

1. Crea funzione in `analytics/`:
```python
# bike_analyzer/backend/analytics/nuova_analisi.py
def calcola_metrica(ride: Ride) -> float:
    # Implementazione
    return valore
```

2. Espone tramite API:
```python
@router.get("/rides/{ride_id}/nuova-metrica")
async def get_nuova_metrica(ride_id: int):
    ride = Ride(**get_ride(ride_id))
    return {"metric": calcola_metrica(ride)}
```

### Aggiungere Modello Dati

Modifica `bike_analyzer/backend/models/models.py`:
```python
@dataclass
class NuovoModello:
    campo1: str
    campo2: int
    # ...
```

## Test

### Struttura Test
```
tests/
├── test_analytics.py       # Test analytics base
├── test_models.py          # Test modelli dati
├── test_database.py        # Test operazioni DB
├── test_performance.py     # Test performance engine
├── test_edge_cases.py      # Test casi limite
└── test_ai_coach.py        # Test AI coach
```

### Scrivere Test
```python
# tests/test_nuovo_modulo.py
import pytest
from bike_analyzer.backend.analytics.nuovo_modulo import funzione_da_testare

def test_funzione_base():
    assert funzione_da_testare(input) == expected

def test_funzione_edge_case():
    with pytest.raises(ValueError):
        funzione_da_testare(invalid_input)
```

### Eseguire Test
```bash
pytest                    # Tutti i test
pytest -v                 # Verbose
pytest --cov=bike_analyzer # Con coverage
pytest tests/test_models.py # Singolo file
```

## Database

### Schema Tabelle

**rides**
| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| id | INTEGER PK | Chiave primaria |
| athlete_id | INTEGER FK | Riferimento atleta |
| date | TEXT | Data attività |
| distance_km | REAL | Distanza km |
| duration_minutes | REAL | Durata minuti |
| avg_speed_kmh | REAL | Velocità media |
| weight_kg | REAL | Peso atleta |
| calories | REAL | Calorie |
| heart_rate_avg | REAL | HR media |
| elevation_gain_m | REAL | Salita metri |
| gps_points | TEXT (JSON) | Punti GPS |
| created_at | TEXT | Timestamp |

**athletes**
| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| id | INTEGER PK | Chiave primaria |
| name | TEXT | Nome atleta |
| age | INTEGER | Età |
| weight_kg | REAL | Peso kg |
| height_cm | REAL | Altezza cm |
| fat_percentage | REAL | % massa grassa |
| years_active | INTEGER | Anni attività |
| weekly_sessions | INTEGER | Sessioni settimanali |
| monthly_hours | REAL | Ore mensili |
| annual_hours | REAL | Ore annuali |
| experience_level | TEXT | Livello esperienza |

**metrics**
| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| id | INTEGER PK | Chiave primaria |
| athlete_id | INTEGER FK | Riferimento atleta |
| ride_id | INTEGER FK | Riferimento ride |
| fatigue_score | REAL | Punteggio affaticamento |
| recovery_hours | REAL | Ore recupero |
| calories_per_km | REAL | Calorie per km |
| efficiency_score | REAL | Punteggio efficienza |

### Operazioni Database
```python
from bike_analyzer.backend.db.database import (
    init_db, save_ride, get_ride, get_all_rides,
    delete_ride, save_athlete, get_athlete,
    create_indices, backup_database
)

# Inizializza
init_db()

# Salva ride
ride_id = save_ride({
    "date": "2024-01-15",
    "distance_km": 25.5,
    "duration_minutes": 65
})

# Recupera ride
ride = get_ride(ride_id)

# Backup
backup_path = backup_database()
```

## Frontend

### Dashboard Multi-Tab
Il frontend è integrato in FastAPI e servito da `/` (root route):
- `bike_analyzer/backend/static/index.html` — Pagina principale con 6 tab: Rides, Import, Athlete, AI Coach, Knowledge, Admin
- `bike_analyzer/backend/static/app.js` — Logica JavaScript completa (~700 righe)
- `bike_analyzer/backend/static/styles.css` — Stili dark theme con variabili CSS

### Tab e Funzionalità

| Tab | Funzionalità | Endpoint usati |
|-----|--------------|----------------|
| Rides | CRUD rides, grafico durata, grafici dettaglio, mappa, export JSON/CSV | `rides/*`, `charts/*`, `export/*` |
| Import | Upload multiplo GPX/FIT con drag&drop | `import/multiple` |
| Athlete | CRUD profilo atleta, punteggi performance | `athletes/*`, `scores/athlete/*` |
| AI Coach | Workout/recovery/trends recommendations | `coach/*` |
| Knowledge | Ricerca nella knowledge base | `knowledge`, `knowledge/search` |
| Admin | Statistiche, backup DB, creazione indici, benchmark | `admin/*`, `benchmark/compare` |

### API Client JS
```javascript
// app.js
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

### Variabili Ambiente
| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| DATABASE_URL | sqlite:///./rides.db | Connessione DB |
| API_HOST | 0.0.0.0 | Host API server |
| API_PORT | 8000 | Porta API server |
| MAP_DEFAULT_ZOOM | 13 | Zoom mappe default |
| GOOGLE_MAPS_API_KEY | - | Chiave API Google Maps |

### Docker
```dockerfile
# Dockerfile personalizzato
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py", "api"]
```

### Azure Developer CLI
```bash
azd up        # Deploy completo
azd deploy    # Deploy solo app
```

## Roadmap

| Fase | Stato | Descrizione |
|------|-------|-------------|
| 1-110 | ✅ | Core completato (130/135 step) |
| 136-145 | ⏳ | Test coverage (in corso) |

Vedi [ROADMAP.md](../ROADMAP.md) per dettagli completi.