# Piano di Refactor BikeMaster

**Obiettivo**: portare BikeMaster da "progetto tecnico con tante feature" a prodotto
funzionale organizzando i pezzi esistenti, senza rompere ciò che non deve cambiare.

**Principio guida**: la fondazione che NON dipende dal prodotto (identità, OAuth,
contratti DB/API, sicurezza) viene **bloccata e indurita per prima**. Il refactor
prodotto (Activity generico, tracking always-on, health profile, AI fusion) si
costruisce SOPRA questa fondazione e non la tocca.

---

## Fase 0 — Fondazione immutabile (blindare per prima)

Queste parti restano invariate a prescindere dall'evoluzione del prodotto. Vanno
rese robuste e poi "congelate" come contratto.

### 0.1 Identità & Auth (contratto fisso)
| Pezzo | Dove | Stato |
|---|---|---|
| Login / Register / Logout / Refresh | `api/routes.py:432,555,496,527` | ✅ stabile, rate-limited |
| `/auth/me`, `/auth/profile`, change-password | `api/routes.py:657,689,720` | ✅ |
| JWT HS256 + bcrypt + rotazione key | `backend/security.py` | ✅ |
| Rate limiting auth (login 5/min, register 3/min) | `rate_limiter.py` + `routes.py` | ✅ |
| Isolamento tenant (`tenant_id`) | `db/models.py`, `AthleteModel/RideModel` | ✅ |
| OAuth Google login (URL, exchange, session) | `auth/google_auth.py` | ✅ ma scope limitato |

**Da sistemare ORA (stabilizzazione):**
- `google_auth.py:18` scope è solo `openid email profile`. Per la visione
  "salute + Google Fit/Health" servono scope aggiuntivi (`fitnes...`, `health...`).
  Preparare lo switch ma NON rompere il login base.
- `redirect_uri` hardcoded di default in `google_auth.py:10` e `schemas.py:329,145`.
  Centralizzare in `settings.py` (`GOOGLE_REDIRECT_URI`) così dev/prod non divergono.

### 0.2 OAuth Callback (contratti fissi dettati dai provider)
| Flusso | Endpoint | Stato |
|---|---|---|
| Google login | `/auth/google` + `/auth/google/callback` + `/auth/google/code-exchange` | `routes.py:743,762,895` |
| Strava import | `/import/strava/auth` + `/import/strava/callback` | `strava_client.py` + routes |
| Garmin import | `/import/garmin/*` | `garmin_client.py` |
| Google Fit | `/import/google-fit/auth|token|callback|` | `routes.py:1582,1767,1809,1901` |
| Google Health | `/import/google-health/auth|callback|` | `routes.py:1601,1629,1715` |

**Da sistemare ORA:**
- Le race condition OAuth (loading overlay / redirect) sono già state risolte ma
  sono fragili (vedi `AGENTS.md` router guard). Aggiungere test E2E che le blocchino.
- `STRAVA_REDIRECT_URI` deve puntare a `/api/v1/import/strava/callback` (path
  `/import/`, non `/auth/`) — già documentato, verificare che valga per tutti i provider.

### 0.3 Contratti DB (schema "owned")
Tabelle con colonne di ownership fisse: `users`, `athletes`, `rides`
(`db/models.py`, `core/models.py:74`).
**Regola**: `athlete_id` + `tenant_id` sono intoccabili. Ogni nuova tabella (es.
`activities`, `health_samples`) EREDITA queste due colonne, non le reimplementa.

### 0.4 Contratti API (il frontend dipende da questi)
- Prefisso fisso `/api/v1` (`app_factory.py:202`).
- Forme di risposta in `api/schemas.py` (RideResponse, Athlete*, Token, POI*).
- **Regola di freeze**: i refactor di prodotto estendono gli schema (nuovi campi
  opzionali) ma non cambiano tipi/campi esistenti, per non rompere frontend/Android.

### 0.5 Sicurezza & Infra (fissa)
CSP/HSTS/rate-limit (`security.py`), Docker hardened, CI GitHub Actions, monitoring
(Sentry/Prometheus). Non toccare durante il refactor.

---

## Fase 1 — Refactor sopra la fondazione (mutabile)

Costruiti SOPRA Fase 0, retro-compatibili.

### 1.1 `Ride` → `Activity` (sblocca tutto)
- Estendere `core/models.py:74` `Ride` con `activity_type`, `is_official`, `source`
  (campi opzionali → non rompe schema esistente).
- Estendere `RideModel` (`db/models.py:84`) + Alembic migration additiva.
- `RideCreate`/`RideResponse` (`schemas.py:8,23`): aggiungere campi opzionali.
- Gli strumenti esistenti (TSS, FTP, power, fatigue) restano identici.

### 1.2 Tracking always-on (SessionData)
- `trackingStore.ts`: aggiungere `mode: 'live'|'background'|'off'` + `promoteToRide()`.
- Riutilizzare `BikeTrackingService.kt` (foreground service già pronto).

### 1.3 Health Profile proprio
- Nuova tabella `health_samples` (sleep, hrv, steps, resting_hr, weight) con
  `athlete_id`+`tenant_id`. Estendere `google_fit.py` da OAuth→fetch+store.

### 1.4 Fusion Layer → AI (il "unire con intelligenza")
- Estendere `analytics/services/context_builder.py` per ingerire health + weather +
  traffic oltre a rides/fitness_state. Base già presente, da ampliare.

### 1.5 Versioni native (quando lo scheletro regge)
- Mappe MapLibre GL + OSM (hai `osm_maps.py`); Health DB proprio invece di dipendere
  solo da Google Fit.

---

## Regole di non-regressione
1. Ogni refactor aggiunge campi, non li rimuove/ritipizza negli schema API e DB.
2. I test OAuth esistenti (e quelli E2E da aggiungere) devono restare verdi.
3. `tenant_id`/`athlete_id` obbligatori in ogni nuova query (ereditati, non nuovi).
4. Auth/security non vengono toccati dalle fasi 1.x.

## Sequenza consigliata
1. **Fase 0 stabilizzazione** (redirect URI in settings, scope Google pronti,
   test E2E OAuth) → fondazione blindata.
2. Fase 1.1 (Ride→Activity) → moltiplicatore per le successive.
3. Fase 1.2 → 1.3 → 1.4 → 1.5.

*Nota: la Fase 0 non richiede nuove feature, solo robustezza e freeze dei contratti.*
