# Modelli di Dominio

Riferimento delle entità di dominio (dataclass pure, senza dipendenze infrastrutturali) e degli oggetti del motore di simulazione BikeMaster 2.0.

- **Dominio core:** `bike_analyzer/core/models.py`, `bike_analyzer/core/fitness_state.py`
- **BM2:** `bike_analyzer/bm2/units.py`, `models.py`, `transformer.py`, `algorithms/base.py`, `simulation.py`, `knowledge.py`

---

## 1. Dominio core

### `GPSPoint` (`core/models.py`, frozen)
Singolo campione della traccia GPS.

| Campo | Tipo | Significato |
|---|---|---|
| `lat` | `float` | Latitudine (gradi, WGS84) |
| `lon` | `float` | Longitudine (gradi, WGS84) |
| `timestamp` | `datetime` | Istante del campione |
| `altitude` | `float \| None` | Quota (m) |
| `speed` | `float \| None` | Velocità |
| `power` | `float \| None` | Potenza (W) |
| `heart_rate` | `float \| None` | Frequenza cardiaca (bpm) |
| `cadence` | `float \| None` | Cadenza (rpm) |

Metodo: `distance_to(other)` → distanza haversine.
Helper modulo: `haversine_distance_m(lat1, lon1, lat2, lon2)` (`EARTH_RADIUS_M = 6_371_000`).

### `Segment` (`core/models.py`)
Sotto-sezione di una ride tra due punti.

| Campo | Tipo | Default | Significato |
|---|---|---|---|
| `start` | `GPSPoint` | — | Punto iniziale |
| `end` | `GPSPoint` | — | Punto finale |
| `distance_m` | `float` | 0.0 | Lunghezza (m) |
| `duration_s` | `float` | 0.0 | Durata (s) |
| `avg_speed_km_h` | `float` | 0.0 | Velocità media |
| `elevation_gain_m` | `float` | 0.0 | Dislivello positivo (m) |
| `elevation_loss_m` | `float` | 0.0 | Dislivello negativo (m) |

### `Pause` (`core/models.py`)
Intervallo di sosta.

| Campo | Tipo | Default | Significato |
|---|---|---|---|
| `start` | `datetime` | — | Inizio pausa |
| `end` | `datetime` | — | Fine pausa |
| `duration_s` | `float` | 0.0 | Durata (s) |

### `RouteStatistics` (`core/models.py`)
Statistiche aggregate del percorso.

| Campo | Tipo | Default |
|---|---|---|
| `total_distance_m` | `float` | 0.0 |
| `total_duration_s` | `float` | 0.0 |
| `total_pause_duration_s` | `float` | 0.0 |
| `avg_speed_km_h` | `float` | 0.0 |
| `max_speed_km_h` | `float` | 0.0 |
| `total_elevation_gain_m` | `float` | 0.0 |
| `total_elevation_loss_m` | `float` | 0.0 |
| `segment_count` | `int` | 0 |
| `pause_count` | `int` | 0 |

### `Ride` (`core/models.py`)
Entità ride completa. Metodi/proprietà: `to_dict()`, `duration_hours`.

| Campo | Tipo | Default | Significato |
|---|---|---|---|
| `id` | `int \| None` | None | PK |
| `athlete_id` | `int \| None` | None | Atleta proprietario |
| `tenant_id` | `int` | 0 | Isolamento tenant |
| `date` | `str` | "" | Data (ISO) |
| `distance_km` | `float` | 0.0 | Distanza |
| `duration_minutes` | `float` | 0.0 | Durata |
| `avg_speed_kmh` | `float` | 0.0 | Velocità media |
| `weight_kg` | `float` | 70.0 | Peso usato |
| `calories` | `float` | 0.0 | Calorie |
| `heart_rate_avg` | `float \| None` | None | FC media |
| `elevation_gain_m` | `float \| None` | None | Dislivello (m) |
| `external_source` | `str \| None` | None | es. `strava` |
| `external_id` | `str \| None` | None | id attività esterna |
| `title` | `str \| None` | None | Titolo |
| `gps_points` | `list[GPSPoint] \| None` | None | Traccia |
| `created_at` | `str \| None` | None | Creazione |
| `activity_type` | `str` | "ride" | Tipo attività |
| `is_official` | `bool` | True | Ufficiale vs stimata |
| `source` | `str` | "manual" | Origine |

### `AthleteProfile` (`core/models.py`)
Profilo atleta. Metodo `to_dict()`.

| Campo | Tipo | Default |
|---|---|---|
| `id` | `int \| None` | None |
| `name` | `str` | "" |
| `age` | `int` | 30 |
| `weight_kg` | `float` | 70.0 |
| `height_cm` | `float \| None` | None |
| `fat_percentage` | `float \| None` | None |
| `years_active` | `int` | 1 |
| `weekly_sessions` | `int` | 3 |
| `monthly_hours` | `float` | 0.0 |
| `annual_hours` | `float` | 0.0 |
| `experience_level` | `str` | "Beginner" |
| `goals` | `str \| None` | None |
| `preferred_terrain` | `str \| None` | None |
| `weekly_volume_km` | `float` | 0.0 |
| `best_segments` | `str \| None` | None |
| `medical_notes` | `str \| None` | None |
| `equipment` | `str \| None` | None |
| `ftp_watts` | `float \| None` | None |
| `created_at` | `str \| None` | None |

### `CalendarEvent` (`core/models.py`)
Evento/allenamento pianificato. Metodo `to_dict()`.

| Campo | Tipo | Default |
|---|---|---|
| `id` | `int \| None` | None |
| `athlete_id` | `int \| None` | None |
| `title` | `str` | "" |
| `event_type` | `str` | "training" |
| `date` | `str` | "" |
| `duration_minutes` | `int` | 0 |
| `description` | `str \| None` | None |
| `completed` | `bool` | False |
| `created_at` | `str \| None` | None |

### `TrainingStressDay` (`core/fitness_state.py`)
Un giorno di metriche di carico.

| Campo | Tipo | Default | Significato |
|---|---|---|---|
| `date` | `date` | — | Giorno |
| `tss` | `float` | 0.0 | Training Stress Score |
| `atl` | `float` | 0.0 | Acute Training Load (7g) |
| `ctl` | `float` | 0.0 | Chronic Training Load (42g) |
| `tsb` | `float` | 0.0 | Training Stress Balance (ctl−atl) |

### `FitnessStateVector` (`core/fitness_state.py`)
Snapshot fisiologico. Metodo `to_dict()`; proprietà calcolate `is_overtraining_risk`, `is_fresh`, `is_ready_for_hard_effort`.

| Campo | Tipo | Default |
|---|---|---|
| `athlete_id` | `int` | — |
| `computed_at` | `datetime` | — |
| `atl` | `float` | 0.0 |
| `ctl` | `float` | 0.0 |
| `tsb` | `float` | 0.0 |
| `fitness` | `float` | 0.0 |
| `fatigue` | `float` | 0.0 |
| `form` | `float` | 0.0 |
| `recovery_hours_needed` | `float` | 0.0 |
| `weekly_tss` | `float` | 0.0 |
| `monthly_tss` | `float` | 0.0 |
| `trend_7d` | `str` | "stable" |
| `trend_30d` | `str` | "stable" |
| `risk_indicators` | `list[str]` | [] |
| `recommendation` | `str` | "" |

---

## 2. Modelli BikeMaster 2.0 (BM2)

### `Quantity` (`bm2/units.py`, frozen)
Misura fondamentale "valore + unità + precisione + fonte". Costruttore helper: `q(...)`.

| Campo | Tipo | Default | Significato |
|---|---|---|---|
| `value` | `float` | — | Valore numerico nell'unità |
| `unit` | `str` | — | Simbolo unità (es. `kg`, `m/s`, `%`) |
| `precision` | `float` | 0.0 | Incertezza assoluta (stessa unità) |
| `source` | `str` | "unknown" | Origine (garmin/strava/manual/gps/dem/estimate…) |
| `timestamp` | `datetime \| None` | None | Istante di misura |

**`UnitRegistry`** (`default_registry`): tabelle di conversione lineari per massa/lunghezza/velocità/tempo/energia/potenza/frequenza/pressione/densità/coppia, più dimensioni non lineari (`slope`, `angle`, `temperature`). Unità canoniche interne: massa→kg, lunghezza→m, velocità→m/s, tempo→s, energia→J, potenza→W, pendenza→%, angolo→deg, frequenza→bpm, temperatura→°C. Metodi: `dimension_of`, `canonical_unit`, `to_canonical`, `convert`, `explain_conversion`.

### `GeoPoint` (`bm2/transformer.py`, frozen)
Punto geografico con proiezione metrica locale.

| Campo | Tipo | Default |
|---|---|---|
| `lat` | `float` | — |
| `lon` | `float` | — |
| `altitude` | `float` | 0.0 |
| `timestamp` | `datetime \| None` | None |
| `x` | `float` | 0.0 (X metrico locale) |
| `y` | `float` | 0.0 (Y metrico locale) |
| `speed` | `float \| None` | None |
| `power` | `float \| None` | None |
| `heart_rate` | `float \| None` | None |
| `cadence` | `float \| None` | None |

### `Athlete` (`bm2/models.py`)
Metodi: `from_raw`, `to_dict`, `from_dict`, `power_to_weight()`.

| Campo | Tipo | Default |
|---|---|---|
| `weight_kg` | `Quantity` | — |
| `age` | `int` | 30 |
| `height_m` | `Quantity \| None` | None |
| `ftp_w` | `Quantity \| None` | None |
| `max_hr_bpm` | `Quantity \| None` | None |
| `resting_hr_bpm` | `Quantity \| None` | None |
| `experience_level` | `str` | "Beginner" |
| `weekly_hours` | `Quantity \| None` | None |
| `name` | `str` | "" |
| `ctl_stress_score` | `Quantity \| None` | None |
| `atl_stress_score` | `Quantity \| None` | None |
| `tsb_stress_score` | `Quantity \| None` | None |

### `Bike` (`bm2/models.py`)

| Campo | Tipo | Default | Significato |
|---|---|---|---|
| `weight_kg` | `Quantity` | — | Peso bici |
| `crr` | `float` | 0.005 | Coeff. resistenza rotolamento |
| `cda` | `float` | 0.40 | Area frontale × Cd |
| `drivetrain_efficiency` | `float` | 0.97 | Efficienza trasmissione |
| `name` | `str` | "" | |
| `category` | `str` | "road" | road/gravel/mtb/other |
| `gear_ratio` | `float \| None` | None | Rapporto |

### `Activity` (`bm2/models.py`)
Metodo `metrics(t)` → distance_m, duration_s, gain_m, loss_m, avg_slope_percent, avg_speed_ms.

| Campo | Tipo | Default |
|---|---|---|
| `points` | `list[GeoPoint]` | — |
| `title` | `str` | "" |
| `sport` | `str` | "cycling" |
| `laps` | `list[dict]` | [] |
| `segments` | `list[dict]` | [] |
| `summary` | `dict` | {} |

### `WorldObject` (`bm2/models.py`)
Condizioni ambientali/territorio.

| Campo | Tipo | Default |
|---|---|---|
| `surface` | `str` | "asphalt" |
| `roughness_index` | `Quantity` | q(0.0, "") |
| `avg_slope_percent` | `Quantity \| None` | None |
| `wind_speed_ms` | `Quantity \| None` | None |
| `temperature_c` | `Quantity \| None` | None |

### `AnalysisContext` (`bm2/models.py`)
Contesto di analisi che raggruppa gli oggetti. Proprietà `total_mass_kg`.

| Campo | Tipo |
|---|---|
| `athlete` | `Athlete` |
| `activity` | `Activity` |
| `bike` | `Bike` |
| `world` | `WorldObject` |
| `transformer` | `TransformerEngine` |

### `ModelResult` (`bm2/algorithms/base.py`)
Contratto universale di output di ogni algoritmo BM2. Metodi: `to_dict`, `from_dict`, `uncertainty_bounds()`, `compare_with(other)`.

| Campo | Tipo | Significato |
|---|---|---|
| `value` | `float` | Risultato nell'unità |
| `unit` | `str` | Unità risultato |
| `formula` | `str` | Formula/metodo applicato |
| `data_used` | `list[str]` | Input consumati |
| `precision` | `float` | Incertezza assoluta |
| `confidence` | `float` | Affidabilità 0..1 |
| `source` | `str` | Algoritmo/metodo produttore |
| `details` | `dict` | Output secondari |

La classe base **`Algorithm`** (ABC) definisce `run(ctx, extra) -> ModelResult`, una mappa `SOURCE_CONFIDENCE` e i controlli `_has_input`.

### Simulazione what-if (`bm2/simulation.py`)

- **`ScenarioOverride`**: `athlete_weight_delta_kg`, `bike_weight_delta_kg`, `slope_delta_percent`, `cda_override`, `experience_override`.
- **`SimulationComparison`**: `baseline: dict[str, ModelResult]`, `scenario: dict[str, ModelResult]`, `deltas: dict[str, float]`; `to_dict`, `summary`.
- **`ScenarioPresets`**: `PRESETS` (race/training/light_bike); `names/get/build`.
- **`SensitivityPoint`**: `param_value`, `results: dict[str, float]`.
- **`SensitivityResult`**: `param`, `values`, `points`; `curve(algorithm_name)`, `to_dict`.

### `Insight` (`bm2/knowledge.py`)
Output interpretato del Knowledge Layer. Metodo `to_dict`.

| Campo | Tipo | Default | Significato |
|---|---|---|---|
| `concept` | `str` | — | Concetto |
| `detail` | `str` | — | Spiegazione |
| `severity` | `str` | "info" | info \| note \| warning \| critical |

`KnowledgeEngine.explain(results: dict[str, ModelResult]) -> list[Insight]`.

---

## 3. Relazione dominio ↔ persistenza

Gli oggetti BM2 sono in-memory/serializzabili (`to_dict`/`from_dict` con round-trip via `Quantity`). Vengono persistiti indirettamente: `Athlete`/`Activity`/`WorldObject`/`Bike` mappano sulle tabelle `athletes`/`rides`/`fitness_states` tramite gli adapter in `bm2/adapters.py` e `db/`; gli output `ModelResult`/`Insight` sono salvati come JSON in `metrics`, `fitness_states.risk_indicators/recommendation`, e i chunk RAG in `knowledge_chunks`. Vedi [database-schema.md](./database-schema.md).
