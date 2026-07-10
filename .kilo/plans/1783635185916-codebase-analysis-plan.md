# Analisi completa BikeMaster — Codice & Applicazione

**Scope:** analisi qualità, architettura, sicurezza e stato test/build su tutte le parti
(frontend, backend API/auth, analytics/AI coach, data layer, CI). Nessun file sorgente
è stato modificato. I fix della test-suite frontend (vedi `.kilo/plans/1783631660667-failing-tests-debug-plan.md`)
risultano già applicati nel working tree.

## Stato implementazione (primo passo — fix contenute e ad alto valore)
**FATTO:**
- §2.1.1 Open redirect OAuth: `_validate_redirect_uri` non si fida più dell'header `Origin`
  (rimosso `dynamic_hosts`); allow-list statica (CORS hosts + `oauth_allowed_redirect_hosts`
  in `settings.py` + localhost + `bikemaster.onrender.com`/`testserver`). `routes.py` + `settings.py`.
- §2.1.3 `refresh_token` usa `decode_token_with_fallback` (gestisce `SECRET_KEY_PREVIOUS`). `routes.py:444`.
- §2.1.4 `/sentry-debug` gated fuori produzione. `routes.py:318`.
- §2.1.6 HSTS anche su `staging` + header `Permissions-Policy`/`Cross-Origin-Resource-Policy`. `app_factory.py:179`.
- §2.1.7 audit log usa `X-Forwarded-For` (proxy-aware). `app_factory.py:162`.
- §2.5.22 AGENTS.md aggiornato: il logout silenzioso su 401 è già implementato.
- §2.6.26 CI frontend: aggiunti `lint` + `typecheck` + `vitest run` prima di `build`. `ci.yml`.
- §2.6.29 `prebuild.mjs`: log esplicito invece di commento vuoto.
- Pulizia lint: rimosso import `_forwarded_value` morto in `app_factory.py`.

**VALIDATO:** `ruff` pulito su file modificati; import OK; `pytest tests/test_routes_coverage.py::test_register_endpoint_success` PASS.

**RIMANENTE (refactor ampi/rischiosi — NON fatti in questo passo):**
- §2.2.8/2.2.9 Data layer async/Postgres: `backend/db/models.py` inesistente + `async_db.py` stub.
  Richiede definizione ORM + `get_session_factory`/`get_rides_by_athlete_async` reali; rischioso
  senza conoscere lo schema. Opzione: implementare il layer async o disabilitarlo esplicitamente
  finché non funzionante (l'app gira su SQLite oggi).
- §2.2.10 Modelli dominio duplicati (`core/models.py` vs `backend/models/models.py`).
- §2.3.12 Validazione Pydantic su import GPX/FIT; §2.2.11 HTTP async (`httpx`/backoff); §2.3.13 matplotlib `to_thread`.
- §2.3.14/2.4.19 Pagination DB + index composito; §2.3.15 EMBEDDING_DIMENSION 1536→384.
- §2.4.16/17 Consolidamento TSS/ATL-CTL-TSB; dead code; Google Fit deprecato.
- §2.6.27 Pin TS 5.x; §2.6.28 riconciliazione requirements/pyproject.

---

## 1. Architettura (riassunto)

- **Frontend:** Vue 3 + Pinia + Vue Router 4 + Vite 5 + PWA (`vite-plugin-pwa`). ~109 file `src/**`. Auth via JWT in `localStorage`, guard router con sync da localStorage per evitare race OAuth.
- **Backend:** FastAPI esposto su `/api/v1`. **Default: SQLite sync** (`db/database.py`). Percorso **async/Postgres** opzionale (`db/async_db.py`, `async_db_facade.py`, repositories) — *attualmente rotto* (vedi §2.3).
- **Analytics:** `backend/analytics/` (30+ file) + `bike_analyzer/core/` (motore/pipeline/calculators). Ampia sovrapposizione di logica (modelli dominio, TSS, training load).
- **Integrazioni:** ingestion Strava/Garmin/Google Fit/Health/Wahoo, maps (Google/OSM/SerpApi), weather, traffic, **AI coach + PgVector** (`vectordb.py`, `knowledge_base.py`, `ai_coach.py`).
- **Infra:** Docker/Render, Alembic, Prometheus/Grafana, Capacitor (Android), OpenTelemetry tracing.

---

## 2. Findings per priorità

### 2.1 CRITICAL / HIGH — Sicurezza & Auth (`backend/security.py`, `api/routes.py`, `auth/`)
1. **Open redirect OAuth via spoofing header `Origin`** — `routes.py` (`_validate_redirect_uri`): la whitelist valida l'host prendendolo dall'`Origin` della request. Un attacker falsifica `Origin` → `redirect_uri` risolve a dominio controllato → credential harvesting. **Fix:** whitelist statica di domini consentiti in `settings.py`, ignora `Origin` non fidato.
2. **`revoke_token` ritorna `True` con Redis=None** — `security.py:125-127` (modifica non committata). Il revoke va solo in dict in-memory, perso al restart; combinato con `is_token_revoked` che ritorna `False` se Redis=None (`:141-144`), i token revocati tornano validi dopo outage Redis. **Fix:** ritornare esito coerente col degradation; richiedere Redis in prod all'avvio.
3. **`refresh_token` usa `SECRET_KEY` grezza, non `decode_token_with_fallback`** — `routes.py:444`. Rotazione `SECRET_KEY_PREVIOUS` valida i access token vecchi ma **non** i refresh token → logout forzato dopo rotazione. **Fix:** usare il decoder con fallback.
4. **`/sentry-debug` esposto in tutti gli ambienti** — `routes.py:318-321` (solleva `ZeroDivisionError`). Gated dietro env check o rimosso in prod.
5. **Weak password policy** — `routes.py:477` minimo 6 char, nessuna complessità, nessun `max_length` su username. **Fix:** ≥8-12, controllo breached password, validator username.
6. **Header HSTS solo `production`/`prod`** — `routes.py:186` ma CORS wildcard ammette `staging` (`:206`). Beta/staging senza HSTS. Aggiungere `staging`; aggiungere `Permissions-Policy`/`Cross-Origin-Resource-Policy` in `app_factory.py:180`.
7. **Audit log usa `request.client.host`** — `app_factory.py:163` (IP socket, non `X-Forwarded-For`) → dietro proxy logga l'IP del proxy.

### 2.2 HIGH — Data layer & DB (`backend/db`, `core`)
8. **`backend/db/models.py` inesistente ma importato** (confermato): `routes.py:357,484`, `knowledge_base.py:722,767`, `repositories/user_repository.py:96`, `fitness_state_repository.py:19`, `athlete_repository.py:98`, `ride_repository.py:17`, `async_db_facade.py:15`. **Runtime `ImportError` non appena `DATABASE_URL` (Postgres/async) è settato in produzione.**
9. **`db/async_db.py` è uno stub di 9 righe che ritorna `[]`** e `get_session_factory` non è definito lì (importato in `async_db_facade.py:14`). `core/engine.py:92` chiama `get_rides_by_athlete_async` → storico ride **silenziosamente vuoto**. Il path async non è funzionante end-to-end.
10. **Modelli dominio duplicati** — `core/models.py` vs `backend/models/models.py` definiscono `Ride`, `AthleteProfile`, `GPSPoint`, ecc. con campi divergenti (es. `tenant_id` presente solo in `backend/models`). Rischio data loss/confusione di tipo.
11. **Sync HTTP bloccante dentro route async** — `strava_client.py`, `garmin_client.py`, `google_fit.py`, `osm_maps.py` usano `requests` sincrono nel loop eventi. Nessun retry/backoff (Strava manda 429/503). **Fix:** `httpx.AsyncClient` + `asyncio.to_thread`/backoff.

### 2.3 HIGH — Code health backend
12. **Import route saltano la validazione Pydantic** — `/import/gpx`, `/import/fit` (`routes.py:1030-1111`) fanno solo check sulla dimensione file, ignorando `core/validation.py` (`ValidatedRide`, `ValidatedGPSPoint` con bounds). **Fix:** validare il parsed payload.
13. **Matplotlib bloccante in route async** — `analytics.py` (`create_speed_chart`, ecc.) chiamato da `routes.py:1245-1325` senza `asyncio.to_thread`.
14. **Pagination in Python** — `routes.py:886-905` carica tutte le ride e fa slice in memoria. Mancano `LIMIT/OFFSET` DB.
15. **Embedding dimension mismatch** — `knowledge_base.py:36` `EMBEDDING_DIMENSION=1536` ma `all-MiniLM-L6-v2` produce 384-dim; padding/truncation maschera il problema ma degrada la similarità coseno. **Fix:** allineare a 384 o al modello reale.

### 2.4 MEDIUM
16. **Tripla implementazione ATL/CTL/TSB** (`training_load.py`, `advanced.py` x2 + pkg opzionale) e **TSS duplicato** (`training_load.py:23` vs `power_model.py:65`). Consolidare in un'unica fonte.
17. **Dead code** — `routes.py:1565-1612` (dopo `return` a :1558 in `google_health_callback`); `routes.py:792-801` secondo `except Exception` irraggiungibile.
18. **Google Fit deprecato** — `routes.py:1836-1838`; `google_fit.py` hardcodata a 2099. Migrare a Google Health o rimuovere.
19. **Mancano index compositi** — `database.py:create_indices` fa index a colonna singola; servirebbe `(athlete_id, date)` (query pattern più comune).
20. **`GPSParser` swallows ImportError** — `gps_parser.py:96` `raise ... from None` perde il contesto.
21. **Race condition su external_id** — `database.py:save_ride` check-then-insert senza lock/UPSERT.

### 2.5 FRONTEND (`frontend/src`)
22. **`api.ts` 401 → logout silenzioso**: a differenza di quanto scritto in AGENTS.md, `request()` chiama `notifySessionExpired()` (`:151-154`) che esegue `auth.logout()` silenzioso + toast "Sessione scaduta". Comportamento corretto, ma `logout()` richiama `/api/v1/auth/logout` con token già cancellato (no-op). Aggiornare AGENTS.md.
23. **`auth.ts:85` `tenant_id` impostato a `data.id`** — possibile bug: il tenant diventa l'id utente. Verificare semantics multi-tenant.
24. **Fragilità test i18n** — componenti renderizzano la *chiave* (`heatmap.load`, `maps.routeMaps`); i test asseriscono sulle chiavi (ok) ma è fragilissimo. Introdurre un mock i18n con dizionario EN condiviso per asserire sul testo reale.
25. **SW cache `/api` stale** — già noto (AGENTS.md): prevedere invalidazione cache per le rides.

### 2.6 QUALITY / BUILD / CI
26. **CI frontend non esegue test/typecheck/lint** — `.github` `ci.yml` job frontend lancia solo `npm run build`. I fallimenti frontend noti (es. transient `router/index.test.js`) passano inosservati. **Aggiungere step `vitest` + `typecheck` + `eslint`.**
27. **`typescript ^6.0.3` + `vue-tsc ^2.2.12`** — combo rischioso per `npm run typecheck`. Pin TS 5.6/5.7.
28. **Drift dipendenze backend** — `requirements.txt` ha `google-auth`, `sentence-transformers`, `pytest-asyncio` non in `pyproject.toml`. Riconciliare.
29. **`prebuild.mjs` senza `-ErrorAction Stop`** — swalla i fallimenti (AGENTS.md chiede il flag). Su agent senza admin il retry è l'unica rete.
30. **Alembic**: migrations orphaned `__pycache__` (tenant). Verificare single head con `alembic check`.
31. **`mypy`** disabilita ~20 error code + `ignore_missing_imports` → basso segnale. Stringere progressivamente.

---

## 3. Azioni prioritarie (ordine consigliato)

1. **Sicurezza OAuth (P1):** whitelist redirect statica + gating `/sentry-debug` + `refresh_token` con fallback decoder. (§2.1.1, 2.1.4, 2.1.3)
2. **Revoca token coerente (P1):** behaviour `revoke_token`/`is_token_revoked` con Redis assente; Redis obbligatorio in prod. (§2.1.2)
3. **Data layer Postgres/async (P1):** creare `backend/db/models.py` (o puntare ai modelli esistenti) e implementare `get_session_factory`/`get_rides_by_athlete_async` reali; altrimenti disabilitare il path async in prod finché non funzionante. (§2.2.8, 2.2.9)
4. **Validazione import + HTTP async (P2):** validare payload GPX/FIT; `httpx`/backoff; `asyncio.to_thread` per matplotlib. (§2.3.12, 2.2.11, 2.3.13)
5. **Consolidamento duplicati (P2):** modelli dominio unici; una sola impl TSS/ATL-CTL-TSB; allineare EMBEDDING_DIMENSION. (§2.2.10, 2.4.16, 2.3.15)
6. **Performance DB (P2):** LIMIT/OFFSET reale, index composito `(athlete_id,date)`. (§2.3.14, 2.4.19)
7. **CI/quality (P2):** vitest+typecheck+lint nel job frontend CI; pin TS 5.x; unifica dipendenze; `-ErrorAction Stop` in prebuild. (§2.6.26–29)
8. **Pulizia (P3):** dead code routes, Google Fit deprecato, aggiorna AGENTS.md (§2.5.22, 2.4.17/18, 2.1.7), mypy più stretto.

---

## 4. Validazione
- **Security:** test su `_validate_redirect_uri` con `Origin` spoofato (deve rifiutare); test revoca con Redis mock `None`.
- **Data layer:** `pytest tests/test_db*.py` dopo fix; avvio con `DATABASE_URL` settato per confermare nessun `ImportError`.
- **Frontend:** `cd frontend && npx vitest run && npm run typecheck && npm run lint`; run completa CI verde.
- **Backend:** `pytest -q` (target 0 failed); `alembic check` single head.

## 5. Open questions
- Il path async/Postgres è intenzionalmente work-in-progress o dovrebbe funzionare in prod oggi? (decide se "fix" o "disabilita").
- Multi-tenant reale? (`tenant_id` in `auth.ts:85` suggerisce possibile confusione).
- `revoke_token` debe essere "best-effort success" (current) o "fail loud" in degraded mode?
