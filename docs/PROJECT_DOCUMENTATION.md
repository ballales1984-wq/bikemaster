# BikeMaster — Documentazione Completa del Progetto

> **Versione:** 1.1.0  
> **Data:** 2026-06-05  
> **Stack:** Python 3.11 · FastAPI · SQLite · Vanilla JS SPA  

---

## Sommario

1. [Panoramica](#1-panoramica)
2. [Architettura del Sistema](#2-architettura-del-sistema)
3. [Stack Tecnologico](#3-stack-tecnologico)
4. [Struttura del Progetto](#4-struttura-del-progetto)
5. [Modello Dati & Database](#5-modello-dati--database)
6. [API Reference (Riepilogo)](#6-api-reference-riepilogo)
7. [Componenti Principali](#7-componenti-principali)
8. [AI Coach & Knowledge Base](#8-ai-coach--knowledge-base)
9. [Frontend](#9-frontend)
10. [Testing](#10-testing)
11. [Configurazione & Deployment](#11-configurazione--deployment)
12. [Roadmap](#12-roadmap)
13. [Troubleshooting Comune](#13-troubleshooting-comune)

---

## 1. Panoramica

**BikeMaster** è un sistema di **intelligence per le performance ciclistiche basato su dati GPS**. Il progetto permette a ciclisti di tutti i livelli (principianti → elite) di:

- importare percorsi da file **GPX / FIT** (dispositivi Garmin, Wahoo, ecc.) o da **Google Fit**;
- analizzare metriche di performance: distanza, velocità, elevazione, accelerazioni, pause;
- stimare **calorie** (modello fisico o MET) e calcolare un **punteggio di affaticamento**;
- confrontare le proprie prestazioni con **benchmark** per categoria;
- ricevere consigli personalizzati da un **AI Coach** alimentato da una Knowledge Base specializzata in ciclismo;
- consultare mappe interattive, chart e statistiche storiche tramite una **dashboard web**.

### Filosofia Architetturale

Applicazione **monolitica modulare** (non microservizi), con backend FastAPI che funge contemporaneamente da **API REST** e da **server di asset statici** per il frontend. Il database è **SQLite** (nessun ORM), scelto per semplicità di deploy e portabilità. L'AI Coach combina:

- calcolo metriche sportive classico
- **RAG (Retrieval-Augmented Generation)** con motore BM25 custom su knowledge base markdown
- generazione LLM via **Groq API** (modello LLaMA 3.3 70B Versatile)
- memoria conversazionale persistita su tabella `chat_history`

---

## 2. Architettura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌──────────────────────┐    ┌───────────────────────────┐  │
│  │   Dashboard SPA      │    │      API REST (/api/v1)   │  │
│  │   index.html +       │    │  FastAPI + Pydantic v2    │  │
│  │   app.js (vanilla)   │    │  ~40 endpoint             │  │
│  └──────────────────────┘    └─────────┬─────────────────┘  │
│                                        │                    │
│  ┌─────────────────────────────────────▼─────────────────┐  │
│  │              STATIC ASSETS (CSS/JS/HTML)                │  │
│  │  styles.css, app.js, sw.js (PWA), manifest.json        │  │
│  └────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                  BUSINESS LOGIC LAYER                        │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │  Analytics  │ │  GPS        │ │  AI Coach             │  │
│  │  Engine     │ │  Processing │ │  (Groq + RAG BM25)    │  │
│  │  - calories │ │  - parser   │ │  - workout advice     │  │
│  │  - fatigue  │ │  - cleaning │ │  - recovery advice    │  │
│  │  - scores   │ │  - segments │ │  - chat con memoria   │  │
│  │  - charts   │ │  - stats    │ │  - historical trends  │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                   DATA ACCESS LAYER                          │
│                    SQLite (sqlite3 nativo)                   │
│  - 4 tabelle: rides, athletes, metrics, chat_history        │
│  - CRUD diretto, indici compositi, backup con timestamp     │
├─────────────────────────────────────────────────────────────┤
│                    DOMAIN MODELS                             │
│  Ride · GPSPoint · Segment · Pause · AthleteProfile          │
│  RouteStatistics · ChatMessage                               │
└─────────────────────────────────────────────────────────────┘

  Servizi Esterni:
  ├─ Groq API (LLM LLaMA 3.3 70B)
  ├─ Google Maps Static API (opzionale)
  ├─ Google Fit API (opzionale, OAuth2)
  └─ OpenStreetMap tiles (Folium / Leaflet)
```

### Pattern Principali

- **Layered Architecture**: Presentation → Business Logic → Data Access → Domain Models
- **IIFE Pattern** nel frontend per evitare scope globale
- **LRU Cache** sulla knowledge base (chiavata su mtime directory)
- **Evento startup** FastAPI per inizializzazione DB automatica
- **PWA-ready**: Service Worker + Web App Manifest

---

## 3. Stack Tecnologico

### Backend

| Componente | Tecnologia | Versione |
|---|---|---|
| Framework API | FastAPI | >= 0.110.0 |
| Validazione | Pydantic v2 | — |
| Server ASGI | Uvicorn | >= 7.x |
| Linguaggio | Python | >= 3.11 |
| Database | SQLite3 (nativo) | built-in |
| Analisi dati | NumPy, Pandas | >= 1.26, >= 2.2 |
| Charts | Matplotlib | >= 3.8 |
| Parsing GPS | gpxpy, fitparse | >= 1.6, >= 1.2 |
| LLM / AI | Groq SDK | >= 0.4.0 |
| HTTP Client | requests | >= 2.31 |
| Config | python-dotenv | — |

### Frontend

| Componente | Tecnologia |
|---|---|
| Markup | HTML5 semantico |
| Stili | CSS3 custom con CSS Variables (dark/light theme) |
| Logica | Vanilla JavaScript ES6+ (IIFE pattern) |
| Mappe interattive | Leaflet.js 1.9.4 (CDN) |
| Grafici barre | Chart.js (CDN) |
| Mappe server-side | Folium 0.16+ |
| PWA | Service Worker + Web App Manifest |

### DevOps & Deploy

| Strumento | Scopo |
|---|---|
| Docker / Compose | Containerizzazione locale |
| Azure Developer CLI (azd) | Deploy su Azure App Service (F1 Free tier) |
| pytest + pytest-asyncio | Test automatici |
| GitHub Actions (previsto) | CI/CD |

---

## 4. Struttura del Progetto

```
D:\BikeMaster
├── main.py                          # Entrypoint CLI/API unificato
├── pyproject.toml                   # Build system + dipendenze + metadata
├── requirements.txt                 # Dipendenze pinned (prod + dev)
├── package.json                     # Metadati NPM (placeholder, privato)
├── Dockerfile                       # Container Python 3.11-slim
├── docker-compose.yml               # Compose per deploy container
├── azure.yaml                       # Configurazione Azure Developer CLI
├── .env.example                     # Template variabili ambiente
├── .gitignore / .dockerignore
├── README.md / LICENSE / ROADMAP.md
│
├── bike_analyzer/                   # Package Python principale
│   ├── __init__.py                  # Facade pubblica
│   ├── main.py                      # Entrypoint CLI demo
│   └── backend/
│       ├── __init__.py
│       ├── api/                     # Layer HTTP FastAPI
│       │   ├── app_factory.py       # Factory FastAPI + CORS + static mount
│       │   ├── routes.py            # ~525 righe, tutti gli endpoint API
│       │   └── schemas.py           # Modelli Pydantic (request/response)
│       ├── analytics/               # "Motore" di calcolo
│       │   ├── analytics.py         # Core: summary, export, report, charts
│       │   ├── calories.py          # Calcolo calorie (fisica + MET)
│       │   ├── fatigue.py           # Modello fatigue + recovery hours
│       │   ├── performance.py       # Score engine (performance/endurance/efficiency)
│       │   ├── benchmark.py         # Confronto percentile per categoria
│       │   ├── ai_coach.py          # AI Coach con Groq/LLaMA + RAG + memoria
│       │   └── knowledge_base.py    # RAG engine BM25 + LRU cache + chunking
│       ├── db/
│       │   └── database.py          # Layer SQLite CRUD (4 tabelle)
│       ├── ingestion/
│       │   ├── gps_parser.py        # Parser GPX (xml.etree) e FIT (fitparse)
│       │   └── google_fit.py        # Integrazione Google Fit (OAuth2)
│       ├── maps/
│       │   ├── map_renderer.py      # Render Folium (Leaflet) color-by-speed
│       │   └── google_maps.py       # Google Static Maps API + elevation
│       ├── models/
│       │   └── models.py            # Dataclass: Ride, GPSPoint, Segment, ecc.
│       └── static/                  # Frontend servito da FastAPI
│           ├── index.html           # Dashboard SPA principale (~290 righe)
│           ├── ai_coach.html        # Pagina AI Coach dedicata (~223 righe)
│           ├── app.js               # ~1015 righe JS vanilla (SPA completa)
│           ├── styles.css           # ~950 righe CSS dark + light theme
│           ├── sw.js                # Service Worker (PWA)
│           ├── manifest.json        # Manifest PWA
│           └── icon.svg             # Icona app
│
├── frontend/                        # Directory placeholder (solo __init__.py)
├── tests/                           # Suite test pytest (~79 test passanti)
│   ├── conftest.py                  # Fixture condivise (TestClient, tmp_db)
│   ├── test_models.py
│   ├── test_database.py
│   ├── test_analytics.py
│   ├── test_edge_cases.py
│   ├── test_performance.py
│   ├── test_benchmark_api.py
│   ├── test_knowledge_api.py        # Test più esteso (~14.8 KB)
│   ├── test_ai_coach.py
│   ├── test_ai_coach_api.py
│   └── ... (altri moduli di test)
│
├── knowledge_base/                  # Knowledge base Markdown per RAG
│   ├── training.md                  # Teoria allenamento, periodizzazione
│   ├── training_plans.md            # Piani allenamento strutturati
│   ├── nutrition.md                  # Nutrizione ciclista (82 righe)
│   ├── cardio.md                     # HR zones, VO2 max, HRV, cardiac drift
│   ├── biomechanics.md               # Pedalata, bike fit, postura
│   ├── equipment.md                  # Componenti, power meter, sensori
│   └── recovery.md                   # Fatigie model, stretching, recupero
│
├── docs/                            # Documentazione progetto
│   ├── API_DOCS.md                  # API docs (EN)
│   ├── API_DOCUMENTAZIONE.md        # API docs (IT)
│   ├── API_EXAMPLES.http            # Esempi HTTP request
│   ├── USER_GUIDE.md                # Guida utente (EN)
│   ├── GUIDA_UTENTE.md              # Guida utente (IT)
│   ├── DEVELOPMENT.md               # Guida sviluppatore (EN)
│   ├── SVILUPPO.md                  # Guida sviluppatore (IT)
│   └── CHANGELOG.md                 # Note di rilascio
│
├── scripts/
│   ├── generate_sample_ride.py      # Generatore dati GPS sintetici
│   └── demo_map.py                  # Genera mappa HTML demo
│
└── [config] .devcontainer/, .pytest_cache/, .benchmarks/
```

---

## 5. Modello Dati & Database

### Schema SQLite (4 tabelle)

```sql
-- Uscite ciclistiche (GPS opzionale serializzato come JSON)
CREATE TABLE rides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER,
    date TEXT NOT NULL,
    distance_km REAL,
    duration_minutes REAL,
    avg_speed_kmh REAL,
    weight_kg REAL DEFAULT 70,
    calories REAL,
    heart_rate_avg REAL,
    elevation_gain_m REAL,
    gps_points TEXT,               -- JSON array di oggetti GPSPoint
    created_at TEXT DEFAULT (datetime('now'))
);

-- Profili atleta
CREATE TABLE athletes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER DEFAULT 30,
    weight_kg REAL DEFAULT 70,
    height_cm REAL,
    fat_percentage REAL,
    years_active INTEGER DEFAULT 1,
    weekly_sessions INTEGER DEFAULT 3,
    monthly_hours REAL DEFAULT 0,
    annual_hours REAL DEFAULT 0,
    experience_level TEXT DEFAULT 'Beginner',
    goals TEXT,
    preferred_terrain TEXT,
    weekly_volume_km REAL,
    best_segments TEXT,
    medical_notes TEXT,
    equipment TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Metriche calcolate per ogni ride
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER,
    ride_id INTEGER,
    fatigue_score REAL,
    recovery_hours REAL,
    calories_per_km REAL,
    efficiency_score REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Memoria conversazionale AI Coach
CREATE TABLE chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER,
    role TEXT NOT NULL,             -- 'user' | 'assistant'
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### Modelli Python (Dataclass)

```python
@dataclass
class Ride:
    id: Optional[int]
    athlete_id: Optional[int]
    date: str                        # ISO format YYYY-MM-DD
    distance_km: float
    duration_minutes: float
    avg_speed_kmh: float
    weight_kg: float = 70.0
    calories: float = 0.0
    heart_rate_avg: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    gps_points: Optional[list[dict]] = None   # serializzati JSON nella colonna DB
    created_at: Optional[str] = None
    @property
    def duration_hours(self) -> float: ...

@dataclass
class GPSPoint:
    lat: float
    lon: float
    timestamp: datetime
    altitude: Optional[float] = None
    speed: Optional[float] = None    # km/h (da FIT enhanced_speed)

@dataclass
class AthleteProfile:
    id: Optional[int]
    name: str
    age: int = 30
    weight_kg: float = 70.0
    height_cm: Optional[float] = None
    fat_percentage: Optional[float] = None
    years_active: int = 1
    weekly_sessions: int = 3
    monthly_hours: float = 0.0
    annual_hours: float = 0.0
    experience_level: str = "Beginner"   # Beginner|Amateur|Intermediate|Advanced|Elite
    goals: Optional[str] = None
    preferred_terrain: Optional[str] = None
    weekly_volume_km: Optional[float] = None
    best_segments: Optional[str] = None
    medical_notes: Optional[str] = None
    equipment: Optional[str] = None
```

> **Nota architetturale**: il progetto usa `sqlite3` nativo, non un ORM. SQLAlchemy 2.0 è importato ma non utilizzato come ORM (solo per utility). I punti GPS sono serializzati come JSON nella colonna `gps_points` (trade-off per semplicità vs. query granulari).

---

## 6. API Reference (Riepilogo)

**Base URL:** `http://localhost:8000/api/v1`

### Rides CRUD

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/rides` | Crea nuova ride (JSON body) |
| `GET` | `/rides?page=&page_size=&sort=` | Lista paginata e ordinabile |
| `GET` | `/rides/{id}` | Dettaglio ride con analytics calcolate |
| `PUT` | `/rides/{id}` | Aggiorna singoli campi (merge parziale) |
| `DELETE` | `/rides/{id}` | Elimina ride |
| `POST` | `/rides/{id}/analyze` | Analisi approfondita singola ride |
| `POST` | `/rides/analyze` | Riepilogo multi-ride (aggregato) |

### Importazione

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/import/gpx` | Upload GPX (multipart/form-data) |
| `POST` | `/import/fit` | Upload FIT Garmin (multipart) |
| `POST` | `/import/multiple` | Upload multiplo batch (GPX + FIT) |
| `GET` | `/import/google-fit/auth` | URL OAuth2 Google Fit |
| `POST` | `/import/google-fit/token` | Scambio codice → token |
| `POST` | `/import/google-fit` | Importa attività cycling da Google Fit |

### Esportazione

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/rides/export/json` | Export completo `rides.json` |
| `GET` | `/rides/export/csv` | Export piatto `rides.csv` |

### Grafici & Mappe

| Metodo | Endpoint | Output |
|---|---|---|
| `GET` | `/charts/speed/{id}` | PNG — profilo velocità vs tempo |
| `GET` | `/charts/elevation/{id}` | PNG — profilo elevazione |
| `GET` | `/charts/distance/{id}` | PNG — distanza cumulativa |
| `GET` | `/charts/duration` | PNG — durata per ride |
| `GET` | `/rides/{id}/map` | HTML — mappa interattiva Folium |
| `GET` | `/rides/{id}/map/google` | PNG — Google Static Maps |

### Atleti

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/athletes` | Crea profilo atleta |
| `GET` | `/athletes/{id}` | Dettaglio atleta |
| `PUT` | `/athletes/{id}` | Aggiorna profilo (merge parziale) |
| `POST` | `/athletes/{id}/metrics` | Salva metriche calcolate |

### Punteggi

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/scores/athlete/{id}` | Performance / Endurance / Efficiency score (0-10) |

### Benchmark

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/benchmark/compare` | Confronto percentile vs categoria per livello |

### AI Coach

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/coach/workout?athlete_id=` | Raccomandazioni allenamento (LLM) |
| `GET` | `/coach/recovery?fatigue_score=&ride_id=` | Consigli recupero (LLM) |
| `GET` | `/coach/trends` | Analisi trend storici (LLM) |
| `GET` | `/coach/full?athlete_id=` | Pacchetto completo + charts |
| `GET/POST` | `/coach/chat` | Chat conversazionale con memoria |
| `GET` | `/coach/history?athlete_id=` | Storico conversazioni |
| `GET` | `/coach/page?athlete_id=` | Pagina completa AI Coach UI |

### Knowledge Base

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/knowledge` | Lista argomenti disponibili |
| `GET` | `/knowledge/search?q=` | Ricerca BM25 sulla KB |
| `GET` | `/knowledge/stats` | Statistiche KB (chunks, topics) |
| `POST` | `/knowledge/reload` | Reload dinamico della KB |

### Admin

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/admin/stats` | Statistiche sistema |
| `GET` | `/admin/backup` | Backup SQLite con timestamp |
| `POST` | `/admin/indexes` | Crea indici compositi |
| `POST` | `/admin/reset-demo` | Reset dati demo |
| `GET` | `/health` | Health check base |
| `GET` | `/health/detailed` | Health check con stats DB |

---

## 7. Componenti Principali

### 7.1 GPS Ingestion (`ingestion/`)

| File | Responsabilità |
|---|---|
| `gps_parser.py` | Parsing GPX 1.1 (XML nativo ElementTree) e Garmin FIT (fitparse); conversione coordinate fix; calcolo distanza cumulativa haversine |
| `google_fit.py` | Flusso OAuth2 completo — authorization URL, token exchange, fetch attività cycling da Google Fitness API |

**Formato GPSPoint serializzato in DB:**
```json
[
  {"lat": 45.4408, "lon": 12.3155, "timestamp": "2024-01-15T09:00:00Z", "altitude": 12.5, "speed": 22.3},
  ...
]
```

### 7.2 GPS Processing (`processing/processing.py`)

Pipeline di pulizia dati GPS prima del salvataggio:

1. **validazione** — range lat [-90, 90], lon [-180, 180], datetime valido
2. **rimozione outlier** — punti con velocità > 120 km/h tra punti consecutivi
3. **rilevamento pause** — soste con velocità < 1.5 km/h per > 3 minuti
4. **rilevamento accelerazioni/rallentamenti** — soglia ±2.0 km/h/s
5. **costruzione segmenti** — triangolazione haversine, calcolo dislivello cumulativo
6. **calcolo statistiche aggregate** — `RouteStatistics`

### 7.3 Analytics Engine (`analytics/`)

| Modulo | Funzionalità |
|---|---|
| `calories.py` | Stima calorie: metodo **fisico** (rolling resistance + resistenza aerodinamica + gravità, efficienza 25%) o metodo **MET** |
| `fatigue.py` | `calculate_fatigue_score(ride)` — punteggio 0-10 con formula weighted (durata 30%, HR% 30%, velocità 20%, dislivello 10%, peso 10%). `estimate_recovery_hours()` — stima 8/16/24/48h |
| `performance.py` | `calculate_performance_score()` — speed + duration + elevation factors → 0-10. `calculate_endurance_score()` — long ride ratio + consistency. `calculate_efficiency_score()` — calorie/km vs benchmark 30 kcal/km → 0-10. `get_experience_level()` — classificazione Beginner / Amateur / Intermediate / Advanced / Elite |
| `dashboard.py` | Aggregatore score per vista dashboard |
| `benchmark.py` | Confronto percentile vs categorie per livello atleta (5 livelli, range km/velocità/ore/settimana; categorizzazioni per età, peso, anni esperienza) |

### 7.4 Maps (`maps/`)

| Modulo | Tecnologia | Output |
|---|---|---|
| `map_renderer.py` | Folium + Leaflet | HTML interattivo — segmenti colorati per velocità (gradiente rosso→giallo→verde), marker start/end, popup statistiche, tile OpenStreetMap |
| `google_maps.py` | Google Static Maps API | PNG — percorso blu, marker S/E, fallback gracefully se API key assente |

### 7.5 Database Layer (`db/database.py`)

**260 righe**, layer CRUD diretto su SQLite senza ORM:

- Funzioni per ogni tabella: `save_ride()`, `get_ride()`, `get_all_rides()`, `delete_ride()`, `save_athlete()`, `get_athlete()`, `save_metrics()`, `get_chat_history()`
- **Indici compositi** su: `rides(date)`, `rides(distance_km)`, `rides(duration_minutes)`, `rides(avg_speed_kmh)`, `rides(athlete_id)`, `metrics(ride_id)`
- **Backup automatico** con timestamp nel nome file
- **Auto-migrazione**: aggiunge colonna `goals` allo schema `athletes` se mancante (migration inline)

---

## 8. AI Coach & Knowledge Base

### 8.1 Knowledge Base (RAG Engine)

**7 file Markdown** in `knowledge_base/` (~250 righe totali):

| File | Argomento |
|---|---|
| `training.md` | Teoria allenamento: periodizzazione, volume, intensità |
| `training_plans.md` | Piani allenamento strutturati |
| `nutrition.md` | Nutrizione ciclista: carboidrati, proteine, idratazione |
| `cardio.md` | Cardiac training, HR zones, VO2 max, HRV, cardiac drift |
| `biomechanics.md` | Biomeccanica pedalata, bike fit, postura |
| `equipment.md` | Componenti, power meter, sensori |
| `recovery.md` | Fatigue model, stretching, recupero attivo |

**Motore di ricerca (`knowledge_base.py` — 290 righe):**

- **Chunking**: max 1200 chars per chunk, overlap 200 chars
- **Tokenizer**: tokenizzazione con rimozione stop-words italiano + inglese (60+ parole)
- **Scoring**: **BM25** con parametri k1=1.5, b=0.75, IDF calcolato dinamicamente
- **LRU Cache**: chiavata su `mtime` della directory knowledge base — reload automatico se i file cambiano
- **Metadati arricchiti** per chunk: `topic`, `chunk_id`, `section` (heading estratto), `token_count`, `word_count`
- **Output dual-mode**: `search_knowledge_base("query")` → lista dizionari (per API); `search_knowledge_base("query", as_string=True)` → stringa formattata per LLM

### 8.2 AI Coach (`analytics/ai_coach.py` — 222 righe)

**Client Groq** — modello `llama-3.3-70b-versatile`:

```python
# Flusso AI Coach
generate_workout_recommendations(rides, athlete)   # Piano allenamento personalizzato
generate_recovery_recommendations(ride, fatigue)   # Consigli recupero concreti
analyze_historical_trends(rides)                  # Analisi trend storico
ai_coach_full(athlete_id)                         # Aggregatore: scores + charts + advice
```

**Prompt engineering**:
- Contesto composito: profilo atleta + punteggi calcolati + risultati RAG da knowledge base + storico chat
- Memoria conversazionale: storico salvato in `chat_history` DB, ultimi N turni inclusi nel prompt
- Output strutturato: risposte in italiano, formattate come consigli pratici

---

## 9. Frontend

### Dashboard Principale (`static/index.html` + `app.js` + `styles.css`)

**SPA vanilla** con 6 tab:

| Tab | Contenuto |
|---|---|
| Rides | Form aggiunta ride + lista cards + dettaglio con chart + mappa |
| Import | Upload drag-and-drop GPX/FIT con anteprima file |
| Athlete | Form profilo completo atleta |
| AI Coach | Input ID atleta + caricamento dati coach |
| Knowledge | Ricerca full-text KB + lista argomenti |
| Admin | Statistiche, backup DB, indici, benchmark, reset demo |

**Stats bar** (sempre visibile): 5 indicatori — totale uscite, km totali, calorie totali, velocità media, ore totali.

**Mappa Footer**: Leaflet map sempre visibile in fondo.

### Pagina AI Coach Dedicata (`static/ai_coach.html`)

- Score cards con codifica colore semantica (verde/giallo/rosso)
- Sezioni: Consigli Allenamento, Analisi Storica, Consigli Recupero
- Charts grid (grafici velocità e durata PNG server-side)

### Caratteristiche Frontend

- **Dark theme** (default) + Light theme toggle con CSS Variables
- **PWA-ready**: Service Worker caching + Web App Manifest (icon SVG)
- **Accessibilità**: ARIA labels, semantic HTML, focus-visible outlines, `prefers-reduced-motion`
- **Responsività**: breakpoint 768px (mobile drawer), 480px (form single-column)
- **UX**: toast notifications, skeleton loading, scroll indicator, animazioni hover

---

## 10. Testing

**Suite:** pytest 8+ + pytest-asyncio  
**Test passanti:** 79 test (~79% coverage)  
**Config:** `conftest.py` con fixture condivise (`TestClient`, `tmp_db` path), mock `GROQ_API_KEY`, mock `GOOGLE_MAPS_API_KEY`

### Moduli di Test

| File | Focus |
|---|---|
| `test_models.py` | Modelli dataclass, haversine, GPSPoint |
| `test_database.py` | CRUD rides/athletes, indici, backup |
| `test_database_backup.py` | Funzionalità backup DB |
| `test_analytics.py` | Calories, fatigue, export, report, charts |
| `test_performance.py` | Score engine (performance, endurance, efficiency) |
| `test_edge_cases.py` | Coordinate 0.0, GPS vuoto, input negativi, rimozione ride |
| `test_import_batch.py` | Upload multiplo GPX/FIT |
| `test_google_maps_mock.py` | Mock Google Maps senza API key |
| `test_athlete_profile.py` | CRUD + validazioni profilo atleta |
| `test_scores_api.py` | Endpoint scores HTTP |
| `test_benchmark_api.py` | Confronto benchmark HTTP |
| `test_ai_coach.py` | AI Coach generazione advice |
| `test_ai_coach_api.py` | Endpoint AI Coach HTTP |
| `test_knowledge_api.py` | **~15KB** — BM25, chunking, RAG, reload, stats, context formatting |
| `test_api_coverage.py` | Coverage endpoint principali |

### Esecuzione

```bash
# Tutti i test
pytest

# Con coverage
pytest --cov=bike_analyzer --cov-report=term-missing

# Test singolo modulo
pytest tests/test_knowledge_api.py -v

# Test con filtro per nome
pytest -k "test_search_training_topic_found" -v
```

---

## 11. Configurazione & Deployment

### Variabili d'Ambiente

| Variabile | Default | Descrizione |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./rides.db` | Connessione database |
| `API_HOST` | `0.0.0.0` | Host server API |
| `API_PORT` | `8000` | Porta server API |
| `MAP_DEFAULT_ZOOM` | `13` | Zoom default mappe |
| `GOOGLE_MAPS_API_KEY` | *(vuoto)* | Google Static Maps API key |
| `GROQ_API_KEY` | *(richiesta per AI Coach)* | Chiave API Groq per LLM |

### Modalità d'Uso

```bash
# API Server (default) — dashboard + REST API
python main.py api
python main.py api --reload    # con hot-reload per sviluppo

# Web server standalone
python main.py web

# CLI — demo analytics su dati sample
python main.py cli

# Apri browser: http://localhost:8000
```

### Docker

```bash
# Build
docker build -t bikemaster .

# Run singolo container
docker run -p 8000:8000 bikemaster

# Docker Compose (con volumi persistenti)
docker-compose up -d
docker-compose logs -f

# Stop
docker-compose down
```

**Volumi Compose:**
- `./data:/app/data` — database persistente
- `./static:/app/static` — asset frontend customizzabili

### Azure (azd)

```bash
azd up        # Provision + deploy completo
azd deploy    # Solo deploy codice
```

Configurazione in `azure.yaml`:
- Tipo: web app Python 3.11
- SKU: F1 (Free tier)
- Hook post-provision per install dipendenze

---

## 12. Roadmap

| Fase | Stato | Descrizione |
|---|---|---|
| Core GPS ingestion & parsing | ✅ Completo | GPX/FIT parsing, pulizia, segmentazione |
| Analytics base | ✅ Completo | Calorie, fatigue, performance scores, charts |
| Benchmark & confronti | ✅ Completo | 5 categorie, percentile, classificazione |
| AI Coach | ✅ Completo | Groq + RAG + memoria conversazionale |
| Knowledge Base | ✅ Completo | 7 argomenti, BM25 engine, 79 test |
| Google Fit OAuth | ✅ Completo | Flusso OAuth2 completo |
| Google Maps | ✅ Completo | Static Maps + elevation |
| Docker / Azure deploy | ✅ Completo | Container + azd |
| Test coverage | ✅ ~79% | 79 test passanti, obiettivo >80% |
| Miglioramenti UI/UX | ✅ Completo | Dark theme, PWA, scroll indicator, accessibilità |
| Vector DB / embedding | 🔄 Futuro | Sostituire BM25 con vector search (es. Chroma, Qdrant) |
| Autenticazione utenti | 🔄 Futuro | JWT / API key per produzione |
| PostgreSQL migrazione | 🔄 Futuro | Sostituire SQLite per produzione scale |
| Real-time sync | 🔄 Futuro | WebSocket per aggiornamenti live durante ride |

---

## 13. Troubleshooting Comune

| Problema | Causa | Soluzione |
|---|---|---|
| `No GPS points for this ride` | File GPX/FIT vuoto o corrotto | Verificare che il file contenga track points `<trkpt>` o record FIT |
| `GOOGLE_MAPS_API_KEY not configured` | Variabile `.env` mancante | Aggiungere `GOOGLE_MAPS_API_KEY=your_key` in `.env` |
| `GROQ_API_KEY missing` | AI Coach disabilitato | Aggiungere `GROQ_API_KEY` in `.env` o disabilitare endpoint coach |
| Database locked / errors | SQLite concorrenza | Usare `POST /admin/indexes` per ottimizzare, o migrare a WAL mode |
| `LF will be replaced by CRLF` (git warning) | File con line-ending Windows | Normale su Windows, non blocca il commit |
| Import FIT fallisce | File FIT non supportato / corrotto | Verificare che sia un FIT valido (non ANT FIT) |

---

## Contatti & Link

- **Repository:** https://github.com/ballales1984-wq/bikemaster
- **Issues:** https://github.com/ballales1984-wq/bikemaster/issues
- **License:** MIT

---

*Documento generato automaticamente — BikeMaster v1.1.0*
