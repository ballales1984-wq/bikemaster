# Commands

## Frontend

```bash
cd frontend
npm install
npm run dev          # vite dev server
npm run build        # vite build  (ATTENZIONE: vedi ../build.md)
npm run typecheck    # vue-tsc --noEmit --incremental
npm run lint         # eslint --fix
npm run test         # vitest unit
npm run e2e          # playwright test (config: playwright.config.js)
npm run e2e:local    # playwright --config playwright.local.config.js
```

- Config Vitest: `frontend/vitest.config.js`. Test unit esistenti in `frontend/src/stores/auth.test.ts`, `ui` test, `trackingStore.test.ts`.
- **NON esiste** `playwright.prod.config.js` né `frontend/tests/e2e`: i test E2E stanno in `frontend/tests/` con `playwright.config.js`. Se serve un config "prod", crearlo a partire da quello esistente.

## Backend

```bash
pip install -e .            # o via .venv
pytest                      # test Python (tests/)
```

- Health endpoints (già presenti in `bike_analyzer/backend/api/routes.py`):
  - `GET /api/v1/health` (routes.py:261)
  - `GET /api/v1/health/redis` (routes.py:280)
  - `GET /api/v1/health/detailed` (routes.py:952)
  - Esclusi dal tracing: `/metrics`, `/health` (app_factory.py:90).
  **Nota**: il path è `/api/v1/health`, non `/health` nudo.
