# BikeMaster — Guida per principianti

> Sezione 1: cos'è l'app e a cosa serve.

## 1. Panoramica generale

**BikeMaster** è un'applicazione di *intelligenza dello stile di vita* che usa il ciclismo come punto di partenza per capire e migliorare il benessere generale.

L'idea centrale è:

```
STATO DI SALUTE = EQUILIBRIO DINAMICO DELLE VAR
```

Le **VAR** (Variabili di stato) sono caratteristiche come energia, glicemia, idratazione, VO2, frequenza cardiaca, orari, storia. Il sistema le raccoglie dalla vita reale — dallo stile di vita, dagli sport, dai sensori, dalle app collegate — e cerca di tenerle in equilibrio.

**Cos'è l'applicazione?**

| Aspetto | Tecnologia |
|---|---|
| **Cosa fa** | Registra uscite ciclistiche (GPS, potenza, FC), analizza i dati, dà consigli, gestisce nutrizione, sonno, recupero |
| **Piattaforma principale** | App desktop **Tauri 2** (un file `.exe`/`.dmg`/`AppImage` che gira offline) |
| **Frontend** | Vue 3 + Vite + TypeScript (interfaccia reattiva, installabile anche come PWA su telefono) |
| **Backend** | FastAPI (Python) — gira *embedded* dentro l'app desktop oppure su server |
| **Database** | SQLite (locale, offline) + PostgreSQL (opzionale, per sincronizzare i dati su cloud) |
| **Mobile** | Android (con Capacitor + Kotlin), iOS in valutazione |

### Filosofia: "local-first"

L'app è progettata per **funzionare offline**. Il tuo computer o telefono è la "sorgente di verità" (dove stanno i dati). Puoi scegliere di **non sincronizzare mai** e usare tutto in locale. La sincronizzazione con il cloud (Render + PostgreSQL) è opzionale.

### Architettura a due backend

Ci sono due modi per avviare il backend:

1. **Modulo locale** (`python main.py api`): FastAPI + SQLite, gira sul tuo computer a `localhost:8001`. È il default per sviluppo e per l'app desktop Tauri.
2. **Modulo hub** (`python main.py hub`): FastAPI + PostgreSQL multi-tenant, per la sincronizzazione e la community. Su Render (cloud).

Il backend ha un meccanismo di **dispatch automatico**: quando trova la variabile `DATABASE_URL` (cioè è su Render), le funzioni del database mandano le richieste a PostgreSQL invece che a SQLite.

### Il motore BM2

All'interno c'è il **motore di simulazione BikeMaster 2.0** (`bike_analyzer/bm2/`) con 9 algoritmi (movimento, energia, performance, fatica, difficoltà del percorso, recupero, nutrizione, potenza, carico di allenamento) e 7 pipeline specializzate (import, tracking, misurazione, analisi, territorio, conoscenza, AI Coach).

---

## 2. Schema del flusso principale

Ecco il flusso più semplice, con un esempio concreto.

### ESEMPIO: "Salvo una nuova uscita ciclistica"

```
[1] L'utente clicca "Salva uscita" nel frontend
    ↓
[2] Il frontend (Vue 3) chiama l'API:
    apiPost("/api/v1/rides", { gps_points, distance_km, ... })
    ↓
[3] Il browser invia una richiesta HTTP POST all'URL del backend
    (es. http://localhost:8001/api/v1/rides  oppure  https://bikemaster.onrender.com/api/v1/rides)
    → con header "Authorization: Bearer <JWT>"
    ↓
[4] Il backend FastAPI riceve la richiesta:
    - il middleware estrae il JWT e identifica l'utente
    - il router /rides → funzione create_ride()
    - valida i dati → li "pulisce" (process_route) → calcola calorie/distanza se mancanti
    - salva nel database via save_ride()
    ↓
[5] Il database (SQLite locale o PostgreSQL su cloud) memorizza la ride
    ↓
[6] Il backend risponde con { id: 42, ... }
    ↓
[7] Il frontend aggiorna la sua lista delle uscite (store Pinia) e mostra il risultato
```

### ESEMPIO: "Accedo all'app con Google"

```
[1] Utente clicca "Accedi con Google"
    ↓
[2] Frontend chiama GET /api/v1/auth/google?redirect_uri=...&frontend_origin=...
    ↓
[3] Backend risponde con l'URL di Google per l'OAuth
    ↓
[4] Il browser reindirizza su Google → utente autorizza
    ↓
[5] Google riporta su /api/v1/auth/google/callback?code=...
    ↓
[6] Backend scambia il codice con Google, crea l'atleta, genera un JWT
    ↓
[7] Backend reindirizza al frontend con #token=<JWT> nell'URL (fragment, non
    appare nei log del server)
    ↓
[8] Il frontend (main.ts) legge il fragment, salva il token nel Pinia store
    (sessionStorage), e naviga alla dashboard
```

---

## 3. Dove si trovano le parti importanti

```
D:\BikeMaster/
├── main.py                      ← ENTRYPPOINT: avvia il backend (api/hub/cli)
├── bike_analyzer/               ← TUTTO il codice Python (backend)
│   ├── backend/
│   │   ├── api/
│   │   │   ├── app_factory.py   ← Crea l'app FastAPI (middleware, router, startup)
│   │   │   ├── routes.py        ← TUTTE le API REST (100+ endpoint)
│   │   │   ├── schemas.py       ← Modelli Pydantic (validazione dati)
│   │   │   └── utils.py         ← Funzioni di utilità per le route
│   │   ├── auth/                ← Google OAuth, autenticazione
│   │   ├── security.py          ← JWT, password, token, middleware auth
│   │   ├── db/
│   │   │   ├── database.py      ← SQLite (salva/legge rides, atleti, POI...)
│   │   │   ├── models.py        ← Modelli SQLAlchemy (PostgreSQL)
│   │   │   └── async_db.py      ← Connessione async a PostgreSQL
│   │   ├── analytics/           ← Calcolo metriche (fatica, calorie, badges, coach)
│   │   ├── processing/          ← Pulizia dati GPS (process_route)
│   │   ├── maps/                ← Mappe, POI, renderer di route
│   │   ├── models/              ← Modelli dati (Ride, Athlete, GPSPoint)
│   │   ├── ingestion/           ← Import da Strava/Garmin/Wahoo/Google Fit
│   │   ├── bm2/                 ← Motore simulazione (9 algoritmi)
│   │   ├── hub/                 ← Backend cloud (multi-tenant, PostgreSQL)
│   │   └── ...                  ← eventi, redis, monitoring, geo, weather, traffic
│   └── bm2/                     ← (moduli core BM2, analytics, simulation)
├── frontend/                    ← TUTTO il codice del frontend (Vue 3)
│   ├── src/
│   │   ├── App.vue              ← Componente radice (layout, header, routing)
│   │   ├── main.ts              ← Bootstrap dell'app (Pinia, router, OAuth, PWA)
│   │   ├── router/              ← Vue Router (route/page, con guardia auth)
│   │   ├── stores/              ← Pinia stores (auth, rides, athlete, ui...)
│   │   ├── components/          ← Componenti UI riutilizzabili (50+ componenti)
│   │   ├── views/               ← Pagine intere (RidesView, DashboardPanel...)
│   │   ├── composables/         ← Funzioni riutilizzabili (useChart, useAetherMap...)
│   │   ├── services/            ← Logica di servizio (oauth, authSync)
│   │   ├── utils/               ← Strumenti (api.ts = client HTTP, backend-config)
│   │   ├── db/                  ← localDb.ts = cache SQLite locale nel browser
│   │   └── types/               ← Tipi TypeScript condivisi
│   │   ├── public/              ← Immagini, manifest PWA
│   └── src-tauri/               ← Configurazione Tauri (Rust)
├── tests/                       ← Test backend (pytest)
├── docker/                      ← Docker per sviluppo e produzione
├── render.yaml                  ← Configurazione deploy cloud (Render)
├── requirements.txt           ← Dipendenze Python
└── .env                         ← Variabili d'ambiente (locale)
```

---

## 4. Le funzioni/API più importanti

### Backend — le API REST principali (`routes.py`)

Tutte le API sono sotto il prefisso `/api/v1/`. Ecco le più usate:

| HTTP | Endpoint | Cosa fa |
|---|---|---|
| POST | `/api/v1/auth/login` | Accedi con nome utente + password → torna JWT access + refresh token |
| POST | `/api/v1/auth/register` | Registrati (crea atleta) |
| POST | `/api/v1/auth/logout` | Esci — revoca token JWT e token esterni |
| GET | `/api/v1/auth/me` | Chi sei (dati atleta, se profilo è completo) |
| GET | `/auth/google` | URL per accedere con Google OAuth |
| GET | `/auth/google/callback` | Dove Google torna dopo l'autorizzazione |
| GET | `/api/v1/rides` | Lista le tue uscite (con paginazione e ordinamento) |
| POST | `/api/v1/rides` | Salva una nuova uscita |
| GET | `/api/v1/rides/{id}` | Dettaglio di un'uscita (con metriche: fatica, calorie) |
| PUT | `/api/v1/rides/{id}` | Modifica un'uscita |
| DELETE | `/api/v1/rides/{id}` | Cancella un'uscita |
| GET | `/api/v1/athletes/me` | Dati del tuo profilo atleta |
| PUT | `/api/v1/auth/profile` | Aggiorna il profilo (età, peso, FTP...) |
| POST | `/api/v1/import/gpx` | Importa un file GPX |
| POST | `/api/v1/import/garmin` | Importa da Garmin Connect |
| GET | `/api/v1/maps/pois/nearby` | POI (fontane, ristori...) vicini a te |
| POST | `/api/v1/itineraries` | Crea un itinerario (multi-giorno) |
| GET | `/api/v1/health` | Controlla che il backend sia attivo |

Le **chiavi funzionali** sono in `security.py`:

- `create_access_token()` — genera il JWT (token valido 1 ora). Contiene `sub` (id utente), `is_admin`, `tenant_id`, `exp` (scadenza), `jti` (identificativo unico).
- `create_refresh_token()` — JWT valido 30 giorni, serve a rinnovare l'access token.
- `get_current_user()` — **FastAPI dependency** che legge l'header `Authorization: Bearer <JWT>`, lo decodifica e restituisce i dati utente. È usata in quasi tutte le route protette (si vede `current_user: dict = Depends(get_current_user)`).
- `verify_password()` / `hash_password()` — confrontano e criptano le password con bcrypt.

Le **funzioni del database** sono in `db/database.py` (SQLite) e in `db/postgres_rides.py` + altri (PostgreSQL):

- `init_db()` — crea tutte le tabelle SQLite all'avvio.
- `save_ride()` — salva un'uscita. Fa **deduplication** (se proviene da Strava/Garmin e esiste già, non la riscrive). Il dispatch SQLite-vs-PostgreSQL avviene tramite il decoratore `@pg_dispatch` in `db/dispatch.py` (vedi 6.2), non inline.
- `get_ride()` / `get_rides_by_athlete()` — leggono uscite, **filtrando sempre per tenant_id** (o athleta_id) per isolare i dati degli utenti.
- `save_athlete()` / `get_athlete()` — CRUD dell'atleta.

Le **funzioni di analisi** sono in `analytics/`:

- `calculate_fatigue_score()` — calcola la "fatica" di un'uscita (0-10).
- `estimate_recovery_hours()` — ore di recupero servete.
- `estimate_calories()` — stima le calorie bruciate (usa FC se disponibile, altrimenti fisica del movimento o MET).
- `calculate_badges()` / `get_heatmap_points()` — badge e mappa di calorio (dove esci più spesso).
- `generate_granfondo_plan()` — pianifica un granfondo (gara lunga).

### Frontend — i principali componenti

**Pinia stores** (`src/stores/`) — sono come le "caselle di memoria" dell'app:

| Store | Cosa contiene |
|---|---|
| `auth.ts` | Token JWT, dati utente, login/logout/refresh. Salva in `sessionStorage`. |
| `rides.ts` | Lista uscite, filtri, riepilogo (chilometri totali, calorie...). Carica da API o cache locale. |
| `athlete.ts` | Profilo atleta (età, peso, FTP, obiettivi...). |
| `ui.ts` | Stato dell'interfaccia (tema scuro/chiaro, loading, sidebar). |
| `itinerary.ts` | Itinerari multi-giorno e tappe. |
| `trackingStore.ts` | Dati del tracciamento live (GPS, FC, potenza in tempo reale). |

**Client HTTP** (`src/utils/api.ts`)

Tutte le chiamate al backend passano per funzioni come `apiGet()`, `apiPost()`, `apiPut()`, `apiDelete()`. Fanno una serie di cose utili:

- Aggiungono automaticamente l'header `Authorization: Bearer <token>`.
- **Retry automatico**: se il server non risponde o restituisce 502/503 (es. Render è "addormentato"), riprova 4 volte con attesa crescente.
- **Failover**: l'ultimo tentativo può andare su Render (`bikemaster.onrender.com`) come backup.
- Su errore 401, fanno logout automatico ("sessione scaduta").

**Router** (`src/router/index.ts`)

Definisce le pagine (route) e una **guardia di autenticazione** (`beforeEach`): se la pagina richiede login e non sei autenticato, ti manda alla home `/`.

**OAuth** (`src/services/oauth.ts`)

Gestisce il round-trip Google OAuth: legge il token dal fragment dell'URL (`#token=...`), lo salva nel Pinia store, e lo cancella dall'URL. Ha anche un meccanismo di **recupero sessionStorage** per non perdere il token se la pagina ricarica a metà del login.

**Local DB** (`src/db/localDb.ts`)

Usa IndexedDB (SQLite-like nel browser) per memorizzare offline le uscite e le impostazioni. È un "cache locale" per quando il backend non è raggiungibile.

---

## 5. Come sono collegati frontend e backend

### Il browser parla con il backend via HTTP REST + JSON

1. Il frontend manda richieste HTTP a `/api/v1/...` usando le funzioni in `api.ts`.
2. Il backend FastAPI le riceve, le processa, e risponde con JSON.
3. L'autenticazione avviene con un **JWT** (token) che il frontend salva e invia ad ogni richiesta.

### Dove si trova il backend (l'URL cambia)

Il frontend non ha un URL fisso del backend: lo **risolve a runtime** in `src/utils/backend-config.ts`:

```
resolveApiBase() → controlla in ordine:
   1. VITE_API_BASE (variabile impostata a build-time, usata su Vercel → Render)
   2. Se sei in Tauri → http://localhost:8001 (backend embedded)
   3. "" → same origin (default: in dev Vite fa proxy verso localhost:8001)
```

**Modalità principali:**

- **Sviluppo locale**: frontend su `localhost:5173`, backend su `localhost:8001`. Vite (dev server) fa da proxy.
- **Tauri desktop**: il backend gira *dentro* l'app, su `localhost:8001`. Il frontend (WebView) lo chiama direttamente. Niente internet necessario.
- **Vercel (produzione web)**: frontend statico su `.vercel.app`. `VITE_API_BASE` &egrave; configurato su Render (fonte di verit&agrave; produzione).
- **Render (cloud)**: backend live su `bikemaster.onrender.com`. Usato come backend primario in produzione; il fallback &egrave; gestito automaticamente.

### Cookie vs Token

L'autenticazione usa **JWT in header** (`Authorization: Bearer`), non cookie. Il token viene:
- Salvato nel `Pinia store` (che lo persiste in `sessionStorage`).
- Inviato ad ogni chiamata API da `api.ts`.
- Rinnovato automaticamente con il refresh token quando scade.

---

## 6. Punti confusi o complicati (e come funzionano)

### 6.1 OAuth con Google: tanti passaggi

Il login con Google è complicato perché deve funzionare in **diverse condizioni**: browser web, app Tauri, app mobile. Il flusso è:

```
Frontend → GET /auth/google → backend → URL Google
  → utente autorizza → Google → /auth/google/callback
  → backend scambia code → crea JWT →
  reindirizza al frontend con #token=JWT  (fragment!)
  → frontend (main.ts) legge il fragment, salva token, pulisce URL
```

Perché l'URL è un **fragment** (`#token=...`) e non un query param? Perché i fragment **non vengono mai inviati al server**, quindi il JWT non appare nei log di Google o del tuo proxy.

C'è anche una versione **SPA popup** (`code-exchange`) per quando il backend non può fare redirect (es. dentro Tauri).

### 6.2 SQLite vs PostgreSQL: il dispatch centralizzato

Il codice ha due percorsi per il database, decisi da **una sola variabile**: `DATABASE_URL`. Quando è impostata (produzione su Render), le funzioni mandano a PostgreSQL; altrimenti usano SQLite locale.

Il punto chiave: il dispatch **non** è più sparso in ogni funzione. Esiste un unico modulo, `bike_analyzer/backend/db/dispatch.py`, che è la fonte di verità:

```python
# bike_analyzer/backend/db/dispatch.py  ← DECIDe SOLO QUI
def is_postgres() -> bool:        # True se DATABASE_URL è impostata
    ...

POSTGRES_BACKENDS = {             # ← confine di migrazione in un posto solo
    "athlete":     ("...postgres_athlete",     [get_athlete, save_athlete, ...]),
    "rides":       ("...postgres_rides",       [save_ride, get_ride, ...]),
    "itineraries": ("...postgres_itineraries", [save_itinerary, ...]),
}

@pg_dispatch("bike_analyzer.backend.db.postgres_rides")
def save_ride(ride: dict) -> int:
    """...corpo SQLite, niente if has_postgres() inline..."""
```

Prima, **33 funzioni** in `database.py` avevano una copia incolata di `if has_postgres(): return _pg_...`. Ora basta un decoratore e il dispatch (con import *lazy* di psycopg2) vive solo in `dispatch.py`.

Puoi vedere subito quali domini sono migrati aprindo `POSTGRES_BACKENDS`. **Tutto il resto** (POI, HR 24h, metabolismo, chat, calendario, weather, BLE, sensor, utenti, consenso, road incidents, route safety, fitness states, nutrizione, Beck, audit) è **solo SQLite**: i dati andranno persi se il container di Render riavvia. I dati critici (ride, atleta, metrics, itinerari, training goals) sono migrati su PostgreSQL e sono al sicuro.

> Nota tecnica: i moduli `*_rides.py`/`*_athlete.py` sono **sincroni** (psycopg2), non async, nonostante l'ORM in `models.py`/`async_db.py` sia async. I 33 wrapper di `database.py` tengono lo stesso **ordine e nomi degli argomenti** dei loro specchi PostgreSQL, così le route non cambiano.

### 6.3 Retry e failover delle API

In `api.ts`, quando il backend non risponde (es. Render è "addormentato" nella tier gratuita e si risveglia dopo 50 secondi), il frontend:

1. Aspetta (con backoff: 1.5s, 3s, 4.5s...)
2. Notifica "Il server si sta riavviando, attendo qualche secondo…"
3. All'ultimo tentativo, se il fallback è abilitato, prova su `bikemaster.onrender.com`

Questo rende l'app molto resiliente ma può causare **ritardi di carico** quando il server è addormentato.

### 6.4 Service worker e aggiornamenti

In `main.ts`, quando arriva un nuovo aggiornamento del frontend (il service worker scarica una nuova versione):

- Se sei **nel bel mezzo di un login OAuth**, aspetta che finisca prima di aggiornare.
- Altrimenti, aggiorna immediatamente con `SKIP_WAITING`.

### 6.5 Tauri: frontend + backend nello stesso file

Con Tauri, il frontend Vue viene **imbundito dentro l'app desktop**. Il backend FastAPI gira come processo separato su `localhost:8001`. Il frontend lo chiama via HTTP ma da locale (non passa internet). Il tutto è in `src-tauri/`.

### 6.6 Multi-tenant

Ogni utente ha un `tenant_id` (di solito uguale al suo id). Tutte le query filtrano per `tenant_id` per isolare i dati. Gli utenti "admin" possono vedere il tenant di tutti. Questo è importante per la versione cloud (hub) dove più atleti condividono lo stesso database PostgreSQL.

### 6.7 Repository + key-provider (layered dependencies)

Il Service layer non tocca mai il database né l'API HTTP direttamente. La
direzione delle dipendenze è unidirezionale (AGENTS.md §2):

    Router -> Service -> Repository -> db.database
                         |
                         v
               user_keys_provider (Protocol, trasport-agnostic)
                 -> request_context (infra, lazy ContextVar)

- `WeatherService` (`backend/weather/weather_service.py`) legge/scrive la cache
  SOLO tramite `WeatherRepository` (`backend/weather/repositories/weather_repository.py`),
  mai tramite `from ..db.database import ...` nel service. L'import di
  `db.database` dentro il repository è *lazy* (nei metodi) per evitare il ciclo
  di caricamento `db.database <-> db/repositories/*` già presente nel layer di
  persistenza. Rompie il viezo `Service -> Database`.
- Le chiavi API per-utente arrivano dal *provider*
  (`UserKeysProvider` / `ContextVarUserKeysProvider` in
  `backend/user_keys_provider.py`), popolato dal middleware
  (`X-User-Api-Keys` -> `request_context`) — NON da `api/user_keys`. Rompie il
  vecchio ciclo `Service -> api`.
- Stesso pattern: `analytics/ai_coach.py` usa `AIAuditRepository` + provider,
  `analytics/metabolism.py` usa `MetabolismRepository`.

> Verifica di aciclicità: `tests/test_weather_repository.py` analizza l'AST delle
> sorgenti del Service layer e FALLISCE se un service importa `db.database` o
> `api.user_keys` (cattura anche import lazy dentro i metodi).

---

## 7. Come avviare l'app (riassunto veloce)

**Solo backend (per sviluppo API):**
```bash
python main.py api --port 8001
```

**Frontend (dev server con hot-reload):**
```bash
cd frontend && npm run dev
# → http://localhost:5173 (vite proxy a localhost:8001)
```

**Desktop (Tauri):**
```bash
cd frontend && npm run tauri dev
```

**Backend cloud (hub):**
```bash
python main.py hub --port 10000
```

Le **variabili d'ambiente** importanti (`.env`):
- `DATABASE_URL` — se impostata, usa PostgreSQL invece di SQLite.
- `VITE_API_BASE` — URL del backend, usata dal frontend su Vercel.
- `GOOGLE_MAPS_API_KEY` — per le mappe.
- `SECRET_KEY` — firma dei JWT.

---

*Questa documentazione copre le parti più importanti del progetto. Se vuoi approfondire un'area specifica (ad esempio il motore BM2, le mappe AetherMap, o il sistema di importazione), chiedi pure!*
