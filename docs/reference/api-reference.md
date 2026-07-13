# API Reference — Completa

Riferimento esaustivo di tutti gli endpoint REST di BikeMaster, generato dai file di route reali:
`bike_analyzer/backend/api/routes.py` (router pubblico + `admin_router`) e
`bike_analyzer/backend/api/bm2_routes.py`.

- **Base URL API:** `/api/v1`
- **Base URL Admin:** `/api/v1/admin`
- **Base URL BM2:** `/api/v1/bm2`
- **Totale endpoint:** 133 (router + admin) + 5 (BM2) = **138**

## Convenzioni

| Colonna | Significato |
|---|---|
| **Auth** | `Yes` = richiede un JWT valido (`Authorization: Bearer <token>`) tramite `Depends(get_current_user)`. `No` = endpoint pubblico. |
| `{param}` | Segmento di path variabile. |

### Autenticazione

L'autenticazione usa JWT (HS256) emessi da `POST /api/v1/auth/login`. Il token va inviato nell'header:

```
Authorization: Bearer <access_token>
```

Configurazione JWT: `SECRET_KEY`, `ALGORITHM=HS256`, `ACCESS_TOKEN_EXPIRE_MINUTES=30`, `JWT_ISSUER`, `JWT_AUDIENCE` (vedi [configuration.md](./configuration.md)).

### Rate limiting

Il rate limiting è gestito da `slowapi` (`SlowAPIMiddleware`), per-IP e proxy-aware. Gli endpoint sensibili (login/register) hanno limiti dedicati.

### Formato errori

Gli errori seguono il formato standard FastAPI:

```json
{ "detail": "Messaggio di errore" }
```

Codici comuni: `400` (input non valido), `401` (non autenticato), `403` (non autorizzato / tenant errato), `404` (risorsa inesistente), `422` (validazione schema), `429` (rate limit), `500` (errore interno).

---

## 1. Health & Monitoring

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/health` | No | Health check di base |
| GET | `/api/v1/health/detailed` | No | Health check dettagliato (DB, cache, dipendenze) |
| GET | `/api/v1/health/redis` | No | Stato connessione Redis |
| POST | `/api/v1/alerts/webhook` | No | Ingest webhook di Alertmanager |
| GET | `/api/v1/sentry-debug` | No | Endpoint di test per Sentry (genera errore) |

---

## 2. Autenticazione & Account

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| POST | `/api/v1/auth/login` | No | Login con username/password → JWT (rate-limited) |
| POST | `/api/v1/auth/register` | No | Registrazione nuovo utente (rate-limited) |
| POST | `/api/v1/auth/refresh` | No | Rinnovo access token |
| POST | `/api/v1/auth/logout` | Yes | Logout (invalidazione lato client) |
| GET | `/api/v1/auth/me` | Yes | Profilo dell'utente autenticato |
| PUT | `/api/v1/auth/profile` | Yes | Aggiornamento profilo utente |
| POST | `/api/v1/auth/change-password` | Yes | Cambio password |
| GET | `/api/v1/auth/google` | No | URL di autorizzazione Google OAuth2 |
| GET | `/api/v1/auth/google/callback` | No | Callback OAuth2 Google (redirect) |
| POST | `/api/v1/auth/google/code-exchange` | No | Scambio authorization code → token (mobile/SPA) |

---

## 3. Rides (CRUD & analisi)

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| POST | `/api/v1/rides` | Yes | Crea una ride |
| GET | `/api/v1/rides` | Yes | Elenco ride (paginato, tenant-scoped) |
| GET | `/api/v1/rides/count` | Yes | Conteggio ride |
| GET | `/api/v1/rides/{ride_id}` | Yes | Dettaglio ride (+ fatica, cal/km) |
| PUT | `/api/v1/rides/{ride_id}` | Yes | Aggiorna ride |
| DELETE | `/api/v1/rides/{ride_id}` | Yes | Elimina ride |
| POST | `/api/v1/rides/analyze` | Yes | Analisi aggregata multi-ride |
| POST | `/api/v1/rides/{ride_id}/analyze` | Yes | Analisi di una singola ride |
| GET | `/api/v1/rides/{ride_id}/report` | Yes | Report testuale della ride |
| GET | `/api/v1/rides/{ride_id}/segments` | Yes | Segmenti della ride |
| GET | `/api/v1/rides/{ride_id}/power-metrics` | Yes | Metriche di potenza (NP, IF, TSS, ecc.) |
| GET | `/api/v1/rides/{ride_id}/safety` | Yes | Punteggio di sicurezza del percorso |
| GET | `/api/v1/rides/{ride_id}/map` | Yes | Mappa della ride (Leaflet/Folium) |
| GET | `/api/v1/rides/{ride_id}/map/google` | Yes | Mappa statica Google della ride |
| GET | `/api/v1/rides/{ride_id}/speed-path` | Yes | Traccia colorata per velocità |

### Export

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/rides/export/json` | Yes | Export ride in JSON |
| GET | `/api/v1/rides/export/csv` | Yes | Export ride in CSV |

---

## 4. Import (GPS files & provider esterni)

### File upload

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| POST | `/api/v1/import/gpx` | Yes | Upload e parsing file GPX |
| POST | `/api/v1/import/fit` | Yes | Upload e parsing file Garmin FIT |
| POST | `/api/v1/import/multiple` | Yes | Upload batch di più file |
| GET | `/api/v1/import/providers` | No | Elenco provider di import disponibili |

### Strava

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/import/strava/auth` | Yes | URL autorizzazione Strava (OAuth2 + PKCE) |
| GET | `/api/v1/import/strava/callback` | No | Callback OAuth2 Strava (redirect) |
| POST | `/api/v1/import/strava/callback` | Yes | Scambio token Strava |
| POST | `/api/v1/import/strava/sync` | Yes | Sincronizza attività Strava (batch) |
| DELETE | `/api/v1/import/strava/disconnect` | Yes | Disconnette Strava |

### Garmin Connect

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/import/garmin/auth` | Yes | URL autorizzazione Garmin (OAuth2) |
| POST | `/api/v1/import/garmin/callback` | Yes | Scambio token Garmin |
| POST | `/api/v1/import/garmin/sync` | Yes | Sincronizza attività Garmin |
| DELETE | `/api/v1/import/garmin/disconnect` | Yes | Disconnette Garmin |

### Wahoo Fitness

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/import/wahoo/auth` | Yes | URL autorizzazione Wahoo (OAuth2) |
| POST | `/api/v1/import/wahoo/callback` | Yes | Scambio token Wahoo |
| POST | `/api/v1/import/wahoo/sync` | Yes | Sincronizza attività Wahoo |
| DELETE | `/api/v1/import/wahoo/disconnect` | Yes | Disconnette Wahoo |

### Google Fit / Google Health

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/import/google-fit/auth` | No | URL autorizzazione Google Fit |
| GET | `/api/v1/import/google-fit/callback` | No | Callback OAuth2 Google Fit |
| POST | `/api/v1/import/google-fit/token` | Yes | Scambio token Google Fit |
| POST | `/api/v1/import/google-fit` | Yes | Importa attività da Google Fit |
| DELETE | `/api/v1/import/google-fit/disconnect` | Yes | Disconnette Google Fit |
| GET | `/api/v1/import/google-health/auth` | No | URL autorizzazione Google Health |
| GET | `/api/v1/import/google-health/callback` | No | Callback OAuth2 Google Health |
| POST | `/api/v1/import/google-health` | Yes | Importa attività da Google Health |
| DELETE | `/api/v1/import/google-health/disconnect` | Yes | Disconnette Google Health |

---

## 5. Athletes

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| POST | `/api/v1/athletes` | Yes | Crea profilo atleta |
| GET | `/api/v1/athletes` | Yes | Elenco atleti (tenant-scoped) |
| GET | `/api/v1/athletes/me` | Yes | Profilo atleta dell'utente corrente |
| GET | `/api/v1/athletes/{athlete_id}` | Yes | Dettaglio atleta |
| PUT | `/api/v1/athletes/{athlete_id}` | Yes | Aggiorna atleta |
| POST | `/api/v1/athletes/{athlete_id}/metrics` | Yes | Salva metriche dell'atleta |

---

## 6. Scores & Benchmark

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/scores/athlete/{athlete_id}` | Yes | Punteggi dell'atleta |
| POST | `/api/v1/benchmark/compare` | Yes | Confronto benchmark per categoria |

---

## 7. Analytics

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/analytics/trends` | Yes | Trend nel tempo |
| GET | `/api/v1/analytics/monthly` | Yes | Aggregati mensili |
| GET | `/api/v1/analytics/comparison` | Yes | Confronto tra periodi |
| GET | `/api/v1/analytics/projection` | Yes | Proiezioni di performance |
| GET | `/api/v1/analytics/speed-data` | Yes | Serie dati di velocità |
| GET | `/api/v1/analytics/multi-classify` | Yes | Classificazione multi-modello |
| GET | `/api/v1/analytics/vip` | Yes | Predizione VIP/performance |
| GET | `/api/v1/analytics/inactivity` | Yes | Stima inattività |
| GET | `/api/v1/analytics/route-suggestions` | Yes | Suggerimenti di percorso |
| GET | `/api/v1/heatmap` | Yes | Heatmap densità percorsi |
| GET | `/api/v1/badges` | Yes | Badge e riconoscimenti |

### Charts (PNG)

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/charts/speed/{ride_id}` | Yes | Grafico velocità (PNG) |
| GET | `/api/v1/charts/elevation/{ride_id}` | Yes | Grafico altimetria (PNG) |
| GET | `/api/v1/charts/distance/{ride_id}` | Yes | Grafico distanza (PNG) |
| GET | `/api/v1/charts/duration` | Yes | Grafico durata (PNG) |

---

## 8. Training

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/training/load` | Yes | Carico di allenamento (TSS/ATL/CTL/TSB) |
| GET | `/api/v1/training/status` | Yes | Stato forma/fatica |
| GET | `/api/v1/training/summary` | Yes | Riepilogo allenamento |
| POST | `/api/v1/training/goals` | Yes | Crea obiettivo di allenamento |
| GET | `/api/v1/training/goals` | Yes | Elenco obiettivi |
| POST | `/api/v1/training/workouts/generate` | Yes | Genera workout pianificati |
| POST | `/api/v1/training/granfondo/plan` | Yes | Genera piano granfondo (con tapering) |
| POST | `/api/v1/training/granfondo/save` | Yes | Salva piano granfondo |

---

## 9. Calendar

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| POST | `/api/v1/calendar/events` | Yes | Crea evento di calendario |
| GET | `/api/v1/calendar/events` | Yes | Elenco eventi |
| GET | `/api/v1/calendar/events/range` | Yes | Eventi in un intervallo di date |
| GET | `/api/v1/calendar/events/{event_id}` | Yes | Dettaglio evento |
| PUT | `/api/v1/calendar/events/{event_id}` | Yes | Aggiorna evento |
| DELETE | `/api/v1/calendar/events/{event_id}` | Yes | Elimina evento |
| POST | `/api/v1/calendar/events/{event_id}/complete` | Yes | Segna evento come completato |

---

## 10. AI Coach & Knowledge Base

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/coach/chat` | Yes | Recupera conversazione chat |
| POST | `/api/v1/coach/chat` | Yes | Invia messaggio all'AI Coach |
| GET | `/api/v1/coach/history` | Yes | Storico chat |
| GET | `/api/v1/coach/workout` | Yes | Consiglio workout personalizzato |
| GET | `/api/v1/coach/recovery` | Yes | Consiglio di recupero |
| GET | `/api/v1/coach/trends` | Yes | Analisi trend dell'atleta |
| GET | `/api/v1/coach/full` | Yes | Report coaching completo |
| GET | `/api/v1/coach/page` | No | Pagina HTML dell'AI Coach |

### Knowledge Base (RAG)

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/knowledge` | No | Elenco documenti della knowledge base |
| GET | `/api/v1/knowledge/search` | No | Ricerca semantica (BM25/PGVector) |
| GET | `/api/v1/knowledge/stats` | Yes | Statistiche knowledge base |
| POST | `/api/v1/knowledge/reload` | No | Ricarica knowledge base |
| POST | `/api/v1/knowledge/init-embeddings` | No | Inizializza embeddings |

---

## 11. Maps & POI

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/config/google-maps-key` | Yes | Chiave Google Maps (per il client) |
| GET | `/api/v1/maps/pois` | No | Elenco POI |
| GET | `/api/v1/maps/pois/nearby` | No | POI vicini a una coordinata |
| POST | `/api/v1/maps/pois` | Yes | Crea POI |
| GET | `/api/v1/maps/pois/{poi_id}` | No | Dettaglio POI |
| DELETE | `/api/v1/maps/pois/{poi_id}` | Yes | Elimina POI |
| GET | `/api/v1/maps/places/nearby` | Yes | Luoghi vicini |
| GET | `/api/v1/maps/places/search` | Yes | Ricerca luoghi |
| GET | `/api/v1/maps/places/osm-search` | No | Ricerca luoghi via OSM/Nominatim |

---

## 12. Weather

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/weather` | No | Meteo corrente |
| GET | `/api/v1/weather/forecast` | No | Previsioni meteo |

---

## 13. Traffic Safety

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/traffic/road-types` | No | Tipi di strada (OSM/Overpass) |
| GET | `/api/v1/traffic/bike-infrastructure` | No | Infrastrutture ciclabili |
| GET | `/api/v1/traffic/incidents` | No | Incidenti stradali nell'area |

---

## 14. Dashboard

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/dashboard` | Yes | Dati aggregati per la dashboard |

---

## 15. Admin (`/api/v1/admin`)

> **Nota di sicurezza:** questi endpoint sono montati sotto `admin_router`. Verificare le protezioni di accesso a livello di deployment: dall'analisi del codice non risultano dipendenze `get_current_user` sui singoli handler admin, quindi vanno protetti a livello di rete/reverse proxy o aggiungendo un controllo ruolo admin.

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/admin/athletes` | No | Elenco completo atleti (admin) |
| GET | `/api/v1/admin/stats` | No | Statistiche di sistema |
| GET | `/api/v1/admin/backup` | No | Backup del database |
| POST | `/api/v1/admin/backup/scheduled` | No | Avvia backup schedulato |
| POST | `/api/v1/admin/indexes` | No | (Ri)crea indici DB |
| POST | `/api/v1/admin/reset-demo` | No | Reset dati demo |
| GET | `/api/v1/admin/ceo` | No | Cruscotto CEO/aggregati |
| GET | `/api/v1/admin/audit-logs` | No | Log di audit |
| GET | `/api/v1/admin/test-sentry` | No | Test integrazione Sentry |

---

## 16. BikeMaster 2.0 — Simulation Engine (`/api/v1/bm2`)

Vedi [engines-and-analytics.md](./engines-and-analytics.md) per il dettaglio degli algoritmi.

| Metodo | Endpoint | Auth | Descrizione |
|---|---|:---:|---|
| GET | `/api/v1/bm2/models` | No | Elenco algoritmi/modelli BM2 disponibili |
| POST | `/api/v1/bm2/ask` | No | Query interpretata sui modelli BM2 |
| POST | `/api/v1/bm2/simulate` | No | Simulazione what-if generica |
| POST | `/api/v1/bm2/simulate-ride` | Yes | Simulazione what-if su una ride esistente |
| POST | `/api/v1/bm2/validate` | Yes | Validazione input/contratti BM2 |

---

## Riferimenti

- Schemi request/response (Pydantic): `bike_analyzer/backend/api/schemas.py`
- Factory dell'app e middleware: `bike_analyzer/backend/api/app_factory.py`
- Rate limiter: `bike_analyzer/backend/rate_limiter.py`
- Sicurezza / JWT: `bike_analyzer/backend/security.py`
- Esempi di richieste: [`../API_EXAMPLES.http`](../API_EXAMPLES.http)
