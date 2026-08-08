# Code Graph — Grafo delle Dipendenze

Grafo che rappresenta il codice del progetto: file, moduli, classi, funzioni,
variabili, API, database, test, componenti e le loro relazioni (§24).

Il **LIBRARIAN** mantiene questo grafo; l'agente **ARCHITECT** lo utilizza
per l'analisi d'impatto.

## Entità (§24)

- FILE
- MODULE
- CLASS
- FUNCTION
- VARIABLE
- API (endpoint HTTP)
- DATABASE (tabella/scheletro)
- TEST
- COMPONENT (Vue)

## Relazioni (§24)

| Relazione | Descrizione |
|---|---|
| CALLS | FUNCTION → FUNCTION |
| IMPORTS | MODULE → MODULE / FILE → FILE |
| USES | COMPONENT → FUNCTION / CLASS → VARIABLE |
| RETURNS | FUNCTION → VARIABLE/COMPONENT |
| READS | FUNCTION/COMPONENT → VARIABLE/DATABASE |
| WRITES | FUNCTION → DATABASE/VARIABLE |
| TESTS | TEST → FUNCTION/CLASS |
| DEPENDS_ON | FILE → MODULE, COMPONENT → STORE |
| EXPOSES | API → FUNCTION, MODULE → API |
| CONSUMES | FRONTEND → API, SERVICE → API |

## Perimetro BikeMaster (mappatura iniziale)

```
main.py                        → entrypoint FastAPI
api/                           → router HTTP
  rides.py                     → API rides (EXPOSES)
  auth.py                      → API auth (EXPOSES)
  stats.py                     → API stats (EXPOSES)
  maps.py                      → API mappe (EXPOSES)
bike_analyzer/                 → core domain
  backend/                     → api, db, analytics, ingestion, sync, auth, maps
  core/                        → models, engine, pipeline, calculators, physics
  bm2/                         → simulation, algorithms, agents, transformer
db/                            → database layer
  models.py                    → modelli Python
  database.py                  → SQLite ↔ PostgreSQL routing
  postgres_athlete.py          → instradamento atleta su PostgreSQL
frontend/                      → Vue 3 app
  src/
    stores/                    → Pinia (auth.ts, rides.ts, athlete.ts, ui.ts, ...)
    composables/               → useRides, useI18n, useToast, useChart, usePWA
    components/                → componenti Vue
    views/                     → pagine/route
    router/index.ts            → Vue Router 4 (beforeEach auth)
    utils/api.ts               → API client (apiGet/Post/Put/Delete/Upload)
    sw.js                      → service worker (PWA caching)
tests/                         → backend pytest
frontend/tests/                → frontend vitest + playwright E2E
aethermap/                     → cartografia (R&D)
aethermap/ai/                  → pipeline IA
docs/                          → documentazione
```

## Domande il grafo risolve (§24)

- "Chi chiama questa funzione?"
- "Quante componenti sono influenzate da questa modifica?"
- "Quali test coprono questa funzione?"
- "Quale API espone questo servizio?"

(questo file è un punto di partenza; il LIBRARIAN lo arricchisce con il
disegno effettivo delle dipendenze man mano che esplora il codice)
