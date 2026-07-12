# BikeMaster 2.0 — Guida all'integrazione

**Versione:** Bozza 1.0
**Riferimento:** `docs/ARCHITECTURE.md` (sezione 5), `docs/BM2_ENGINE_ARCHITECTURE.md`

---

## 1. Dove si inserisce BM2 nel sistema esistente

BM2 è un **sottosistema isolato ma già connesso** all'app FastAPI esistente.
Non sostituisce `core/engine.py` o `core/pipeline.py`: li integra tramite
gli adapter già presenti in `bike_analyzer/bm2/adapters.py`.

```
Frontend Vue
    │
FastAPI (routes.py, app_factory.py)
    │
    ├── Engine esistenti (Import, Tracking, Analysis, ecc.)
    │
    ├── bm2_routes.py  →  Adapter BMW 2.0 (già montato)
    │                               │
    │                               ▼
    │                    bm2/orchestrator.py
    │                    bm2/simulation.py
    │                    bm2/knowledge.py
    │
    └── core/physics/  →  kernel numerico condiviso
```

---

## 2. Endpoint già cablati

Verificare in `bike_analyzer/backend/api/bm2_routes.py` e `app_factory.py`.

| Endpoint | Metodo | Stato |
|---|---|---|
| `/api/v1/bm2/simulate-ride` | POST | ✅ cablato |
| `/api/v1/bm2/simulate-preset` | POST | 🟡 da verificare |
| `/api/v1/bm2/simulation` | POST/GET | 🟡 da verificare |
| `/api/v1/bm2/models` | GET | 🟡 da verificare |

Consultare `tests/test_bm2_*.py` per endpoint attivi e payload accettati.

---

## 3. Flusso di integrazione per nuova feature

Quando si aggiunge una feature che coinvolge BM2:

1. **Frontend** chiama endpoint FastAPI esistente o nuovo.
2. ** routes.py** valida auth, parametri, chiama il servizio o Engine appropriato.
3. **Adapter BMW 2.0** (`bm2/adapters.py`) converte oggetti del dominio esistente
   in `AnalysisContext` (o sottoclasse).
4. **BM2 Engine** esegue logica pura (algoritmi, simulazione, knowledge).
5. **Risposta** convertita in JSON contrattato e restituita al client.

```
Client → routes.py → adapter.py → BM2 Engine → JSON → Client
```

---

## 4. Adapter pattern

`bm2/adapters.py` contiene le conversioni tra dominio esistente e dominio BMW 2.0.

**Esempio tipico:**
```python
from bike_analyzer.bm2.models import AnalysisContext, Athlete, Bike, Activity, WorldObject
from bike_analyzer.bm2.transformer import TransformerEngine

def ride_to_analysis_context(ride: Ride, athlete: AthleteProfile) -> AnalysisContext:
    t = TransformerEngine()
    points = [t.ingest_gps_point(p) for p in ride.points]
    activity = Activity.from_raw_points(points)
    bike = Bike.from_ride_bike(ride.bike)
    world = WorldObject.from_activity(activity)
    return AnalysisContext(
        athlete=Athlete.from_profile(athlete),
        bike=bike,
        activity=activity,
        world=world,
        transformer=t,
        total_mass_kg=athlete.weight_kg + bike.weight_kg,
    )
```

**Regola:** l'adapter è l'**unico** punto dove i due domini si toccano.
Non mescolare oggetti BMW 2.0 dentro `core/pipeline.py` o `analytics/*`.

---

## 5. Kernel numerico condiviso

`core/physics/` è il kernel fisico condiviso tra BM2 e il sistema esistente.

| File BMW 2.0 | File core | Funzione |
|---|---|---|
| `bm2/algorithms/base.py:_cycling_forces` | `core/physics/cycling_forces.py` | Forze di resistenza |
| `bm2/algorithms/power_model.py:_power_for_speed` | `core/physics/instantaneous_power.py` | Potenza richiesta |
| `bm2/algorithms/power_model.py:_speed_for_power` | `core/physics/required_speed_for_power.py` | Velocità sostenibile |

**Regola:** se serve una formula fisica in BMW 2.0, cercala prima in `core/physics/`.
Se non esiste, implementala lì (non dentro `bm2/algorithms/`).

---

## 6. Estensione del frontend

Per aggiungere una UI per BMW 2.0:

1. **Componente Vue** in `frontend/src/components/` (es. `SimulationPanel.vue`).
2. **Store Pinia** in `frontend/src/stores/` se serve stato locale.
3. **Chiamata API** tramite `frontend/src/utils/api.ts` (usare `apiPost`/`apiGet`).
4. **Routing** in `frontend/src/router/index.ts` se serve pagina dedicata.

**Convenzioni:**
- Tipi TypeScript: definire interfacce corrispondenti ai contratti JSON BM2.
- Non duplicare logica di calcolo nel frontend: tutto passa dal backend.
- Riutilizzare componenti esistenti (es. `RidesPanel.vue` per display risultati).

---

## 7. Database: migrazioni e schema

BM2 usa lo stesso DB del sistema esistente (Alembic).

Se si aggiungono tabelle per BMW 2.0:
1. Definire modello SQLAlchemy in `bike_analyzer/backend/db/models.py` (o modulo dedicato).
2. Generare migration: `alembic revision --autogenerate -m "add_bm2_X"`.
3. Applicare migration: `alembic upgrade head`.
4. Verificare con `pytest` che i test di integrazione passino.

**Tabelle già presenti** (vedi `bm2/database-schema.md`):
- `sessions`, `movement_points`, `territory_segments`, `knowledge_states`, ecc.

---

## 8. Testing di integrazione

Per verificare che BM2 sia correttamente integrato:

1. **Test unit** (già presenti): `tests/test_bm2_*.py` eseguono algoritmi in isolamento.
2. **Test di integrazione**: chiamare endpoint FastAPI e verificare risposta.
   ```bash
   pytest tests/test_bm2_integration.py -v
   ```
3. **Test di adapter**: verificare conversione `Ride` → `AnalysisContext`.
   ```bash
   pytest tests/test_bm2_adapters.py -v
   ```

Se non esiste `test_bm2_integration.py`, crearlo con `TestClient` FastAPI.

---

## 9. Checklist nuove feature BMW 2.0

- [ ] Contratto JSON definito in `bm2/data-contracts.md`
- [ ] Schema DB aggiornato in `bm2/database-schema.md` (se serve persistenza)
- [ ] Algoritmo/i in `bm2/algorithms/` (se serve calcolo)
- [ ] Adapter in `bm2/adapters.py` (se serve connettersi al dominio esistente)
- [ ] Endpoint in `bm2_routes.py` + registrato in `app_factory.py`
- [ ] Test unit in `tests/test_bm2_*.py`
- [ ] Componente frontend + chiamata API
- [ ] Documentazione aggiornata in `docs/BM2_*.md`
