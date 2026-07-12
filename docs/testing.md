# Testing

## Backend

- **97 pytest files** covering unit, integration, API, and error paths
- Run: `pytest` or `pytest --cov=bike_analyzer --cov-report=term`
- Frameworks: pytest, pytest-asyncio, pytest-cov

## Frontend

- **Vitest**: `cd frontend && npm run test` (321 tests)
- **Playwright**: `npm run test:e2e` or `npm run e2e:local`
- Frameworks: Vitest, @vue/test-utils, Playwright

## Key Test Modules

- Core models, pipeline, engine, fitness state
- Analytics calculators (100% coverage)
- Power model, fatigue, performance, stress
- AI Coach API, knowledge base API
- Strava/Garmin/Google Fit integrations
- Security, rate limiting, event bus
- Traffic safety, weather, anomaly detection
- Frontend: auth, routing, API client, components

## Coverage Notes

- Coverage threshold removed from pytest config (informational only)
- Backend: `pytest --cov=bike_analyzer --cov-report=term`
- Frontend: `npx vitest run --coverage`
