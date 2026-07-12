# Repository Structure

```
frontend/                 # App Vue 3 (src/, public/, tests)
  src/
    main.ts               # bootstrap: Pinia, router, SW register, OAuth token da URL
    App.vue               # shell + overlay oauthLoading + LoginForm
    router/index.ts       # guard auth, sync localStorage, redirect post-login
    stores/auth.ts        # JWT in localStorage, isTokenValid(), login/register/logout
    stores/ui.ts          # tema, lingua, oauthLoading
    utils/api.ts          # wrapper fetch (apiGet/Post/Put/Delete/Upload) + clearAuth
    components/           # pannelli (RidesPanel, ImportPanel, AthletePanel, ...)
    views/                # RidesView, RideTracking, pagine legali
    composables/          # useRides, useToast, usePWA, useI18n, useChart
bike_analyzer/
  backend/
    api/routes.py         # tutte le route FastAPI (auth, rides, import, health)
    api/app_factory.py    # creazione app, mount router, middleware
    auth/                 # login, JWT, google oauth
    security.py           # OAuth2 scheme, cookie refresh
    rate_limiter.py       # rate limiting (esistente, da cablare su login/register)
    monitoring.py         # health checks DB/Redis/task queue
  core/                   # motore analisi (engine, pipeline, calculators)
  frontend/dashboard.py   # dashboard server-side (non l'app Vue)
tests/                    # test Python (pytest) backend
aethermap/                # Progetto R&D separato (motore cartografico) — vedi sotto
```

## AetherMap (R&D)

Vedi [aethermap.md](./aethermap.md).

## BikeMaster 2.0 (BM2)

Vedi [bm2.md](./bm2.md).
