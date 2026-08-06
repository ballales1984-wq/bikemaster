# BikeMaster

[![License: All Rights Reserved](https://img.shields.io/badge/License-All%20Rights%20Reserved-red.svg)](LICENSE)
[![Tauri 2 Desktop](https://img.shields.io/badge/Platform-Tauri%202%20Desktop-blue.svg)](https://tauri.app)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/Vue-3.4%2B-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-black.svg)](https://fastapi.tiangolo.com/)

**BikeMaster** è un sistema di *intelligenza dello stile di vita*: definisce lo stato di salute come il bilanciamento dinamico delle variabili acquisite dalla vita reale di ogni persona, e usa l'attività ciclistica come dominio strutturato per analisi, raccomandazioni e ottimizzazione.

> **Mission ufficiale:** il nostro programma definisce lo stato di salute come il bilanciamento delle variabili acquisite dal tuo stile di vita. Tu scegli cosa mangiare, lui analizza, ti consiglia la quantità compatibile, ti propone micro-correzioni e ti dà la quantità giusta di movimento per mantenere l'equilibrio. Siamo simili come biologia, ma diversi come vita — e il sistema rispetta entrambe le cose.

> **Piattaforma primaria:** desktop **Tauri 2** (`.exe`/`.dmg`/`.AppImage`) con backend embedded e database locale SQLite. PWA supportata per utenti web-only. Deploy cloud opzionale per sync/community.

## Indice

- [Visione](#visione)
- [Architettura](#architettura)
- [Documentazione](#documentazione)
- [Quick Start](#quick-start)
- [BikeMaster 2.0 — Simulation Engine](#bikemaster-20--simulation-engine)
- [Roadmap](#roadmap)
- [Come contribuire](#come-contribuire)
- [Licenza](#licenza)

## Visione

### Missione ufficiale

Il nostro programma definisce lo stato di salute come il bilanciamento delle variabili acquisite dal tuo stile di vita.

```
STATO DI SALUTE = EQUILIBRIO DINAMICO DELLE VAR
```

Tu scegli cosa mangiare, il sistema analizza, ti consiglia la quantità compatibile, ti propone micro-correzioni e ti dà la quantità giusta di movimento per mantenere l'equilibrio. Siamo simili come biologia, ma diversi come vita — e il sistema rispetta entrambe le cose.

### Le VAR — la firma metabolica di ogni persona

Il programma considera lo stato generale di salute come l'equilibrio dinamico di tutte le variabili che raccoglie:

| VAR | Descrizione |
|---|---|
| **Energia** | Livello energetico disponibile |
| **Macronutrienti** | Bilanciamento proteine/carboidrati/grassi |
| **Acqua_totale** | Idratazione giornaliera |
| **Glicemia** | Controllo glicemico |
| **VO2** | Capacità cardio-respiratoria |
| **Respirazione** | Efficienza respiratoria |
| **Battito** | Frequenza cardiaca a riposo e sotto sforzo |
| **Orario** | Ritmi circadiani e tempistiche |
| **Storico** | Andamento nel tempo |
| **Stato_generale** | Percezione soggettiva del benessere |

Queste VAR sono la **firma metabolica** di ogni persona.

### Origine delle VAR — la vita reale

Il sistema non inventa nulla: prende le variabili direttamente dal tuo stile di vita:

- **Stile_di_vita** — sedentarietà, attività spontanea, routine
- **Orari_di_lavoro** — turni, flessibilità, carico lavorativo
- **Famiglia** — responsabilità, supporto sociale, conflitti
- **Stress** — pressione psicologica, eventi stressanti
- **Vizi** — fumo, alcol, sostanze
- **Abitudini** — routine consolidate, scelte automatiche
- **Sonno** — durata, qualità, continuità
- **Attività_fisica** — esercizio strutturato (ciclismo incluso) e movimento spontaneo

Perché siamo simili come biologia, ma diversi come vita.

### Ciclo operativo del sistema

Ogni giorno il sistema:

1. **Analizza** ciò che scegli di mangiare → *Analisi_cibo*
2. **Consiglia** la quantità compatibile → *Quantita_compatibile*
3. **Propone** micro-correzioni intelligenti → *Correzione_micro*
4. **Calcola** la quantità giusta di movimento → *Allenamento_dinamico*
5. **Bilancia** le VAR per riportarti in equilibrio → *Equilibrio_metabolico*

### Feedback e misurazioni dirette

Il sistema diventa personale grazie a:

- **Feedback_personale** — percezioni, sensazioni, preferenze
- **Misurazioni_dirette** — sensori, dispositivi, laboratori

Così capisce: come reagisci, come ti senti, come varia la tua energia, come cambia il tuo stato generale. E adatta tutto.

### Principio guida

I dati grezzi non hanno valore finché non vengono trasformati in conoscenza utilizzabile.

```
DATI GREZZI → MODELLI MATEMATICI → STATI INTERPRETATI → KNOWLEDGE BASE → AI COACH → DECISIONI
```

L'obiettivo non è accumulare dati, ma costruire un modello completo di persona + territorio + ambiente. L'AI Coach riceve solo concetti già interpretati, mai numeri grezzi.

**Posizionamento:** non compete con app dedicate (Strava/Garmin/TrainingPeaks per il ciclismo, MyFitnessPal per la nutrizione, Oura/Whoop per il sonno). È uno **strato di intelligenza sopra tutti gli strumenti che la persona già usa**, integrato in un'unica visione olistica dello stato di salute.

## Architettura

**Local-first, desktop-first (Tauri 2).** Il device è la sorgente di verità. L'architettura prevede due moduli backend:
- **Modulo locale** (default): FastAPI embedded + SQLite, gira su `localhost` nel device.
- **Modulo hub** (opzionale): FastAPI + PostgreSQL multi-tenant, per sync e community.

L'utente può attivare la modalità **"Mai"** (mai sync) e usare l'app 100% offline.

### Platform

| Livello | Tecnologia |
|---|---|
| Desktop | Tauri 2 (Rust + WebView) — distribuzione primaria |
| Frontend | Vue 3 + Vite + TypeScript — bundle inside Tauri WebView |
| Backend | FastAPI (Python) embedded — `localhost` nel device |
| Database | SQLite (primario, locale) + PostgreSQL (opzionale, cloud hub) |
| Mobile | Android (Capacitor + Kotlin) · iOS (Capacitor, in valutazione) |
| Web | PWA per utenti browser-only |

### Engine BM2 (7 pipeline specializzate)

| Engine | Responsabilità |
|---|---|
| **Import Engine** | GPX/FIT/Strava/Garmin/Wahoo |
| **Tracking Engine** | Sessioni live GPS + sensori |
| **Measurement Engine** | Conversioni e grandezze derivate |
| **Analysis Engine** | Metriche di sessione e atleta |
| **Territory Engine** | Modello territorio e difficoltà percorso |
| **Knowledge Layer** | Stati interpretati (FitnessState, FatigueState, RecoveryState...) |
| **AI Coach** | Consigli basati solo sul Knowledge Layer |

### Infrastruttura trasversale

| Modulo | Ruolo |
|---|---|
| **Data Layer** | Storage canonico atleti, sessioni, bici, telemetria |
| **Time Engine** | Timeline unificata e sincronizzazione eventi |

## Documentazione

### Indice centrale

Per una guida completa a tutti i documenti, vedi [`docs/README.md`](docs/README.md).

### Riferimento tecnico (`docs/reference/`)

| Documento | Contenuto |
|---|---|
| [`docs/reference/README.md`](docs/reference/README.md) | Indice del riferimento completo |
| [`docs/reference/architecture.md`](docs/reference/architecture.md) | Architettura di sistema: layer, flusso, moduli |
| [`docs/reference/api-reference.md`](docs/reference/api-reference.md) | Tutti gli endpoint REST |
| [`docs/reference/database-schema.md`](docs/reference/database-schema.md) | Schema DB completo |
| [`docs/reference/domain-models.md`](docs/reference/domain-models.md) | Entità di dominio + modelli BM2 |
| [`docs/reference/configuration.md`](docs/reference/configuration.md) | Variabili d'ambiente / settings |
| [`docs/reference/engines-and-analytics.md`](docs/reference/engines-and-analytics.md) | Engine BM2 + motore analytics |
| [`docs/reference/frontend.md`](docs/reference/frontend.md) | SPA Vue 3: route, store, componenti |

### Architettura e visione

| Documento | Contenuto |
|---|---|
| [`docs/MASTER.md`](docs/MASTER.md) | Documento di riferimento completo del progetto |
| [`docs/MASTER.md`](docs/MASTER.md) | Documento di riferimento completo del progetto |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architettura madre (Clean v2, UnifiedMetricsEngine) |
| [`docs/BM2_ENGINE_ARCHITECTURE.md`](docs/BM2_ENGINE_ARCHITECTURE.md) | Specifica Engine BM2: pipeline, dipendenze, contratti |
| [`docs/BM2_ALGORITHMS.md`](docs/BM2_ALGORITHMS.md) | Formule delle variabili derivate |
| [`docs/PRODUCT_LOGIC.md`](docs/PRODUCT_LOGIC.md) | Visione prodotto, quattro pilastri, logica centrale |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | Setup, build, test, lint, come contribuire |

### AetherMap (terrain intelligence module)

Progetto cartografico R&D fuso in BikeMaster come modulo terrain intelligence opzionale (`aethermap/`). Fornisce digital twin + AI pipeline per arricchimento coordinate terrain delle ride. Condivide lo stack (Vue + FastAPI) ed è integrato tramite adapter con feature flag `BIKEMASTER_MAP_PROVIDER=aethermap` / `VITE_AETHERMAP_ENABLED=true`.

| Documento | Contenuto |
|---|---|
| [`aethermap/README.md`](aethermap/README.md) | Panoramica progetto AetherMap |
| [`docs/agent/aethermap.md`](docs/agent/aethermap.md) | Istruzioni agent per AetherMap |

### Modulo hub (cloud sync & community)

Backend cloud opzionale per sync bidirezionale, multi-tenant e knowledge base condivisa.

| Documento | Contenuto |
|---|---|
| [`docs/hub.md`](docs/hub.md) | Modulo hub: architettura, avvio, endpoint, sync |

**Ordine di lettura consigliato:** [README centrale](docs/README.md) → architettura generale → [MASTER.md](docs/MASTER.md) → schema database → contratti dati → API → algoritmi.

## Quick Start

### Prerequisiti

- Python 3.11+
- Node.js 18+ (per il frontend)
- Rust/Cargo (per Tauri desktop, opzionale)

### Backend (API locale)

```bash
git clone https://github.com/ballales1984-wq/bikemaster.git
cd bikemaster
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
python main.py api             # API + dashboard su http://localhost:8000
```

### Frontend (Vite dev server)

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

### Desktop (Tauri 2)

```bash
cd frontend
npm run tauri dev              # App desktop con backend embedded
```

### Docker

```bash
docker compose up -d
```

Per la configurazione delle variabili d'ambiente copia `.env.example` in `.env`.

## BikeMaster 2.0 — Simulation Engine

BM2 è l'**engine di simulazione sportiva** interno: fornisce analisi what-if, algoritmi type-safe con analisi dimensionale (`Quantity` + `UnitRegistry`) e un Knowledge Layer per insight guidati dall'AI.

- **7 engine specializzati**: Import, Tracking, Measurement, Analysis, Territory, Knowledge Layer, AI Coach
- **9 algoritmi**: Movement, Energy, Performance, Fatigue, RouteDifficulty, Recovery, Nutrition, Power, TrainingLoad
- **Kernel fisico condiviso**: `bike_analyzer/core/physics/`
- **Algoritmi puri**: ogni algoritmo restituisce `ModelResult` con formula, input, precisione e confidence

```bash
# Test BM2
pytest tests/test_bm2_*.py -v

# Demo simulazione
cd bike_analyzer && python -m bm2.simulation.demo
```

## Roadmap

**Stato:** architettura locale-first (Tauri 2 + SQLite primario + backend FastAPI embedded) completata; engine BM2 e AetherMap attivi. Build backend e frontend con test automatizzati (vedi [`ROADMAP.md`](ROADMAP.md) e [`PROJECT_STATUS.md`](PROJECT_STATUS.md) per i numeri aggiornati).

### Completato

- [x] Architettura locale-first Tauri 2 + SQLite primario
- [x] 7 Engine BM2 + 9 algoritmi
- [x] AI Coach (Groq + RAG)
- [x] Import Strava/Garmin/Wahoo/Google Fit
- [x] Phone GPS Tracking (Android + iOS)
- [x] Traffic Safety Analysis
- [x] Multi-tenant + data isolation
- [x] AetherMap (fasi 1-5 complete, convergence into BikeMaster)

### In corso

- [ ] Anomaly detection + piano di allenamento LLM
- [ ] Voice Coach (TTS/audio)

Vedi [`ROADMAP.md`](ROADMAP.md) per il dettaglio completo.

## Come contribuire

1. Fai un fork del repository
2. Crea un branch di feature (`git checkout -b feature/nome-feature`)
3. Commit delle modifiche (`git commit -m 'feat: aggiunge nome-feature'`)
4. Push del branch (`git push origin feature/nome-feature`)
5. Apri una Pull Request

Prima di proporre modifiche architetturali, verificare che rispettino i confini di responsabilità definiti in [`docs/BM2_ENGINE_ARCHITECTURE.md`](docs/BM2_ENGINE_ARCHITECTURE.md). Assicurarsi che tutti i test passino prima di inviare una PR.

## Licenza

All Rights Reserved — vedi il file [LICENSE](LICENSE) per i dettagli.
