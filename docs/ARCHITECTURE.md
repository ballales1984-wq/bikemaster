# BikeMaster — Architettura Madre (Super App)

Documento di riferimento del nuovo sistema. Definisce i layer, il modello dominio,
la **nuova logica di calcolo** e i flussi. I pezzi esistenti vengono "incastrati"
negli slot definiti qui, senza riscrittura dove non serve.

**Principi**
1. Ogni cosa è un modulo con dipendenze esplicite (nessun accoppiamento nascosto).
2. Il dominio non dipende da infrastruttura (DB, provider, mappe).
3. La logica di calcolo è **pura** (input → output, testabile), separata dall'I/O.
4. I dati grezzi entrano come `SessionData` e diventano `Activity` + `FusionRecord`.
5. L'AI Coach consuma solo `FusionRecord` (contesto già fuso), mai sorgenti grezze.

---

## 1. Layered Architecture (Clean v2)

```
Presentation      API (FastAPI) · Frontend Vue · Android/iOS (Capacitor)
       │
Application       Use cases: StartSession, PromoteSession, ImportActivity,
                   AnalyzeActivity, SyncHealth, CoachAdvise, PlanTraining
       │
Domain            Entities + UnifiedMetricsEngine (logica di calcolo pura)
       │
Infrastructure    Repositories · Ingestion (Strava/Garmin/Fit/GPX) ·
                   Tracking · Maps · Weather · Traffic · VectorDB

Repository Layer:
  db/repositories/        # SQLite wrappers (athlete, ride) — importati da database.py
  analytics/repositories/ # Domain repositories (19 file) — dual-mode sync/async,
                           # circular import risolti via lazy import per metodo
                           # TrainingGoalRepository → PostgreSQL/SQLAlchemy diretto
```

Dipendenze puntano solo verso l'interno. L'`Application` orchestra; il `Domain`
calcola; l'`Infrastructure` persiste/recupera.

---

## 2. Modello Dominio (nuovo)

Estende `core/models.py` mantenendo retro-compatibilità.

| Entità | Ruolo | Stato vs esistente |
|---|---|---|
| `GPSPoint` | punto grezzo + sensori | ✅ esiste (`core/models.py:28`) |
| `SessionData` | **NUOVO** stream live/background (GPS+sensori+contesto) | da creare |
| `Activity` | superset di `Ride` (tipo, is_official, source) | estende `Ride` (`core/models.py:74`) |
| `HealthSample` | sonno/HRV/passi/resting_hr/peso | **NUOVO** |
| `FusionRecord` | snapshot fuso (salute+meteo+traffico+stato) per AI | **NUOVO** |
| `AthleteProfile` | dati atleta + obiettivi | ✅ esiste (`core/models.py:128`) |
| `Recommendation` | output AI (recupero/nutrizione/allenamento) | **NUOVO** |

`Activity` eredita `tenant_id`+`athlete_id` (regola fissa da `db/models.py`).

---

## 3. Nuova logica di calcolo — `UnifiedMetricsEngine`

Cuore del sistema. Prende `SessionData` (non solo GPS, ma anche HR/power/cadence/
salute/contesto) e produce metriche + aggiorna `FitnessState`.

```
SessionData
   │  (normalizzazione punti, filtri accuratezza GPS >20m)
   ▼
RawMetrics  ──► calculators/*  (riusati: power, fatigue, calories,
   │                                  stress, performance, advanced)
   ▼
ActivityMetrics (TSS, NP, IF, CTL/ATL/TSB, recovery, calorie, score)
   │
   ▼
FitnessState update  (fitness_state.py)
   │
   ▼
FusionRecord  (unisce salute+meteo+traffico+stato) → pronto per AI
```

I `calculators/` esistenti restano gli atomi; il `UnifiedMetricsEngine` è il
nuovo orchestratore che li compone E aggiunge input salute/sensori/context
(oggi assenti nel pipeline `core/pipeline.py`).

---

## 4. Flussi (sequence)

**A. Tracking live → analisi**
`Android/BikeTrackingService` → `trackingStore` (mode live) → `SessionData`
→ stop → `PromoteSession` → `UnifiedMetricsEngine` → persist `Activity`
→ aggiorna `FitnessState` → emetti `FusionRecord` → notifica AI Coach.

**B. Import esterno**
Strava/Garmin/Fit/GPX → `ingestion/*` → normalizza in `SessionData`
→ `AnalyzeActivity` → `Activity` + `FitnessState`.

**C. Sync salute**
Google Fit / Apple Health → `HealthSample` → `FusionRecord` aggiornato.

**D. AI Coach**
`CoachAdvise` → legge `FusionRecord` (+ RAG `knowledge_base`) → `Recommendation`.

---

## 5. Mappa pezzi esistenti → slot

| Pezzo esistente | Slot architettura | Azione |
|---|---|---|
| `core/engine.py`, `pipeline.py`, `fitness_state.py` | Domain · calcolo | riusare, assorbiti da `UnifiedMetricsEngine` |
| `analytics/calculators/*` | Domain · atomi puri | riusare com'è |
| `analytics/services/context_builder.py` | Application · Fusion | estendere → produce `FusionRecord` |
| `analytics/ai_coach.py` + `knowledge_base.py` | Application · Coach | riusare (consuma `FusionRecord`) |
| `auth/*`, `security.py`, `routes.py` | Presentation/Identity | riusare (fondazione fissa) |
| `ingestion/*` (strava/garmin/fit/gpx) | Infrastructure · Ingestion | riusare |
| `BikeTrackingService.kt` + `trackingStore.ts` | Infrastructure/Presentation · Tracking | estendere con `mode`/`promote` |
| `maps/*` (osm_maps) | Infrastructure · Maps | base nativa riusata |
| `weather/*`, `traffic/*` | Infrastructure · Context | riusare come input Fusion |

---

## 6. Prossimi passi concreti
1. Creare `core/session.py` (`SessionData`) + estendere `Ride`→`Activity`.
2. Creare `core/fusion.py` (`HealthSample`, `FusionRecord`).
3. Creare `core/engine_v2.py` (`UnifiedMetricsEngine`) sopra i `calculators`.
4. Estendere `context_builder.py` per emettere `FusionRecord`.
5. Tastare il flusso A end-to-end con un test di integrazione.
