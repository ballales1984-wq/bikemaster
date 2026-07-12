# BikeMaster 2.0 — Architettura Engine

**Versione:** Bozza 1.0
**Riferimento:** `docs/ARCHITECTURE.md` (sezioni 1–6), `bm2/data-contracts.md`, `bm2/database-schema.md`

---

## 1. Panoramica

BM2 è una pipeline di **Engine specializzati** che trasformano dati grezzi in insight
sportivi. Ogni Engine ha:
- **Responsabilità** ben definita.
- **Input** contrattati (vedi `bm2/data-contracts.md`).
- **Output** contrattati verso Engine a valle.
- **Dependency direction** rigorosa: non può leggere output di Engine "a monte"
  nella pipeline (es. Analysis Engine non può leggere `RawGPSPoint`).

L'architettura è **a pipeline**, non a servizi REST diretti. Ogni Engine
è una classe Python con metodo `process()` (o equivalente) che riceve/ritorna
dati contrattati.

---

## 2. Mappa Engine → contratti

| Engine | Produce | Consuma |
|---|---|---|
| **Import Engine** | `RawGPSPoint`, `session_id` | file GPX/FIT/Strava |
| **Tracking Engine** | `RawGPSPoint`, `session_id` | GPS live, sensori BLE |
| **Measurement Engine** | `NormalizedMovementPoint` | `RawGPSPoint` |
| **Analysis Engine** | `SessionSummary` | `NormalizedMovementPoint` |
| **Territory Engine** | `TerritorySegment` | `NormalizedMovementPoint`, dati geografici esterni |
| **Knowledge Layer** | `AthleteKnowledgeState`, `RouteDifficulty`, `PerformancePrediction` | `SessionSummary`, `TerritorySegment`, `daily_status`, `environment_readings` |
| **AI Coach** | `CoachResponse` | `AthleteKnowledgeState`, `RouteDifficulty`, `PerformancePrediction`, `CoachRequest` |

> **Nota:** il Data Layer (DB) non è un Engine: è un **outbox** condiviso.
> Ogni Engine persiste i propri output nel DB, ma nessun Engine "parla" direttamente
> con un altro Engine tramite DB. La comunicazione è sempre in-memory o via eventi.

---

## 3. Pattern di comunicazione

### 3.1 Pipeline sincrona (batch)
Usata per elaborazione non-real-time (import, analisi storica):
```
RawGPSPoint[] → MeasurementEngine → NormalizedMovementPoint[] → AnalysisEngine → SessionSummary
```

### 3.2 Pipeline streaming (live)
Usata per tracking in tempo reale:
```
TrackingEngine → RawGPSPoint (stream) → MeasurementEngine → NormalizedMovementPoint (buffer)
                                                              → TerritoryEngine (segment detection)
```

### 3.3 Eventi + polling (Knowledge Layer)
Il Knowledge Layer non è attivato da ogni punto: scatta su **trigger**:
- Fine sessione (`SessionSummary` disponibile).
- Aggiornamento `daily_status` (es. HRV del mattino).
- Cambio condizioni meteo su segmento.
- Richiesta esplicita AI Coach.

---

## 4. Dettaglio Engine

### 4.1 Import Engine

**Responsabilità:** normalizzare sorgenti esterne nel contratto `RawGPSPoint`.

**Dependency:** nessuna (foglia della pipeline). Parser specifici per formato.

**Pseudocodice:**
```python
class ImportEngine:
    def import_gpx(self, file_path) -> list[RawGPSPoint]
    def import_fit(self, file_path) -> list[RawGPSPoint]
    def import_strava(self, oauth_token, activity_id) -> list[RawGPSPoint]
```

**Persistenza:** scrive `RawGPSPoint` nel Data Layer (`movement_points` raw)
e crea record `sessions` + `imports`.

---

### 4.2 Tracking Engine

**Responsabilità:** acquisire GPS+sensori da dispositivo live e produrre `RawGPSPoint`.

**Dependency:** nessuna. Comunica con il dispositivo tramite BLE/WebSocket.

**Pseudocodice:**
```python
class TrackingEngine:
    def start_session(self) -> str  # tracking_session_id
    def ingest_point(self, session_id, gps, sensors) -> RawGPSPoint
    def stop_session(self, session_id) -> Session
```

**Note:** il Tracking Engine non calcola metriche. I punti grezzi sono buffered
e spediti al Measurement Engine in blocchi o su richiesta.

---

### 4.3 Measurement Engine

**Responsabilità:** normalizzare, filtrare e derivare grandezze fisiche
da `RawGPSPoint` → `NormalizedMovementPoint`.

**Dependency:** `core/physics/` (kernel numerico condiviso con `bm2`).

**Pseudocodice:**
```python
class MeasurementEngine:
    def process(self, raw: RawGPSPoint) -> NormalizedMovementPoint
    def smooth(self, points: list[NormalizedMovementPoint]) -> list[NormalizedMovementPoint]
    def filter_gps_accuracy(self, points, max_error_m=20) -> list[NormalizedMovementPoint]
```

**Output:** stream di `NormalizedMovementPoint` verso:
- Analysis Engine (per metriche).
- Territory Engine (per segment detection in tempo reale).

---

### 4.4 Analysis Engine

**Responsabilità:** aggregare `NormalizedMovementPoint` in metriche di sessione.

**Dependency:** `analytics/calculators/*` (power, fatigue, calories, stress,
performance, advanced).

**Pseudocodice:**
```python
class AnalysisEngine:
    def analyze_session(self, session_id) -> SessionSummary
    def detect_zones(self, hr_series, power_series) -> Zones
    def compute_trimp(self, hr_series, duration_s) -> float
```

**Output:** `SessionSummary` → Knowledge Layer (per `fitness_state`/`fatigue_state`)
+ Data Layer (`sessions`).

---

### 4.5 Territory Engine

**Responsabilità:** classificare il territorio percorso in `TerritorySegment`.

**Dependency:** dati geografici esterni (OpenStreetMap, elevation API).

**Pseudocodice:**
```python
class TerritoryEngine:
    def segmentize(self, points: list[NormalizedMovementPoint]) -> list[TerritorySegment]
    def match_existing(self, geometry) -> TerritorySegment | None
    def compute_difficulty(self, segment, weather=None) -> float
```

**Output:** `TerritorySegment` → Knowledge Layer (per `RouteDifficulty`)
+ Data Layer (`territory_segments`, `session_territory_map`).

---

### 4.6 Knowledge Layer

**Responsabilità:** interpretare i dati grezzi/aggregati in stati cognitivi
dell'atleta e predizioni.

**Dependency:** `knowledge_base/` (modelli matematici), storage storico.

**Pseudocodice:**
```python
class KnowledgeLayer:
    def compute_fitness_state(self, athlete_id, date) -> AthleteKnowledgeState
    def compute_route_difficulty(self, segment_id, weather=None) -> RouteDifficulty
    def predict_performance(self, athlete_id, segment_id, conditions) -> PerformancePrediction
```

**Regola:** il Knowledge Layer **non riceve** `RawGPSPoint` o `NormalizedMovementPoint`.
Riceve solo `SessionSummary`, `TerritorySegment`, `daily_status`, `environment_readings`.

**Output:** tutti i contratti del §5 di `bm2/data-contracts.md` → Data Layer
(`knowledge_states`) + AI Coach.

---

### 4.7 AI Coach

**Responsabilità:** rispondere a domande dell'utente in linguaggio naturale,
basandosi ESCLUSIVAMENTE su oggetti del Knowledge Layer.

**Dependency:** LLM (locale o cloud), RAG su `knowledge_base/`.

**Pseudocodice:**
```python
class AICoach:
    def ask(self, athlete_id, question) -> CoachResponse
    def recommend(self, athlete_id) -> list[Recommendation]
```

**Regola:** l'AI Coach **non può** accedere al Data Layer grezzo.
Tutti i dati passano attraverso il Knowledge Layer.

---

## 5. Diagramma di sequenza (elaborazione sessione)

```
[Tracking/Import]
        │
        ▼
  RawGPSPoint[]
        │
        ▼
  ┌─────────────────┐
  │ Measurement     │
  │ Engine           │
  └─────────────────┘
        │
        ▼
  NormalizedMovementPoint[]
        │
   ┌────┴────┐
   │         │
   ▼         ▼
Analysis   Territory
 Engine     Engine
   │         │
   ▼         ▼
SessionSummary  TerritorySegment
   │         │
   └────┬────┘
        │
        ▼
  ┌─────────────────┐
  │ Knowledge Layer  │
  └─────────────────┘
        │
        ▼
  ┌─────────────────┐
  │    AI Coach      │
  └─────────────────┘
```

---

## 6. Error handling & fallback

| Caso | Comportamento |
|---|---|
| Measurement Engine fallisce | Tracking Engine buffera; ritenta o marca sessione come `incompleta` |
| Analysis Engine fallisce | Sessione persiste senza metriche; notifica admin |
| Territory Engine fallisce | Prosegue senza segmenti; non blocca analisi |
| Knowledge Layer fallisce | AI Coach risponde "dati non disponibili"; non inventa |

Nessun Engine deve mai lanciare eccezioni non gestite verso l'esterno della pipeline.

---

## 7. Versionamento contratti

Ogni contratto JSON ha campo `type` con formato `NomeContratto.v{MAJOR}`.
Esempi:
- `RawGPSPoint.v1`
- `NormalizedMovementPoint.v1`
- `SessionSummary.v1`
- `AthleteKnowledgeState.v1`

Cambiamenti **breaking** (rimozione campo, rename, cambio tipo) → bump MAJOR.
Cambiamenti **additivi** (nuovo campo opzionale) → MINOR (solo se backward compatibile).
Fix (documentazione, valori enum) → PATCH.

Engine che ricevono un contratto con version sconosciuta:
- Se `MAJOR` > supported → fallisci con errore esplicito.
- Se `MINOR` > supported → ignora campi sconosciuti, procedi.

---

## 8. Configurazione Engine

Ogni Engine è configurabile via dependency injection:

```python
measurement_engine = MeasurementEngine(
    physics_kernel=core_physics,
    gps_accuracy_threshold_m=20,
    smoothing_window_s=5,
)

analysis_engine = AnalysisEngine(
    calculators=load_calculators(),
    hr_max_default=190,
    hr_rest_default=60,
)

knowledge_layer = KnowledgeLayer(
    storage=postgres_repository,
    fitness_model=ctl_atl_model,
    weather_provider=openweathermap,
)
```

Nessun Engine legge config da env/DB direttamente: riceve le dipendenze dal
composition root (Application layer / `app_factory.py`).

---

## 9. Testabilità

Ogni Engine deve essere testabile in isolamento:
- Input: mock di contratti JSON.
- Output: asserzione su contratti JSON.
- Dependency: mock (es. `physics_kernel` fake, `storage` fake).

Nessun Engine dipende da:
- Network (eccetto provider esterni espliciti, mockati).
- DB (eccetto repository iniettato).
- Stato globale / singleton non dichiarati.
