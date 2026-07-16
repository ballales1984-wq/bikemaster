# BikeMaster 2.0 (BM2) — Deluxe Simulation Engine

BM2 is the "what-if" simulation and knowledge engine inside BikeMaster. It transforms raw ride data into interpreted states (fatigue, recovery, performance, route difficulty) and supports scenario simulations.

**Location:** `bike_analyzer/bm2/`

## Documents

| Document | Description |
|---|---|
| [variables.md](./variables.md) | Variable dictionary — domains, canonical units, gaps vs code |
| [data-contracts.md](./data-contracts.md) | JSON schemas exchanged between BM2 Engines |
| [database-schema.md](./database-schema.md) | Relational + time-series schema for BM2 persistence |

## Key Concepts

- **TransformerEngine**: unit conversion + geo projection + time + data quality (`transformer.py`)
- **Core Models**: `Athlete`, `Bike`, `Activity`, `WorldObject`, `AnalysisContext` (`models.py`)
- **Algorithms**: Movement, Energy, Performance, Fatigue, Recovery, Nutrition, Power, TrainingLoad, RouteDifficulty (`algorithms/`)
- **Knowledge Layer**: `KnowledgeEngine` → `Insight` (numbers → concepts) (`knowledge.py`)
- **Simulation**: `SimulationEngine` + `ScenarioOverride` for what-if queries (`simulation.py`)
- **Orchestrator**: `AIOrchestrator` — routes questions to models, assembles context (`orchestrator.py`)
- **Agents**: `GPSAgent`, `AthleteAgent`, `EnvironmentAgent`, `SensorAgent`, `StravaAgent`, `GarminAgent` (`agents.py`)

## API

BM2 is exposed under `/api/v1/bm2`:
- `POST /api/v1/bm2/ask` — ask a question to the AI Coach
- `POST /api/v1/bm2/simulate` — run a simulation
- `POST /api/v1/bm2/simulate-ride` — simulate a real ride
- `POST /api/v1/bm2/validate` — validate inputs
