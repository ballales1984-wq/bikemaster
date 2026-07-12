# BikeMaster 2.0 — Specifica Algoritmi

**Versione:** Bozza 1.0
**Riferimento:** `docs/BM2_ENGINE_ARCHITECTURE.md`, `bike_analyzer/bm2/algorithms/`

---

## 1. Filosofia

Ogni algoritmo in BM2:
- È **puro**: dipende solo da `AnalysisContext` (dati normalizzati).
- È **trasparente**: espone formula, input usati, precisione e confidenza.
- È **componibile**: più algoritmi possono essere orchestrati insieme.
- È **testabile**: niente I/O, niente side-effect, nessuna dipendenza esterna.

Tutti gli algoritmi ereditano da `Algorithm` (`bm2/algorithms/base.py:94`),
che definisce il contratto:
- `name`, `formula`, `description`, `unit`, `required_inputs`
- `_compute(ctx, extra) → (value, precision, confidence)`
- `_extra_details(ctx, extra) → dict`
- `run(ctx, extra) → ModelResult` (template method)

`ModelResult` (`bm2/algorithms/base.py:24`) incapsula:
`value`, `unit`, `formula`, `data_used`, `precision`, `confidence`, `source`, `details`.

---

## 2. Catalogo algoritmi

### 2.1 MovementModel
- **File:** `bm2/algorithms/movement.py`
- **Nome:** `MovementModel`
- **Formula:** `v_media = distanza / durata; v_max = max(samples); a = d(v)/d(t)`
- **Unità:** `m/s`
- **Input richiesti:** `gps_points`, `distanza`, `durata`
- **Output:** velocità media, massima, accelerazione massima.
- **Confidenza base:** 0.95 (con >= 2 punti GPS)

### 2.2 EnergyModel
- **File:** `bm2/algorithms/energy.py`
- **Nome:** `EnergyModel`
- **Formula:** `P = (crr·m·g + m·g·sin(atan(slope)) + ½·ρ·CdA·v²)·v; kcal = P·t / (η·4184)`
- **Unità:** `kcal`
- **Input richiesti:** `massa_totale`, `velocità`, `pendenza`, `durata`, `crr`, `cda`
- **Output:** calorie stimate, potenza meccanica/metabolica.
- **Confidenza base:** 0.85 (se c'è dislivello), 0.70 altrimenti.
- **Note:** delega a `core/physics/cycling_forces` (kernel numerico unico).

### 2.3 FatigueModel
- **File:** `bm2/algorithms/fatigue.py`
- **Nome:** `FatigueModel`
- **Formula:** `score = min(10, (durata·0.3 + intensità·0.3 + velocità·0.2 + dislivello·0.1 + peso·0.1)·3)`
- **Unità:** `score` (0–10)
- **Input richiesti:** `durata`, `intensità`, `velocità`, `dislivello`, `peso`
- **Output:** punteggio fatica, ore di recupero stimate, raccomandazione.
- **Confidenza base:** 0.75 (0.85 se disponibile HR max).

### 2.4 PerformanceModel
- **File:** `bm2/algorithms/performance.py`
- **Nome:** `PerformanceModel`
- **Formula:** `indice = clamp(v_media_kmh / v_riferimento(experience) · 100, 0, 120)`
- **Unità:** `score`
- **Input richiesti:** `velocità_media`, `experience_level`
- **Output:** indice di prestazione normalizzato, velocità di riferimento.
- **Confidenza base:** 0.70 (0.85 per Advanced/Elite).
- **Velocità riferimento:**
  - Beginner: 18 km/h
  - Intermediate: 24 km/h
  - Advanced: 30 km/h
  - Elite: 36 km/h

### 2.5 PowerModel
- **File:** `bm2/algorithms/power_model.py`
- **Nome:** `PowerModel`
- **Formula:** `P = (crr·m·g + m·g·slope + ½·ρ·CdA·v²)·v / η; v_ftp = risolvi P=FTP`
- **Unità:** `W`
- **Input richiesti:** `ftp`, `massa_totale`, `pendenza`, `crr`, `cda`, `efficienza`
- **Output:** potenza stimata, velocità sostenibile.
- **Confidenza base:**
  - Con power meter: 0.95
  - Con FTP stimata: 0.50–0.75
- **Note:**
  - Se disponibile potenza da sensori, usa valore medio sensori.
  - Se disponibile FTP, risolve numericamente `v_ftp` tramite `core/physics/required_speed_for_power`.
  - Delega a `core/physics/` per forze e potenza.

### 2.6 TrainingLoadModel
- **File:** `bm2/algorithms/training_load.py`
- **Nome:** `TrainingLoadModel`
- **Formula:** `TSS = (t·NP·IF) / (FTP·3600) · 100; CTL = EMA_42(TSS); ATL = EMA_7(TSS); TSB = CTL - ATL`
- **Unità:** `score`
- **Input richiesti:** `ftp`, `storico_attivita`
- **Output:** CTL, ATL, TSB.
- **Confidenza base:**
  - Con storico >= 7 giorni: 0.80
  - Con storico 1–7 giorni: 0.60
  - Senza storico: 0.30
- **Note:** accetta `activity_history` (list[dict]) nel parametro `extra`.
  `dict` deve contenere `duration_s` e `avg_power_w`.

### 2.7 RecoveryModel
- **File:** `bm2/algorithms/recovery.py`
- **Nome:** `RecoveryModel`
- **Formula:** `readiness = clamp(100 - fatica·6 - sonno_carenza·4 + hrv_bonus, 0, 100)`
- **Unità:** `score` (0–100)
- **Input richiesti:** `fatica`, `sonno_ore`, `hrv`
- **Output:** readiness, fatica, ore recupero, dettagli sonno/HRV.
- **Confidenza base:** 0.70 (0.40 senza sonno/HRV).
- **Dipendenza:** usa `FatigueModel` internamente.

### 2.8 RouteDifficultyModel
- **File:** `bm2/algorithms/route_difficulty.py`
- **Nome:** `RouteDifficultyModel`
- **Formula:** `difficoltà = clamp(100 · (0.3·norm(distanza) + 0.3·norm(dislivello) + 0.25·norm(pendenza) + 0.15·rugosità) / capacità, 0, 100)`
- **Unità:** `score` (0–100)
- **Input richiesti:** `distanza`, `dislivello`, `pendenza`, `rugosità`, `capacità_atleta`
- **Output:** punteggio difficoltà, categoria, superficie.
- **Categorie:**
  - < 20: Facile
  - < 45: Moderato
  - < 70: Impegnativo
  - >= 70: Estremo
- **Roughness factor:** asphalt 1.0, gravel 1.25, dirt 1.5, trail 1.8.
- **Capacità atleta:** Beginner ×1.3, Intermediate ×1.0, Advanced ×0.8, Elite ×0.65.

### 2.9 NutritionModel
- **File:** `bm2/algorithms/nutrition.py`
- **Nome:** `NutritionModel`
- **Formula:** `carb = intensità·60 g/h · ore; acqua = 0.6 L/h · ore; proteine = 0.3 g/kg (post)`
- **Unità:** `g`
- **Input richiesti:** `durata`, `intensità`, `massa_corpo`
- **Output:** carboidrati, acqua, proteine, kcal totali.
- **Confidenza base:** 0.70.
- **Dipendenza:** usa `FatigueModel` e `EnergyModel` internamente.

---

## 3. Kernel fisico condiviso

Tutti gli algoritmi che richiedono calcoli di forza/potenza/velocità usano
`bike_analyzer.core.physics` come **kernel numerico unico**.

| Funzione | Usata da | File |
|---|---|---|
| `cycling_forces()` | EnergyModel, PowerModel, Algorithm._cycling_forces | `core/physics/cycling_forces.py` |
| `instantaneous_power()` | PowerModel._power_for_speed | `core/physics/instantaneous_power.py` |
| `required_speed_for_power()` | PowerModel._speed_for_power | `core/physics/required_speed_for_power.py` |

**Regola:** nessun algoritmo in `bm2/algorithms/` può duplicare la fisica.
Deve importare da `core.physics`.

---

## 4. Orchestrazione algoritmi

`AnalysisContext` (`bm2/models.py`) è il contenitore di input per tutti gli algoritmi.

```python
@dataclass
class AnalysisContext:
    athlete: Athlete
    bike: Bike
    activity: Activity
    world: WorldObject
    transformer: TransformerEngine
    total_mass_kg: float  # atleta + bici + equipaggiamento
```

`Orchestrator` (`bm2/orchestrator.py`) esegue algoritmi multipli:
```python
orchestrator = Orchestrator(transformer)
result = orchestrator.run_on(
    ctx=analysis_context,
    algorithm_names=["MovementModel", "EnergyModel", "FatigueModel"],
)
# Ritorna dict[str, ModelResult]
```

`AIOrchestrator` (`bm2/agents.py`) orchestra per l'AI Coach, aggiungendo
RAG su `knowledge_base/`.

---

## 5. Precisione e confidenza

| Livello confidenza | Significato |
|---|---|
| 0.9–1.0 | Misura diretta affidabile (power meter, HR band, peso noto). |
| 0.7–0.89 | Stima con buoni input (GPS, FTP nota, superficie nota). |
| 0.5–0.69 | Stima con input parziali (velocità senza pendenza, peso stimato). |
| < 0.5 | Output poco affidabile, da segnalare all'utente. |

`ModelResult.precision` è l'incertezza assoluta sul valore.
`ModelResult.confidence` è l'affidabilità complessiva (0..1).

---

## 6. Estensione

Per aggiungere un nuovo algoritmo:

1. Crea file in `bm2/algorithms/nuovo_algoritmo.py`.
2. Estendi `Algorithm`, imposta `name`, `formula`, `unit`, `required_inputs`.
3. Implementa `_compute(ctx, extra) → (value, precision, confidence)`.
4. Implementa `_extra_details(ctx, extra) → dict` (opzionale).
5. Registra in `bm2/algorithms/__init__.py` → `ALL_ALGORITHMS` e `MODEL_REGISTRY`.
6. Aggiungi test in `tests/test_bm2_*.py`.

**Vietato:** accedere a DB, API esterne, variabili globali dentro `_compute`.
Tutto l'I/O deve avvenire prima/dopo la chiamata a `run()`.
