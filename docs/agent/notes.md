# Notes

- Non introdurre dipendenze non presenti in `package.json` / `requirements` senza verificarle prima.
- I test Python sono numerosi (`tests/test_*.py`); eseguire `pytest` prima di modifiche backend ampie.
- Il service worker (`sw.js`) usa caching su `/api`: attenzione a dati stale sulle rides; prevedere invalidazione cache (SKIP_WAITING già gestito in main.ts:46).
- `RidesPanel.vue` ha export CSV; `ImportPanel.vue` gestisce import (Strava/Garmin/Google Fit). La UI Strava è già cablata in `ImportPanel.vue` (pulsanti *Connect/Import/Disconnect Strava*, gated su `providers.strava`): il flusso apre un popup OAuth2+PKCE, legge `?code=` dal redirect e POSTa `{code, code_verifier}` a `POST /api/v1/import/strava/callback`. Non ricreare questo flusso. Endpoint backend: `GET /import/strava/auth`, `POST /import/strava/callback`, `POST /import/strava/sync`, `DELETE /import/strava/disconnect`. `STRAVA_REDIRECT_URI` deve puntare a `.../api/v1/import/strava/callback` (path `/import/`, non `/auth/`).
