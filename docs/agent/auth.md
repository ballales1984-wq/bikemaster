# Auth & OAuth

## Token storage

- Il JWT è letto/scritto da **`localStorage`** (chiave `bikemaster_token`, `bikemaster_user`, `bikemaster_just_logged_in`).
- `utils/api.ts` `request()` su 401 (senza `suppressAuthClear`) chiama `clearAuth()` (rimuove le chiavi localStorage), lancia `ApiError("expired", 401)` e, tramite `notifySessionExpired()`, mostra il toast "Sessione scaduta" ed esegue un **logout silenzioso** nello store (`auth.logout()`). `logout()` richiama anche `POST /api/v1/auth/logout` (no-op perché il token è già stato cancellato). Nota: il logout silenzioso è già implementato.

## Flusso login

1. `auth.login()` (stores/auth.ts:63) chiama `POST /api/v1/auth/login` (form-urlencoded) e salva token+user in localStorage.
2. `App.vue` `onLogin` fa `router.push('/rides')`.
3. Per OAuth (Google), il backend redirige al frontend con `?token=...&email=...` (o `#token=...`). `main.ts` (righe 19-31) legge il token dall'URL e chiama `auth.setAuthFromUrl()`, poi `history.replaceState` per pulire l'URL. In caso di errore: `?oauth_error=...` → `auth.setOauthError()`.

## Guard del router (router/index.ts)

Il `beforeEach` sincronizza lo stato Pinia da localStorage **prima** di valutare l'auth, perché `main.ts` può impostare il token prima che il guard parta. Punti critici da NON rompere:
- Sync `auth.token` / `auth.user` da localStorage (righe 160-174).
- Invalidazione token scaduto (righe 176-182) → pulisce localStorage.
- Gestione token OAuth da hash/query (righe 185-204) → chiama `ui.setOauthLoading(false)`.
- Redirect post-login: se `hasToken && (to.path === '/' || justLoggedIn)` → `checkProfileComplete()` → `/rides` se profilo completo, altrimenti `/athlete` (righe 221-229). `checkProfileComplete` chiama `GET /api/v1/auth/me`.
- **Pulire `bikemaster_just_logged_in` DOPO `next()`** (righe 225-226), altrimenti `App.vue` non renderizza la dashboard.
- Alla fine del flusso OAuth imposta sempre `ui.setOauthLoading(false)`.

## Strava OAuth2 + PKCE

- Il flusso apre un popup OAuth2+PKCE, legge `?code=` dal redirect e POSTa `{code, code_verifier}` a `POST /api/v1/import/strava/callback`.
- Endpoint backend: `GET /import/strava/auth`, `POST /import/strava/callback`, `POST /import/strava/sync`, `DELETE /import/strava/disconnect`.
- `STRAVA_REDIRECT_URI` deve puntare a `.../api/v1/import/strava/callback` (path `/import/`, non `/auth/`).
