# Engine BM2 & Motore Analytics

Riferimento del motore di simulazione **BikeMaster 2.0** (`bike_analyzer/bm2/`) e del **motore analytics** classico (`bike_analyzer/backend/analytics/`).

---

## Parte 1 — BikeMaster 2.0 (BM2)

BM2 è il motore di simulazione sportiva: trasforma dati grezzi in `Quantity` type-safe, esegue algoritmi puri che restituiscono un `ModelResult` (con formula, input usati, precisione e confidence) e produce analisi what-if.

### Componenti

| File | Ruolo |
|---|---|
| `bm2/units.py` | `Quantity` + `UnitRegistry`: unità type-safe e conversioni dimensionali |
| `bm2/transformer.py` | `TransformerEngine` + `GeoPoint`: normalizzazione dati e proiezione metrica locale |
| `bm2/models.py` | Domini: `Athlete`, `Bike`, `Activity`, `WorldObject`, `AnalysisContext` |
| `bm2/algorithms/base.py` | `Algorithm` (ABC) + `ModelResult` (contratto di output) |
| `bm2/algorithms/*.py` | I 9 algoritmi (vedi tabella) |
| `bm2/orchestrator.py` | Seleziona/esegue gli algoritmi, aggrega `ModelResult`, calcola confidence |
| `bm2/simulation.py` | `SimulationEngine`: scenari, preset, analisi di sensibilità |
| `bm2/knowledge.py` | `KnowledgeEngine` + `Insight`: interpretazione dei risultati |
| `bm2/agents.py` | Agenti sorgente dati (`GPSAgent`, `AthleteAgent`, `EnvironmentAgent`, `SensorAgent`, `StravaAgent`, `GarminAgent`) |
| `bm2/adapters.py` | Adattatori dominio ↔ persistenza |

### Gli Engine concettuali

Vedi anche [`../BM2_ENGINE_ARCHITECTURE.md`](../BM2_ENGINE_ARCHITECTURE.md).

| Engine | Responsabilità | Cosa **non** conosce |
|---|---|---|
| **Import Engine** | Import da Strava/GPX/FIT/Garmin/Wahoo | Logica di analisi |
| **Data Layer** | Storage canonico (atleti, sessioni, bici, telemetria) | Interpretazione |
| **Time Engine** | Timeline unificata, sincronizzazione eventi | Fonti dati |
| **Tracking Engine** | Registrazione sessioni live (GPS + sensori) | Metriche derivate |
| **Measurement Engine** | Conversioni e grandezze derivate (standard interno via `Quantity`) | Origine dei sensori |
| **Analysis Engine** | Metriche di sessione/atleta, trend, zone, TSS/TRIMP | Presentazione |
| **Territory Engine** | Modello territorio: strade, pendenze, difficoltà, sicurezza | Stato atleta |
| **Knowledge Layer** | Stati interpretati: `FitnessState`, `FatigueState`, `RecoveryState`, `RouteDifficulty`, `PerformancePrediction` | Dati grezzi |
| **AI Coach** | Spiegazioni, consigli, interazione | Numeri grezzi (legge solo dal Knowledge Layer) |

### I 9 algoritmi (`ALL_ALGORITHMS`)

Ogni algoritmo eredita da `Algorithm` e restituisce un `ModelResult`.

| Algoritmo (`name`) | File | Unità | Cosa calcola |
|---|---|---|---|
| `MovementModel` | `algorithms/movement.py` | `m/s` | Velocità/cinematica del movimento |
| `EnergyModel` | `algorithms/energy.py` | `kcal` | Energia/calorie (modello fisico) |
| `PowerModel` | `algorithms/power_model.py` | `W` | Potenza stimata (forze ciclismo) |
| `PerformanceModel` | `algorithms/performance.py` | `score` | Punteggio di performance |
| `FatigueModel` | `algorithms/fatigue.py` | `score` | Livello di fatica |
| `RecoveryModel` | `algorithms/recovery.py` | `score` | Stato/tempo di recupero |
| `RouteDifficultyModel` | `algorithms/route_difficulty.py` | `score` | Difficoltà del percorso |
| `NutritionModel` | `algorithms/nutrition.py` | `g` | Fabbisogno nutrizionale (carbo/g) |
| `TrainingLoadModel` | `algorithms/training_load.py` | `score` | Carico di allenamento (TSS-like) |

Registro: `MODEL_REGISTRY = {a.name: a for a in ALL_ALGORITHMS}` (`bm2/algorithms/__init__.py`).

### Confidence & precisione

- Ogni `ModelResult` porta `precision` (incertezza assoluta) e `confidence` (0..1).
- `Algorithm.SOURCE_CONFIDENCE` pesa l'affidabilità in base alla fonte del dato (garmin/strava/manual/gps/dem/estimate).
- L'orchestrator aggrega e può segnalare risultati ambigui.

### API BM2

Vedi [api-reference.md — sezione 16](./api-reference.md#16-bikemaster-20--simulation-engine-apiv1bm2):
`GET /api/v1/bm2/models`, `POST /api/v1/bm2/ask`, `POST /api/v1/bm2/simulate`, `POST /api/v1/bm2/simulate-ride` (auth), `POST /api/v1/bm2/validate` (auth).

### Documenti BM2 correlati

- [`../bm2/variables.md`](../bm2/variables.md) — dizionario variabili con unità e posizione nel codice
- [`../bm2/data-contracts.md`](../bm2/data-contracts.md) — contratti JSON tra engine
- [`../bm2/database-schema.md`](../bm2/database-schema.md) — schema entità BM2
- [`../BM2_ALGORITHMS.md`](../BM2_ALGORITHMS.md) — specifica algoritmi
- [`../BM2_INTEGRATION_GUIDE.md`](../BM2_INTEGRATION_GUIDE.md) — integrazione con FastAPI/frontend
- [`../BM2_TESTING_STRATEGY.md`](../BM2_TESTING_STRATEGY.md) — strategia di test

---

## Parte 2 — Motore Analytics classico

Package `bike_analyzer/backend/analytics/`. Struttura a tre livelli: **calculators** (funzioni pure), **services** (orchestrazione use-case), **repositories** (accesso dati).

### Moduli principali

| Modulo | Responsabilità |
|---|---|
| `analytics.py` | Pipeline di analisi ride (statistiche percorso, segmenti, pause) |
| `advanced.py` | Modelli avanzati (pace consistency, VO2max stimato, classificatori salita, ecc.) |
| `power_model.py` | Metriche di potenza: NP, IF, VI, EF, TSS, FTP, Critical Power/W′, zone Coggan |
| `calories.py` | Stima calorie (resistenza rotolamento + aerodinamica + gravità) + tabelle MET |
| `fatigue.py` | Fatigue score 0-10 pesato + stima ore di recupero |
| `training_load.py` | TSS, ATL/CTL/TSB, EWMA, monotony/strain |
| `training_stress.py` | Serie giornaliera di training stress (persistenza `training_stress_days`) |
| `performance.py` | Punteggi di performance/endurance/efficienza |
| `benchmark.py` | Confronto percentile per categoria |
| `analytics_trends.py` | Trend temporali |
| `multi_classifier.py` | Classificazione multi-modello |
| `anomaly_detection.py` | Rilevamento anomalie |
| `vip_predictor.py` | Predizione VIP/performance |
| `inactivity_estimator.py` | Stima periodi di inattività |
| `ride_route_estimator.py` | Stima del percorso da dati parziali |
| `granfondo_planner.py` | Generatore piano granfondo con tapering |
| `training_plan_generator.py` | Generatore piani di allenamento |
| `badges.py` | Badge e riconoscimenti |
| `dashboard.py` | Aggregati per la dashboard |
| `knowledge_base.py` | Knowledge base RAG (indicizzazione documenti sportivi) |
| `ai_coach.py` | AI Coach (Groq/LLM + RAG dal Knowledge Layer) |

### Calculators / Services / Repositories

**Services** (`analytics/services/`):
- `context_builder.py` — costruisce il contesto di analisi
- `ride_analysis_service.py` — orchestrazione analisi ride
- `fitness_state_service.py` — calcolo/aggiornamento `FitnessStateVector`

**Repositories** (`analytics/repositories/`):
`athlete_repository`, `ride_repository`, `chat_history_repository`, `fitness_state_repository`, `poi_repository`, `training_stress_repository`, `user_repository`.

### Metriche di potenza (dettaglio)

- **Normalized Power (NP)**, **Intensity Factor (IF)**, **Variability Index (VI)**, **Efficiency Factor (EF)**
- **TSS**, **FTP**, **Critical Power / W′**
- **Aerobic decoupling**
- **Zone di potenza (Coggan)**

### Carico di allenamento (dettaglio)

- **TSS** — Training Stress Score per sessione
- **ATL** — Acute Training Load (media esponenziale 7 giorni)
- **CTL** — Chronic Training Load (media esponenziale 42 giorni)
- **TSB** — Training Stress Balance (CTL − ATL) → forma
- **Monotony / Strain** — monotonia e stress cumulativo

### Stima calorie (modello fisico)

Somma dei contributi:
- **Resistenza al rotolamento** (Crr · massa · g · cos θ)
- **Resistenza aerodinamica** (½ · ρ · CdA · v²)
- **Gravità** (massa · g · sin θ)
- correzione per **efficienza meccanica** (`CALORIE_EFFICIENCY_FACTOR`) + tabelle **MET** di fallback.

Parametri configurabili: vedi [configuration.md — Analytics](./configuration.md#analytics--soglie-e-pesi).

### AI Coach & Knowledge Base

- **LLM:** Groq (`GROQ_API_KEY`, modello `GROQ_MODEL`, default `openai/gpt-oss-120b`).
- **RAG:** embeddings locali `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dim) con fallback TF-IDF/BM25; store vettoriale `db/vector_db.py` o PGVector (`knowledge_chunks.embedding`).
- **Principio:** l'AI Coach legge solo stati interpretati dal Knowledge Layer, mai dati grezzi.
- **Persistenza chat:** tabella `chat_history` con retention `AI_COACH_CHAT_RETENTION_DAYS` (default 90).

---

## Riferimenti incrociati

- Modelli dati: [domain-models.md](./domain-models.md)
- Schema DB: [database-schema.md](./database-schema.md)
- API: [api-reference.md](./api-reference.md)
- Configurazione: [configuration.md](./configuration.md)
