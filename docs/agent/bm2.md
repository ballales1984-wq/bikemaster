# BM2

## Progetto BikeMaster 2.0 (`bm2/`) — Deluxe Simulation Engine

`bike_analyzer/bm2/` è il motore di **simulazione sportiva** ("what-if") della visione "BikeMaster Deluxe". A differenza di AetherMap, **è parte del prodotto** e risiede dentro il package `bike_analyzer`.

- Filosofia type-safe: `Quantity` + `UnitRegistry` (analisi dimensionale), algoritmi `Algorithm`→`ModelResult`, dominio proprio `AnalysisContext`.
- **Kernel fisico condiviso**: `bm2` delega a `bike_analyzer/core/physics/` (`cycling_forces`, `instantaneous_power`, `required_speed_for_power`). Non duplicare la fisica in `bm2`: usare `core.physics`.
- È **già cablato** via `bike_analyzer/backend/api/bm2_routes.py` (montato in `app_factory.py`) e testato da `tests/test_bm2_*.py`.
- **Non è ancora integrato** col flusso `Ride`/analytics esistente, né validato su dati reali di potenza/HR. Vedi `ROADMAP.md` (Track D) per stato e next-step.

## Struttura bm2/

```
bike_analyzer/bm2/
├── __init__.py            # esporta Quantity, TransformerEngine, Athlete, Bike, Activity, WorldObject, Algorithm, ModelResult, SimulationEngine, KnowledgeEngine, AIOrchestrator, Agents
├── units.py               # Quantity (value+unit+precision+source+timestamp) + UnitRegistry
├── transformer.py         # TransformerEngine (UnitConverter + GeoTransformer + TimeTransformer + DataQuality)
├── models.py              # Athlete, Bike, Activity, WorldObject, AnalysisContext
├── algorithms/            # 9 algoritmi: MovementModel, EnergyModel, PerformanceModel, FatigueModel, RouteDifficultyModel, RecoveryModel, NutritionModel, PowerModel, TrainingLoadModel
├── simulation.py          # SimulationEngine + ScenarioOverride + parse_override_from_text
├── knowledge.py           # KnowledgeEngine (numeri → Insight numerici)
├── orchestrator.py        # AIOrchestrator (routing domanda → modelli, assemblaggio contesto)
└── agents.py              # GPSAgent, AthleteAgent, EnvironmentAgent, SensorAgent, StravaAgent, GarminAgent
```

## API BM2

Montato in `app_factory.py` sotto `/api/v1/bm2`:
- `POST /api/v1/bm2/ask` — chiedi consiglio all'AI Coach
- `POST /api/v1/bm2/simulate` — simulazione what-if
- `POST /api/v1/bm2/simulate-ride` — simulazione su ride reale
- `POST /api/v1/bm2/validate` — valida input
