# Stack

## Frontend

- **Framework**: Vue 3 + Pinia + Vue Router 4 + Vite 5 + TypeScript (`vue-tsc`)
- **PWA**: `vite-plugin-pwa` (`sw.js` custom in `frontend/src/sw.js`)
- **Test**: Vitest (unit) + Playwright (E2E)
- **Lint**: ESLint + vue-tsc

## Backend

- **Framework**: FastAPI (Python) in `bike_analyzer/backend/`, esposto con prefisso `/api/v1` (vedi `bike_analyzer/backend/api/app_factory.py:202`)
- **Database**: SQLite (dev) + PostgreSQL (prod) + SQLAlchemy 2.0 + Alembic
- **Auth**: python-jose, passlib, bcrypt, OAuth2 (Google, Strava, Garmin)
- **AI**: Groq SDK + sentence-transformers (local embeddings) + RAG (BM25 + PGVector)
- **Cache**: Redis 7 (optional, graceful fallback)
- **Observability**: Sentry, Prometheus, Grafana, OpenTelemetry/Zipkin

## Deploy

- **Render** via Docker (vedi `Dockerfile`/`render.yaml` a root o `docker/`)

## Altro

- Capacitor (Android + iOS)
- Prometheus/Grafana (`prometheus/`, `docker/grafana/`)
- Alembic per le migration DB
