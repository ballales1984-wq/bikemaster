# BikeMaster 2.0

[![License: Proprietary](https://img.shields.io/badge/License-All%20Rights%20Reserved-red.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/Vue-3.4%2B-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-black.svg)](https://fastapi.tiangolo.com/)

Digital Twin dell'atleta e dell'ambiente per il ciclismo: raccoglie dati da GPS, sensori e servizi esterni, li trasforma in conoscenza (forma, fatica, recupero, difficoltà percorso) e li mette al servizio di un AI Coach.

> **Stato del progetto:** *Production Ready*. Il sistema è implementato e in esecuzione (backend FastAPI, frontend Vue 3 + PWA, app Android, suite di test ~106 file / 1546+ test, deploy su Render). Il documento di visione e architettura Engine descritto qui sotto è la base concettuale su cui il codice è costruito; la sezione [BikeMaster 2.0 — Deluxe Simulation](#bikemaster-20--deluxe-simulation-engine) descrive lo stato dell'engine di simulazione.

---

## Visione

Il principio guida del sistema è che i dati grezzi non hanno valore finché non vengono trasformati in conoscenza utilizzabile:

```
DATI GREZZI
     ↓
MODELLI MATEMATICI
     ↓
STATI INTERPRETATI
     ↓
KNOWLEDGE BASE
     ↓
AI COACH
     ↓
DECISIONI
```

L'obiettivo non è accumulare quanti più dati possibile, ma raccogliere solo quelli necessari a costruire un modello completo di atleta + territorio + ambiente, ed evitare di mandare dati grezzi direttamente a un modello di AI.

---

## Architettura — panoramica moduli (Engine)

| Engine | Responsabilità |
|---|---|
| **Import Engine** | Importa dati da fonti esterne (Strava, GPX, FIT, Garmin, Wahoo, altri dispositivi) |
| **Data Layer** | Storage canonico di atleti, sessioni, bici, telemetria |
| **Time Engine** | Timeline unificata e sincronizzazione eventi |
| **Tracking Engine** | Registrazione sessioni live (GPS + sensori in tempo reale) |
| **Measurement Engine** | Conversioni e grandezze derivate (velocità, pendenza, energia) — lo "standard interno" a cui tutti i sensori si adattano |
| **Analysis Engine** | Metriche di sessione e di atleta, trend, zone, TRIMP/TSS |
| **Territory Engine** | Modello del territorio: strade, pendenze, difficoltà segmento, sicurezza |
| **Knowledge Layer** | Stati interpretati: `FitnessState`, `FatigueState`, `RecoveryState`, `RouteDifficulty`, `PerformancePrediction` |
| **AI Coach** | Spiegazioni, consigli, interazione con l'utente — legge solo dal Knowledge Layer, mai dati grezzi |

Ogni Engine ha confini precisi (cosa riceve, cosa produce, cosa può leggere, cosa **non deve** conoscere): il dettaglio è nei documenti di architettura.

---

## Documentazione

### Riferimento completo (`docs/reference/`)

Riferimento tecnico esaustivo generato dal codice sorgente — **il punto di partenza consigliato**.

| Documento | Contenuto |
|---|---|
| [`docs/reference/README.md`](docs/reference/README.md) | Indice del riferimento completo |
| [`docs/reference/architecture.md`](docs/reference/architecture.md) | Architettura di sistema: layer, flusso richieste, mappa moduli |
| [`docs/reference/api-reference.md`](docs/reference/api-reference.md) | Tutti i 138 endpoint REST (metodo, path, auth) |
| [`docs/reference/database-schema.md`](docs/reference/database-schema.md) | Schema DB completo: tabelle, indici, migrazioni Alembic |
| [`docs/reference/domain-models.md`](docs/reference/domain-models.md) | Entità di dominio + modelli BM2 campo per campo |
| [`docs/reference/configuration.md`](docs/reference/configuration.md) | Tutte le variabili d'ambiente / settings |
| [`docs/reference/engines-and-analytics.md`](docs/reference/engines-and-analytics.md) | Engine BM2 (9 algoritmi) + motore analytics |
| [`docs/reference/frontend.md`](docs/reference/frontend.md) | SPA Vue 3: route, store, componenti, mobile/PWA |

### Visione e architettura

| Documento | Contenuto |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Visione, principi e architettura generale del sistema |
| [`docs/BM2_ENGINE_ARCHITECTURE.md`](docs/BM2_ENGINE_ARCHITECTURE.md) | Specifica di ogni Engine: pipeline, dipendenze, pattern di comunicazione |
| [`docs/BM2_ALGORITHMS.md`](docs/BM2_ALGORITHMS.md) | Formule delle variabili derivate (potenza stimata, TRIMP, CTL/ATL, difficoltà percorso, ecc.) |
| [`docs/bm2/data-contracts.md`](docs/bm2/data-contracts.md) | Contratti JSON scambiati tra Engine (produttore/consumatore) |
| [`docs/bm2/variables.md`](docs/bm2/variables.md) | Dizionario completo delle variabili BM2 con unità e posizione nel codice |

**Ordine di lettura consigliato:** [indice riferimento](docs/reference/README.md) → architettura generale → architettura Engine → schema database → contratti dati → API → algoritmi.

---

## Principi di progettazione

1. **Separazione delle responsabilità** — ogni Engine fa una cosa sola e non duplica logica altrui.
2. **Standard interno unico** — qualunque sia la fonte del dato (telefono, Garmin, Strava, sensore bici), passa dal Data Normalization Layer prima di essere usato.
3. **Dati grezzi ≠ conoscenza** — l'AI Coach riceve solo concetti già interpretati (`FatigueState`, `RecoveryState`, ecc.), mai numeri grezzi.
4. **Apprendimento personalizzato** — modelli come `RecoveryState` si calibrano nel tempo sullo storico del singolo atleta, non su una formula fissa uguale per tutti.

---

## Quick Start

### Prerequisiti

- Python 3.11+
- Node.js 18+ (per il frontend)

### Backend

```bash
git clone https://github.com/ballales1984-wq/bikemaster.git
cd bikemaster
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
python main.py api             # API + dashboard su http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                    # Vite dev server su http://localhost:5173
```

### Docker

```bash
docker compose up -d
```

Per la configurazione delle variabili d'ambiente copia `.env.example` in `.env`. La documentazione completa di setup, deploy e testing è in [`docs/`](docs/).

---

## BikeMaster 2.0 — Deluxe Simulation Engine

BM2 è l'**engine di simulazione sportiva** interno a BikeMaster: fornisce analisi what-if, algoritmi type-safe con analisi dimensionale (`Quantity` + `UnitRegistry`) e un Knowledge Layer per gli insight guidati dall'AI.

- **7 engine specializzati**: Import, Tracking, Measurement, Analysis, Territory, Knowledge Layer, AI Coach
- **9 algoritmi**: Movement, Energy, Performance, Fatigue, RouteDifficulty, Recovery, Nutrition, Power, TrainingLoad
- **Kernel fisico condiviso**: `bike_analyzer/core/physics/`
- **Algoritmi puri**: ogni algoritmo eredita dalla classe base `Algorithm` e restituisce un `ModelResult` con formula, input usati, precisione e confidence

```bash
# Test BM2
pytest tests/test_bm2_*.py -v
```

---

## Roadmap

- [x] Architettura concettuale e mappa degli Engine
- [x] Vocabolario delle variabili per dominio
- [x] Schema database
- [x] Specifica API
- [x] Documento algoritmi
- [x] Contratti dati tra Engine
- [x] Data Layer + Measurement Engine
- [x] Import Engine (GPX/FIT/Strava/Garmin/Wahoo)
- [x] Tracking Engine (sessioni live + Android)
- [x] Analysis Engine
- [x] Territory Engine (difficoltà + sicurezza percorso)
- [x] Knowledge Layer
- [x] AI Coach (Groq + RAG con PGVector)
- [ ] App mobile iOS (Capacitor iOS)
- [ ] Anomaly detection + piano di allenamento generato da LLM
- [ ] Copertura test > 90%

---

## Come contribuire

1. Fai un fork del repository
2. Crea un branch di feature (`git checkout -b feature/nome-feature`)
3. Commit delle modifiche (`git commit -m 'feat: aggiunge nome-feature'`)
4. Push del branch (`git push origin feature/nome-feature`)
5. Apri una Pull Request

Prima di proporre modifiche architetturali, verificare che rispettino i confini di responsabilità definiti in [`docs/BM2_ENGINE_ARCHITECTURE.md`](docs/BM2_ENGINE_ARCHITECTURE.md). Assicurarsi che tutti i test passino prima di inviare una PR.

---

## Licenza

All Rights Reserved — vedi il file [LICENSE](LICENSE) per i dettagli.
