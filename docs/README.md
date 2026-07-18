# BikeMaster — Developer Documentation

**Stack:** Python 3.11 · FastAPI · Vue 3 · TypeScript · SQLite · Tauri 2 · Clean Architecture

---

## Indice

1. [Overview](#overview)
2. [Riferimento tecnico](#riferimento-tecnico-docsreference)
3. [Architettura e visione](#architettura-e-visione)
4. [BikeMaster 2.0 (BM2)](#bikemaster-20-bm2)
5. [AetherMap (R&D)](#aethermap-rd)
6. [Sviluppo](#sviluppo)
7. [Testing](#testing)
8. [Deploy e configurazione](#deploy-e-configurazione)
9. [Guide](#guide)
10. [Agent Instructions](#agent-instructions)

---

## Overview

**BikeMaster** è un sistema di *intelligenza dello stile di vita*: definisce lo stato di salute come il bilanciamento dinamico delle variabili acquisite dalla vita reale di ogni persona, e usa l'attività ciclistica come dominio strutturato per analisi, raccomandazioni e ottimizzazione.

> **Mission ufficiale:** il nostro programma definisce lo stato di salute come il bilanciamento delle variabili acquisite dal tuo stile di vita. Tu scegli cosa mangiare, lui analizza, ti consiglia la quantità compatibile, ti propone micro-correzioni e ti dà la quantità giusta di movimento per mantenere l'equilibrio. Siamo simili come biologia, ma diversi come vita — e il sistema rispetta entrambe le cose.

Importa tracciati da GPX/FIT o servizi esterni (Strava, Garmin, Wahoo, Google Fit), analizza metriche, stima calorie, calcola fatigue score, confronta con benchmark, fornisce un **AI Coach** (Groq + RAG) e visualizza percorsi su mappe interattive.

Architettura: **local-first, desktop-first (Tauri 2)** con backend FastAPI embedded, frontend Vue 3 SPA, SQLite come database primario. Include **BikeMaster 2.0 (BM2)** come motore di simulazione what-if e **AetherMap** come progetto R&D cartografico separato.

---

## Riferimento tecnico (`docs/reference/`)

Riferimento esaustivo generato dal codice sorgente — **punto di partenza consigliato**.

| Documento | Contenuto |
|---|---|
| [`docs/reference/README.md`](reference/README.md) | Indice del riferimento completo |
| [`docs/reference/architecture.md`](reference/architecture.md) | Architettura di sistema: layer, flusso richieste, mappa moduli |
| [`docs/reference/api-reference.md`](reference/api-reference.md) | Tutti gli endpoint REST (metodo, path, auth) |
| [`docs/reference/database-schema.md`](reference/database-schema.md) | Schema DB completo: tabelle, indici, migrazioni |
| [`docs/reference/domain-models.md`](reference/domain-models.md) | Entità di dominio + modelli BM2 campo per campo |
| [`docs/reference/configuration.md`](reference/configuration.md) | Tutte le variabili d'ambiente / settings |
| [`docs/reference/engines-and-analytics.md`](reference/engines-and-analytics.md) | Engine BM2 (9 algoritmi) + motore analytics |
| [`docs/reference/frontend.md`](reference/frontend.md) | SPA Vue 3: route, store, componenti, mobile/PWA |

---

## Architettura e visione

| Documento | Contenuto |
|---|---|
| [`docs/MASTER.md`](MASTER.md) | Documento di riferimento completo: stack, architettura, modelli, API, analytics, AI Coach |
| [`docs/UNIFIED_DOCUMENTATION.md`](UNIFIED_DOCUMENTATION.md) | Sintesi unificante della documentazione (visione, logica di calcolo, BM2, AetherMap) |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | Clean v2 Architecture — UnifiedMetricsEngine, FusionRecord, domain layers |
| [`docs/DEVELOPMENT.md`](DEVELOPMENT.md) | Setup, build, test, lint, come contribuire |
| [`docs/PRODUCT_LOGIC.md`](PRODUCT_LOGIC.md) | Visione prodotto, quattro pilastri, logica centrale, athlete state |
| [`docs/BM2_ENGINE_ARCHITECTURE.md`](BM2_ENGINE_ARCHITECTURE.md) | Specifica Engine BM2: pipeline, dipendenze, contratti |
| [`docs/BM2_ALGORITHMS.md`](BM2_ALGORITHMS.md) | Formule delle variabili derivate (potenza, TRIMP, CTL/ATL, difficoltà percorso) |
| [`docs/BM2_INTEGRATION_GUIDE.md`](BM2_INTEGRATION_GUIDE.md) | Come integrare BM2 con FastAPI e frontend |
| [`docs/BM2_TESTING_STRATEGY.md`](BM2_TESTING_STRATEGY.md) | Strategia di test BM2 |

---

## BikeMaster 2.0 (BM2)

| Documento | Contenuto |
|---|---|
| [`docs/bm2/README.md`](bm2/README.md) | Indice cartella BM2 |
| [`docs/bm2/data-contracts.md`](bm2/data-contracts.md) | Contratti JSON scambiati tra Engine |
| [`docs/bm2/database-schema.md`](bm2/database-schema.md) | Schema relazionale + time-series per BM2 |
| [`docs/bm2/variables.md`](bm2/variables.md) | Dizionario variabili BM2 (domini, unità, gap vs codice) |
| [`docs/DELUXE_ROADMAP.md`](DELUXE_ROADMAP.md) | Roadmap BikeMaster 2.0 / Deluxe Simulation Engine |

---

## AetherMap (R&D)

Progetto cartografico indipendente (`aethermap/`) — motore "dal nulla" con cube-sphere, S2/H3, data model "database del mondo", pipeline IA "ricercatore", rendering WebGL, digital twin. Condivide lo stack (Vue + FastAPI) ma non è importato dal backend BikeMaster.

| Documento | Contenuto |
|---|---|
| [`aethermap/README.md`](../aethermap/README.md) | Panoramica progetto AetherMap |
| [`docs/agent/aethermap.md`](agent/aethermap.md) | Istruzioni agent per AetherMap |

---

## Sviluppo

| Documento | Contenuto |
|---|---|
| [`docs/backend.md`](backend.md) | Moduli backend, integrazioni, sicurezza, monitoring, phone tracking |
| [`docs/frontend.md`](frontend.md) | Vue 3 app, componenti, store, mobile (Android/iOS Capacitor, Tauri) |
| [`docs/stack-tecnologico.md`](stack-tecnologico.md) | Stack tecnologico dettagliato (IT) |
| [`docs/local-data-storage.md`](local-data-storage.md) | Dove e come i dati sono salvati sui dispositivi (offline-first) |
| [`docs/database-migration.md`](database-migration.md) | Guida alle migrazioni database (Alembic) |

---

## Testing

| Documento | Contenuto |
|---|---|
| [`docs/testing.md`](testing.md) | Strategia di test: backend (pytest) e frontend (Vitest + Playwright) |
| [`docs/PHONE_TRACKING_TESTING.md`](PHONE_TRACKING_TESTING.md) | Test per phone GPS tracking |

---

## Deploy e configurazione

| Documento | Contenuto |
|---|---|
| [`docs/deployment.md`](deployment.md) | Docker, Render, Fly.io, Railway, Kubernetes |
| [`docs/deployment-plan.md`](deployment-plan.md) | Piano di deployment completo: architettura, sync, sicurezza, integrazioni |
| [`docs/configuration.md`](configuration.md) | Variabili d'ambiente, secrets, API keys |
| [`docs/API_DOCS.md`](API_DOCS.md) | Riferimento API REST con tutti gli endpoint |
| [`docs/API_EXAMPLES.http`](API_EXAMPLES.http) | Esempi di richieste API (HTTP file) |

---

## Guide

| Documento | Contenuto |
|---|---|
| [`docs/USER_GUIDE.md`](USER_GUIDE.md) | Guida utente |
| [`docs/PHONE_TRACKING.md`](PHONE_TRACKING.md) | Architettura phone GPS tracking |
| [`docs/PRIVACY_POLICY_STORE.md`](PRIVACY_POLICY_STORE.md) | Privacy policy |
| [`docs/REFACTOR_PLAN.md`](REFACTOR_PLAN.md) | Piano di refactoring |
| [`ROADMAP.md`](../ROADMAP.md) | Roadmap consolidata del progetto |
| [`PROJECT_STATUS.md`](../PROJECT_STATUS.md) | Stato attuale del progetto |

---

## Guide e test

| Documento | Contenuto |
| --- | --- |
| [`docs/tests/road-tests.md`](tests/road-tests.md) | Test su strada e casi d'uso di validazione |

---

## Agent Instructions

Istruzioni specifiche per AI agent (progressive disclosure). Indice completo in [`docs/agent/README.md`](agent/README.md).

| Documento | Contenuto |
| --- | --- |
| [`docs/agent/README.md`](agent/README.md) | Indice delle istruzioni per AI agent |
| [`docs/agent/commands.md`](agent/commands.md) | Comandi frontend, backend e test |
| [`docs/agent/stack.md`](agent/stack.md) | Stack tecnologico completo |
| [`docs/agent/structure.md`](agent/structure.md) | Layout del repository e mappa dei moduli |
| [`docs/agent/auth.md`](agent/auth.md) | Auth, OAuth, JWT, gestione sessioni |
| [`docs/agent/build.md`](agent/build.md) | Note di build (mitigazione EPERM su Windows) |
| [`docs/agent/bm2.md`](agent/bm2.md) | Specifiche del motore BikeMaster 2.0 |
| [`docs/agent/aethermap.md`](agent/aethermap.md) | Confini del progetto AetherMap |
| [`docs/agent/monitoring.md`](agent/monitoring.md) | Rate limiting, Redis, health checks |
| [`docs/agent/notes.md`](agent/notes.md) | Note generali e gotcha per agent |
