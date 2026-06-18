# BikeMaster - Sistema di Analisi Intelligente delle Performance Ciclistiche

GPS-based cycling performance intelligence system. Importa le tue uscite da file GPX/FIT, analizza le metriche di potenza, stima calorie e affaticamento, visualizza i percorsi su mappe interattive e accedi a tutto tramite una REST API completa.

---

## Indice

1. [Caratteristiche](#caratteristiche)
2. [Stack Tecnologico](#stack-tecnologico)
3. [Quick Start](#quick-start)
4. [Configurazione](#configurazione)
5. [Architettura Repository](#architettura-repository)
6. [Modelli di Dato](#modelli-di-dato)
7. [API Reference](#api-reference)
8. [Motore Analitico](#motore-analitico)
9. [Dashboard](#dashboard)
10. [AI Coach](#ai-coach)
11. [Deployment](#deployment)
12. [Sviluppo](#sviluppo)
13. [Testing](#testing)
14. [Roadmap](#roadmap)

---

## Caratteristiche

- **Ingestione GPS** - Parsing file GPX (gpxpy) e Garmin FIT (fitparse)
- **Analisi percorso** - Distanza, velocità, elevazione, accelerazioni, soste
- **Stima calorie** - Modello fisico (resistenza aria + attrito) + MET
- **Punteggio affaticamento** - Formula ponderata con raccomandazioni di recupero
- **Mappe interattive** - Percorsi colorati per velocita con Folium/Leaflet
- **Knowledge Base** - Documenti sportivi indicizzati per RAG
- **AI Coach** - Consigli di allenamento e recupero basati su Groq/LLM
- **Google Fit** - Importazione automatica attivita ciclistiche
- **Google Maps** - Mappe statiche con API key
- **Calendario** - Pianificazione eventi di allenamento
- **Dashboard Web** - UI dark-themed con statistiche e lista uscite
- **Heatmap GPS** - Visualizzazione densita percorsi
- **Sistema Badge** - Medaglie e achievements
- **Piano Granfondo** - Generatore piani con tapering
- **Servizio Meteo** - Consigli meteo per uscite
- **Training Stress** - TSS, ATL/CTL/TSB, EWMA
- **14 Modelli Avanzati** - Power estimate, VO2max, climb classification, speed surging, ecc.
- **Phone GPS Tracking** - Registrazione uscite direttamente dal telefono mobile (Android)
- **REST API** - 40+ endpoint documentati
- **Esportazione** - JSON e CSV
- **JWT Auth** - Login e protezione endpoint
- **Rate Limiting** - Protezione API per-IP
- **Background Tasks** - Queue asincrona per operazioni pesanti
- **Cache Redis** - Caching con fallback graceful

---

## Stack Tecnologico

| Layer | Tecnologia |
|---|---|
| Backend | FastAPI 0.110+, Python 3.11+ |
| Database | SQLite (dev) + PostgreSQL (prod, asyncpg) |
| ORM | SQLAlchemy 2.0 (async + sync) |
| Migrations | Alembic |
| Cache | Redis (opzionale, fallback in-memory) |
| Maps | Folium / Leaflet.js / Google Static Maps |
| Analytics | NumPy, Pandas, Matplotlib, SciPy, scikit-learn, statsmodels |
| Parsers | gpxpy, fitparse |
| Auth | python-jose, passlib, bcrypt |
| AI/LLM | Groq SDK + OpenAI SDK |
| Rate Limit | slowapi |
| Config | Pydantic Settings v2 |
| Testing | pytest, pytest-asyncio |
| Frontend | Vue 3 + Vite + Chart.js + Leaflet |
| Mobile | Android Kotlin (Capacitor) |

---

## Quick Start

### Prerequisiti
- Python 3.11 o superiore
- pip
- Browser web

### Installazione

```bash
git clone https://github.com/ballales1984-wq/bikemaster.git
cd bikemaster
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Avvio

```bash
# API + Dashboard (default)
python main.py api

# Solo frontend standalone
python main.py web

# CLI demo analytics
python main.py cli
```

Apri http://localhost:8000 per la dashboard.

### Docker

```bash
docker compose up -d
```

---

## Configurazione

Copia `.env.example` in `.env` e configura:

```env
# Database
DATABASE_URL=sqlite:///./rides.db        # o postgresql://...
DATABASE_URL_ASYNC=sqlite+aiosqlite:///./rides.db  # async engine

# API
API_HOST=0.0.0.0
API_PORT=8000

# Google
GOOGLE_MAPS_API_KEY=your_key_here        # Opzionale
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org

# AI Coach
GROQ_API_KEY=your_key_here               # Opzionale per AI Coach
OPENAI_API_KEY=your_key_here             # Opzionale

# Security (OBBLIGATORIO in produzione)
SECRET_KEY=your_secret_key               # Min 32 caratteri
SECRET_KEY_PREVIOUS=prev_key_rotation    # Opzionale per rotazione

# Redis (opzionale, fallback in-memory)
REDIS_URL=redis://localhost:6379/0
```

---

## Architettura Repository

```
bikeMaster/
├── main.py                          # Entrypoint applicazione
├── requirements.txt                 # Dipendenze Python
├── pyproject.toml                   # Build system
├── Dockerfile / docker-compose.yml   # Containerizzazione
├── azure.yaml / render.yaml         # Deploy config
│
├── bike_analyzer/                   # Package Python principale
│   ├── __init__.py                  # Package facade
│   ├── main.py                      # CLI wrapper
│   └── backend/
│       ├── config.py                # Configurazioni legacy (.env)
│       ├── settings.py              # Pydantic Settings v2 (centralizzata)
│       ├── security.py              # JWT auth + security headers
│       ├── rate_limiter.py          # slowapi rate limiter
│       ├── redis_client.py          # Client Redis + cache
│       ├── task_queue.py            # Background task queue
│       ├── api/
│       │   ├── app_factory.py       # FastAPI application factory
│       │   ├── routes.py            # 40+ endpoint API
│       │   └── schemas.py           # Pydantic DTOs
│       ├── analytics/               # "Motore" di calcolo
│       │   ├── analytics.py         # Summary, export, report, charts
│       │   ├── analytics_trends.py  # Trend analysis (fitness, monthly, projection)
│       │   ├── advanced.py          # 14 modelli matematici avanzati
│       │   ├── calories.py          # Calcolo calorie (fisica + MET)
│       │   ├── fatigue.py           # Modello fatigue + recovery
│       │   ├── performance.py       # Score engine (performance/endurance/efficiency)
│       │   ├── benchmark.py         # Confronto percentile per categoria
│       │   ├── ai_coach.py          # AI Coach (Groq + RAG + memoria)
│       │   ├── knowledge_base.py    # RAG engine BM25 + LRU cache
│       │   ├── dashboard.py         # Statistiche aggregate dashboard
│       │   ├── training_load.py     # Carico allenamento (RSS, TSS)
│       │   ├── training_stress.py   # Training Stress Score + EWMA
│       │   ├── badges.py            # Sistema badge/heatmap
│       │   └── granfondo_planner.py # Piano granfondo con tapering
│       ├── weather/
│       │   ├── __init__.py
│       │   └── weather_service.py   # Servizio meteo
│       ├── db/
│       │   ├── database.py          # SQLite CRUD layer (sync)
│       │   ├── async_db.py          # Async DB layer (PostgreSQL + SQLite)
│       │   ├── postgres_db.py       # PostgreSQL full ORM
│       │   └── models.py            # SQLAlchemy ORM models (async)
│       ├── ingestion/
│       │   ├── gps_parser.py        # Parser GPX/FIT
│       │   └── google_fit.py        # Google Fit OAuth2
│       ├── maps/
│       │   ├── map_renderer.py      # Render Folium (percorso colorato)
│       │   ├── google_maps.py       # Google Static Maps API
│       │   └── serpapi_maps.py      # SerpApi luoghi vicini
│       ├── models/
│       │   ├── models.py            # Dataclass: Ride, GPSPoint, Segment, ecc.
│       │   └── __init__.py
│       ├── processing/
│       │   ├── processing.py        # Pulizia GPS, pausa, segmentazione
│       │   ├── segment_detector.py  # Segment detection avanzato
│       │   └── __init__.py
│       └── utils/
│           ├── dates.py             # Utilità date
│           ├── logger.py            # Logging configurato
│           └── __init__.py
│
├── frontend/                        # Vue 3 + Vite SPA (standalone)
│   ├── package.json                 # Vue 3, Chart.js, Leaflet, Capacitor
│   ├── vite.config.js
│   ├── index.html                   # Entrypoint Vite
│   ├── src/
│   │   ├── main.js                  # App Vue mount
│   │   ├── App.vue                  # Root component
│   │   ├── index.css
│   │   ├── components/              # 15 componenti Vue
│   │   │   ├── HeaderTabs.vue, RidesPanel.vue, ChartsPanel.vue,
│   │   │   ├── ImportPanel.vue, AthletePanel.vue, AthleteSettings.vue,
│   │   │   ├── CoachPanel.vue, KnowledgePanel.vue, HeatmapPanel.vue,
│   │   │   ├── BadgesPanel.vue, CalendarPanel.vue, GranfondoPlanner.vue,
│   │   │   ├── AdminPanel.vue, LoginForm.vue, RideDetail.vue,
│   │   │   └── StatsSummary.vue, ToastContainer.vue
│   │   └── composables/             # Composable functions
│   │       ├── useAuth.js, useChart.js, useRides.js
│   ├── dist/                        # Build output
│   └── android/                     # Android app (Kotlin + Capacitor)
│
├── android/                         # Android app standalone (Kotlin)
├── scripts/
│   ├── generate_sample_ride.py      # Generazione dati di test
│   └── demo_map.py                  # Demo renderer mappe
├── alembic/                         # Migrazioni DB versionate
│   ├── versions/08ee39bfe529_initial_models.py
│   └── env.py
├── tests/                           # Suite test automatici (24+ file)
├── knowledge_base/                  # Documenti indicizzati per RAG
├── docs/                            # Documentazione sviluppatore
├── .github/workflows/ci.yml         # CI/CD GitHub Actions
├── ROADMAP.md                       # Roadmap progetto
├── PROJECT_STATUS.md                # Stato corrente del progetto
└── requirements.txt
```

---

## Modelli di Dato

### GPSPoint
Punto GPS individuale con latitudine, longitudine, timestamp, altitudine e velocità.

| Campo | Tipo | Descrizione |
|---|---|---|
| lat | float | Latitudine WGS84 |
| lon | float | Longitudine WGS84 |
| timestamp | datetime | Istante del rilevamento |
| altitude | Optional[float] | Altitudine in metri |
| speed | Optional[float] | Velocita in km/h |

### Ride
Rappresenta una sessione ciclistica completata.

| Campo | Tipo | Descrizione |
|---|---|---|
| id | Optional[int] | Identificativo univoco DB |
| athlete_id | Optional[int] | FK al profilo atleta |
| date | str | Data uscita (ISO) |
| distance_km | float | Distanza totale km |
| duration_minutes | float | Durata in minuti |
| avg_speed_kmh | float | Velocita media km/h |
| weight_kg | float | Peso atleta (default 70kg) |
| calories | float | Calorie stimate |
| heart_rate_avg | Optional[float] | FC media |
| elevation_gain_m | Optional[float] | Dislivello positivo |
| gps_points | Optional[list[GPSPoint]] | Array completo punti |

### AthleteProfile
Profilo completo dell'atleta per calcoli personalizzati.

| Campo | Tipo | Descrizione |
|---|---|---|
| id | Optional[int] | Identificativo |
| name | str | Nome |
| age | int | Eta |
| weight_kg | float | Peso kg |
| height_cm | Optional[float] | Altezza cm |
| fat_percentage | Optional[float] | Massa grassa % |
| years_active | int | Anni di attivita |
| weekly_sessions | int | Sessioni settimanali |
| monthly_hours | float | Ore mese |
| annual_hours | float | Ore anno |
| experience_level | str | Livello (Beginner->Elite) |
| goals | Optional[str] | Obiettivi |
| preferred_terrain | Optional[str] | Terreno preferito |
| weekly_volume_km | float | Volume km settimana |

### Entity Figlie
- `CalendarEvent` - Evento di allenamento pianificato
- `Segment` - Segmento tra due GPSPoint
- `Pause` - Sosta rilevata durante la corsa
- `RouteStatistics` - Statistiche aggregate percorso

---

## API Reference

Base URL: `/api/v1`

### Health & Auth
| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/auth/login` | Login JWT |
| POST | `/auth/register` | Registrazione |

### Rides CRUD
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| POST | `/rides` | Yes | Crea uscita |
| GET | `/rides` | No | Elenca uscite (paginate) |
| GET | `/rides/{id}` | Yes | Dettaglio uscita (+fatigue + cal/km) |
| PUT | `/rides/{id}` | Yes | Aggiorna uscita |
| DELETE | `/rides/{id}` | Yes | Elimina uscita |
| GET | `/rides/count` | No | Conteggio uscite |
| POST | `/rides/analyze` | No | Multi-ride summary |
| POST | `/rides/{id}/analyze` | Yes | Analisi singola |
| GET | `/rides/{id}/report` | Yes | Report testuale |

### Import
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| POST | `/import/gpx` | Yes | Upload GPX |
| POST | `/import/fit` | Yes | Upload FIT |
| POST | `/import/multiple` | Yes | Batch upload |
| GET | `/import/google-fit/auth` | No | URL OAuth Google |
| POST | `/import/google-fit/token` | No | Exchange token |
| POST | `/import/google-fit` | Yes | Import da Google Fit |

### Export
| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/rides/export/json` | Export JSON |
| GET | `/rides/export/csv` | Export CSV |

### Charts
| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/charts/speed/{id}` | Grafico velocita (PNG) |
| GET | `/charts/elevation/{id}` | Grafico elevazione (PNG) |
| GET | `/charts/distance/{id}` | Grafico distanza (PNG) |
| GET | `/charts/duration` | Grafico durata |

### Athletes
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| POST | `/athletes` | Yes | Crea profilo |
| GET | `/athletes` | No | Lista atleti |
| GET | `/athletes/{id}` | Yes | Dettaglio |
| PUT | `/athletes/{id}` | Yes | Aggiorna |
| POST | `/athletes/{id}/metrics` | Yes | Salva metriche |

### Scores & Benchmark
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| GET | `/scores/athlete/{id}` | Yes | Punteggi atleta |
| POST | `/benchmark/compare` | No | Confronto benchmark |

### AI Coach
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| GET | `/coach/workout` | Yes | Consigli allenamento |
| GET | `/coach/recovery` | No | Consigli recupero |
| GET | `/coach/trends` | Yes | Analisi storico |
| GET | `/coach/full` | Yes | Report completo |
| POST | `/coach/chat` | No | Chat AI |
| GET | `/coach/history` | No | Storico conversazioni |

### Knowledge Base
| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/knowledge` | Lista topic |
| GET | `/knowledge/search?q=` | Ricerca semantica |
| GET | `/knowledge/stats` | Statistiche KB |
| POST | `/knowledge/reload` | Ricarica indici |

### Maps
| Metodo | Endpoint | Descrizione |
|---|---|---|
| POST | `/rides/{id}/map` | Genera mappa Folium |
| GET | `/rides/{id}/map/google` | Google Static Map (richiedere API key) |
| GET | `/maps/places/nearby` | Luoghi vicini (SerpApi) |
| GET | `/maps/places/search` | Ricerca luoghi |

### Admin
| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| GET | `/admin/backup` | Yes | Download backup DB |
| POST | `/admin/indexes` | No | Crea indici DB |
| GET | `/admin/stats` | No | Statistiche sistema |
| GET | `/health/detailed` | No | Health dettagliato |
| POST | `/admin/reset-demo` | No | Rigenera dati demo |

---

## Motore Analitico

### Calorie (physics + MET)
Calcola il costo energetico in due modalita:
- **Fisica** - Integrazione della potenza (resistenza rotolamento + attrito aria + gravita) divisa per rendimento neuromuscolare 25%
- **MET** - Tabella Metabolic Equivalents per intensita basata su velocita media

### Affaticamento
Score 1-10 basato su 5 fattori pesati:
- Durata (30%)
- Intensita cardiaca/HF (30%)
- Velocita media (20%)
- Dislivello (10%)
- Peso corporeo (10%)

Consigli di recupero dinamici: 8h, 16h, 24h, 48h.

### Performance Scores
- **Performance Score** - Punteggio assoluto uscita corrente
- **Endurance Score** - Indice di resistenza su storico
- **Efficiency Score** - Rapporto potenza-distanza

### Benchmark
Confronata le metriche dell'atleta con distribuzioni benchmark per categoria (eta, peso, esperienza) e calcola i percentile.

---

## AI Coach

Integrazione con Groq (LLM) per:
- Raccomandazioni di allenamento personalizzate
- Consigli di recupero basati su fatigue score
- Analisi trend storici
- Chat conversazionale con storico

Dipendenze: `GROQ_API_KEY` in `.env`.

---

## Dashboard

UI dark-theme con:
- Lista uscite con filtri (data, distanza, durata)
- Card statistiche aggregate
- Mappa percorso interattiva
- Grafici velocita/elevazione
- Widget AI Coach sidebar
- Profilo atleta con score

---

## Deployment

### Docker

```bash
docker build -t bikemaster .
docker run -p 8000:8000 bikemaster
```

### Docker Compose

```bash
docker-compose up -d
docker-compose logs -f
```

### Azure (azd)

```bash
azd up
```

### Render

```bash
render deploy
```

---

## Sviluppo

### Struttura moduli

Ogni modulo backend segue un pattern:
```
module/
├── __init__.py
├── core.py          # Logica pura (testabile singolarmente)
└── [integration]    # Colla con API/DB
```

### Aggiunta endpoint

1. Aggiungi DTO in `api/schemas.py`
2. Implementa handler in `api/routes.py`
3. Includi router in `api/app_factory.py` se serve prefisso custom
4. Aggiungi test in `tests/`

### Convenzioni

- Nomi moduli in `snake_case`
- Type hints obbligatori
- Import lazy nelle route per evitare circular dependency
- Logging tramite `analytics.logger.get_logger(__name__)`
- DB access tramite context manager `get_db_connection()`

---

## Testing

```bash
pytest
```

Suite di 40+ test automatici:
- Unit test modelli e parsing
- Test API coverage
- Mock Google Maps
- Performance engine
- Benchmark
- Knowledge base
- AI Coach API
- Database backup
- Import batch
- Athlete profile

### Coverage attuale: 78%

Target 80% (2 test mancanti).

---

## Roadmap

Stato progetto: Beta (140/145 step completati).

| Fase | Descrizione | Status |
|---|---|---|
| 1. Fondamenta | Progetto, struttra, modelli | ✅ Completata |
| 2. Analisi percorso | GPS, segmenti, statistiche | ✅ Completata |
| 3. Database | SQLite, CRUD, backup | ✅ Completata |
| 4. Profilo atleta | Campi atleta, storico | ✅ Completata |
| 5. Performance engine | Score, endurance, fatigue | ✅ Completata |
| 6. Benchmark | Categorie, percentile | ✅ Completata |
| 7. Knowledge Base | Indicizzazione, RAG | ✅ Completata |
| 8. AI Coach | Consigli, chat, trend | ✅ Completata |
| 9. Google Fit | OAuth2, import | ✅ Completata |
| 10. Google Maps | Static maps | ✅ Completata |
| 11. UI/UX | Dashboard dark theme | ✅ Completata |
| 12. Deployment | Docker, Azure, Render | ✅ Completata |
| 13. Test Coverage | 78% (target 80%) | 🔄 In corso |

---

## Contribuire

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/awesome`)
3. Commit modifiche (`git commit -m 'feat: aggiungi feature'`)
4. Push al branch (`git push origin feature/awesome`)
5. Apri Pull Request

---

## License

MIT - Vedi file LICENSE per dettagli.
