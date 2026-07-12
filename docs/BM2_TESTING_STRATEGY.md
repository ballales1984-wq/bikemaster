# BikeMaster 2.0 — Strategia di Testing

**Versione:** Bozza 1.0
**Riferimento:** `tests/test_bm2_*.py`, `docs/DEVELOPMENT.md`

---

## 1. Filosofia

I test BMW 2.0 seguono la stessa disciplina del resto del progetto:
- **Test unit** per ogni algoritmo e modello.
- **Test di integrazione** per adapter e endpoint.
- **Niente fixture magiche**: ogni test costruisce il proprio contesto con dati
  deterministici.
- **Copertura obiettivo**: core BMW 2.0 >= 90% (gli engine esistenti sono coperti
  separatamente).

---

## 2. Struttura dei test

```
tests/
├── test_bm2_units.py          # UnitRegistry, Quantity, conversioni
├── test_bm2_models.py         # Athlete, Bike, Activity, WorldObject, AnalysisContext
├── test_bm2_engine.py         # Algoritmi, orchestrator, simulazione, knowledge
├── test_bm2_ride_adapter.py   # Adapter Ride → AnalysisContext
├── test_bm2_routes_integration.py  # Endpoint FastAPI
├── test_bm2_api.py            # API BMW 2.0 specifiche
└── test_bm2_agents.py         # AIOrchestrator, agenti NL
```

Ogni file segue il pattern:
```
test_bm2_{modulo}.py
```

---

## 3. Pattern di test

### 3.1 Contesti deterministici

Ogni test che serve un `AnalysisContext` usa una factory locale:

```python
def _ctx():
    t = TransformerEngine()
    athlete = Athlete(
        weight_kg=t.normalize(q(75.0, "kg", source="manual")),
        age=34, max_hr_bpm=t.normalize(q(190.0, "bpm")), experience_level="Intermediate",
    )
    bike = Bike(weight_kg=t.normalize(q(8.0, "kg", source="manual")))
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc)),
    ]
    activity = Activity(points=pts)
    world = WorldObject(surface="asphalt", avg_slope_percent=t.normalize(q(5.0, "%", source="dem")))
    return AnalysisContext(athlete=athlete, activity=activity, bike=bike, world=world, transformer=t)
```

**Regola:** non usare fixture condivise tra test diversi. Se serve una variante
(es. senza HR), creare una factory dedicata.

### 3.2 Asserzioni su ModelResult

Ogni test di algoritmo verifica:

```python
def test_energy_model_reports_provenance():
    r = EnergyModel().run(_ctx())
    assert r.unit == "kcal"
    assert r.value > 0
    assert r.formula                     # formula non vuota
    assert "massa_totale" in r.data_used # input tracciato
    assert 0.0 <= r.confidence <= 1.0    # confidence valida
    assert r.precision > 0               # precisione positiva
```

**Cosa NON asserire:**
- Valori esatti fissi (la fisica può cambiare con refactor).
- Confidenza esatta (dipende da completeness input).

### 3.3 Edge case

| Caso | Test obbligatorio |
|---|---|
| Durata zero / punti vuoti | `test_movement_model_zero_duration_safe` |
| Input mancanti | `test_algorithm_returns_zero_when_inputs_missing` |
| Valori estremi | peso 0, pendenza 100%, velocità 0 |
| Conversioni unità | `test_unitregistry_*` in `test_bm2_units.py` |

---

## 4. Fixture condivise (uso limitato)

Se più test nella stessa classe usano lo stesso setup, usare `@pytest.fixture`
a livello di modulo. **Non** esportare fixture in `conftest.py` globale per
BM2: ogni modulo BMW 2.0 è autocontenuto.

```python
# test_bm2_engine.py
@pytest.fixture
def ctx():
    return _ctx()
```

---

## 5. Mock

- **DB/filestore**: mockare con `unittest.mock` o factory fake.
- **API esterne** (meteo, strava): non chiamare in test. Usare dati fixati.
- **Kernel fisico**: non mockare. Testare `core/physics/` separatamente e
  verificare che BMW 2.0 chiami le funzioni corrette (es. con `unittest.mock.patch`).

---

## 6. Test di integrazione

### 6.1 Adapter

Verificare che oggetti del dominio esistente si convertano correttamente:

```python
def test_ride_to_analysis_context_preserves_data():
    ride = RideFactory.build(...)  # factory da test esistenti
    ctx = ride_to_analysis_context(ride, athlete)
    assert ctx.athlete.weight_kg.value == ride.athlete.weight_kg
    assert len(ctx.activity.points) == len(ride.points)
```

Usare le factory già presenti in `tests/factories.py` se disponibili.

### 6.2 Endpoint FastAPI

Usare `TestClient`:

```python
from fastapi.testclient import TestClient
from bike_analyzer.backend.api.app_factory import create_app

client = TestClient(create_app())

def test_bm2_simulate_ride():
    resp = client.post("/api/v1/bm2/simulate-ride", json=payload, headers=auth_header)
    assert resp.status_code == 200
    data = resp.json()
    assert "estimated_power_w" in data
```

**Nota:** autenticazione. Se l'endpoint richiede JWT, generare un token di test
o mockare `get_current_user`.

### 6.3 Pipeline end-to-end

Verificare flusso completo:
`RawGPSPoint[] → MeasurementEngine → AnalysisEngine → KnowledgeLayer → CoachResponse`

```python
def test_full_pipeline_produces_coach_response():
    raw_points = load_fixture("raw_gps_batch.json")
    # ... pipeline
    response = coach.ask(athlete_id, "Come va?")
    assert response.type == "CoachResponse"
    assert response.based_on
```

---

## 7. Esecuzione

```bash
# Tutti i test BMW 2.0
pytest tests/test_bm2_*.py -v

# Singolo modulo
pytest tests/test_bm2_engine.py -v

# Con copertura
pytest tests/test_bm2_*.py --cov=bike_analyzer.bm2 --cov-report=term-missing

# Solo fast (no integrazione)
pytest tests/test_bm2_*.py -v -m "not integration"
```

**Marcatori consigliati:**

```python
# conftest.py o test_bm2_*.py
@pytest.mark.unit
def test_algoritmo(): ...

@pytest.mark.integration
def test_endpoint(): ...

@pytest.mark.slow
def test_pipeline_larga(): ...
```

---

## 8. Regressioni

Quando si modifica un algoritmo:

1. Eseguire `pytest tests/test_bm2_*.py` prima della modifica (baseline).
2. Modificare algoritmo.
3. Rieseguire test.
4. Se un test di asserzione valori fallisce, aggiornare test + documentazione
   (`BM2_ALGORITHMS.md`).
5. Non rimuovere mai asserzioni su struttura `ModelResult`.

Quando si modifica un contratto JSON:
1. Aggiornare `bm2/data-contracts.md`.
2. Aggiornare test che serializzano/deserializzano il contratto.
3. Eseguire `pytest` su adapter e integrazione.

---

## 9. Coverage target

| Modulo | Target | Note |
|---|---|---|
| `bm2/algorithms/` | 95% | Cuore del sistema |
| `bm2/models.py` | 95% | Entità dominio |
| `bm2/units.py` | 90% | Conversioni, edge case unità |
| `bm2/simulation.py` | 85% | Preset, sensitivity, override |
| `bm2/adapters.py` | 90% | Conversioni dominio ↔ BMW 2.0 |
| `bm2/knowledge.py` | 80% | Dipende da storage |
| `bm2/agents.py` | 70% | Dipende da LLM (mockato) |

Totale progetto BMW 2.0: **>= 85%**.
