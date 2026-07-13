# BikeMaster — Developer Documentation

**Stack:** Python 3.11 · FastAPI · Vue 3 · TypeScript · SQLite/PostgreSQL · Clean Architecture

---

## Overview

**BikeMaster** is a GPS-based cycling performance intelligence system. It allows cyclists of all levels to import routes from GPX/FIT or external services (Strava, Garmin, Wahoo, Google Fit), analyze performance metrics, estimate calories, receive personalized advice from an AI Coach, and visualize routes on interactive maps. The system also includes a **BikeMaster 2.0** Deluxe Simulation Engine (`bike_analyzer/bm2/`) for what-if scenario modeling.

---

## Documents

### 📖 Riferimento Completo (`reference/`)
Riferimento tecnico esaustivo generato dal codice sorgente — **il punto di partenza consigliato**.

| Document | Description |
|---|---|
| [reference/README.md](./reference/README.md) | Indice del riferimento completo |
| [reference/architecture.md](./reference/architecture.md) | Panoramica sistema: layer, flusso richieste, mappa moduli |
| [reference/api-reference.md](./reference/api-reference.md) | Tutti i 138 endpoint REST (metodo, path, auth) |
| [reference/database-schema.md](./reference/database-schema.md) | Schema DB completo: tabelle, indici, migrazioni Alembic |
| [reference/domain-models.md](./reference/domain-models.md) | Entità di dominio + modelli BM2 campo per campo |
| [reference/configuration.md](./reference/configuration.md) | Tutte le variabili d'ambiente / settings |
| [reference/engines-and-analytics.md](./reference/engines-and-analytics.md) | Engine BM2 (9 algoritmi) + motore analytics |
| [reference/frontend.md](./reference/frontend.md) | SPA Vue 3: route, store, componenti, mobile/PWA |

### Core
| Document | Description |
|---|---|
| [MASTER.md](./MASTER.md) | Complete project reference: stack, architecture, data models, API, analytics, AI Coach |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Clean v2 Architecture — UnifiedMetricsEngine, FusionRecord, domain layers |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Setup, build, test, lint, contribute |

### Detailed References
| Document | Description |
|---|---|
| [backend.md](./backend.md) | Backend modules, integrations, security, monitoring, phone tracking, traffic safety |
| [frontend.md](./frontend.md) | Vue 3 app, components, stores, mobile (Android/iOS Capacitor) |
| [testing.md](./testing.md) | Backend (pytest) and frontend (Vitest + Playwright) test strategy |
| [deployment.md](./deployment.md) | Docker, Render, Fly.io, Railway, Kubernetes |
| [configuration.md](./configuration.md) | Environment variables, secrets, API keys |
| [API_DOCS.md](./API_DOCS.md) | REST API reference with all endpoints |

### Roadmaps
| Document | Description |
|---|---|
| [ROADMAP.md](../ROADMAP.md) | Main project roadmap (root level) |
| [DELUXE_ROADMAP.md](./DELUXE_ROADMAP.md) | BikeMaster 2.0 / Deluxe Simulation Engine roadmap |

### BikeMaster 2.0 (BM2)
| Document | Description |
|---|---|
| [bm2/](./bm2/) | BM2 documentation index |
| [bm2/data-contracts.md](./bm2/data-contracts.md) | JSON schemas between BM2 Engines |
| [bm2/database-schema.md](./bm2/database-schema.md) | Relational + time-series schema |
| [bm2/variables.md](./bm2/variables.md) | Variable dictionary (domains, units, gaps) |
| [BM2_ENGINE_ARCHITECTURE.md](./BM2_ENGINE_ARCHITECTURE.md) | Engine pipeline, dependencies, and communication patterns |
| [BM2_ALGORITHMS.md](./BM2_ALGORITHMS.md) | Algorithm specification (Movement, Energy, Fatigue, Power, etc.) |
| [BM2_INTEGRATION_GUIDE.md](./BM2_INTEGRATION_GUIDE.md) | How to integrate BM2 with existing FastAPI routes and frontend |
| [BM2_TESTING_STRATEGY.md](./BM2_TESTING_STRATEGY.md) | Test patterns, coverage targets, and CI integration |

### Guides
| Document | Description |
|---|---|
| [PHONE_TRACKING.md](./PHONE_TRACKING.md) | Phone GPS tracking architecture |
| [PHONE_TRACKING_TESTING.md](./PHONE_TRACKING_TESTING.md) | Phone tracking tests |
| [PRIVACY_POLICY_STORE.md](./PRIVACY_POLICY_STORE.md) | Privacy policy |
| [REFACTOR_PLAN.md](./REFACTOR_PLAN.md) | Refactor plan |
| [stack-tecnologico.md](./stack-tecnologico.md) | Tech stack (IT) |
| [database-migration.md](./database-migration.md) | Database migration guide |
| [USER_GUIDE.md](./USER_GUIDE.md) | User guide |
| [API_EXAMPLES.http](./API_EXAMPLES.http) | API request examples (HTTP file) |

### Agent Instructions
| Document | Description |
|---|---|
| [agent/README.md](./agent/README.md) | AI agent instructions (progressive disclosure) |

---

## Quick Links
- **Repo root:** `D:\BikeMaster`
- **Backend package:** `bike_analyzer/`
- **Frontend app:** `frontend/`
- **Tests:** `tests/` (backend), `frontend/src/**/*.test.ts` (frontend)
- **Deploy configs:** `docker/`, `render.yaml`, `docker/deploy/`
