# Backend Architecture Contracts

## Layer boundaries

- `db/`
  - Owns SQLite schema, SQLAlchemy models, repositories, and DB utilities.
  - Must not import from `api/` or `analytics/`.
  - Exposes only database-facing functions/classes (`save_ride`, `get_athlete`, etc.).

- `api/`
  - Owns FastAPI routes, request/response schemas, middleware, auth, and app factory.
  - Depends on `db/` for persistence and `analytics/` for domain logic.
  - Must not bypass `db/` with inline SQL when a repository exists.

- `analytics/`
  - Owns AI Coach, BM2 engine, training plans, knowledge base, and business rules.
  - Depends on `db/` for data access, but must not know FastAPI or HTTP details.
  - Exposes plain functions/classes (`generate_training_advice`, `AIOrchestrator`, etc.).

- `monitoring/`, `logging_config/`, `settings/`
  - Cross-cutting concerns used by all layers.
  - Must stay framework-agnostic where possible.

## Data flow (request path)

1. HTTP request → `api/app_factory.py` (middleware, CORS, rate limit, auth).
2. Route handler in `api/routes.py` validates input via `schemas.py`.
3. Handler calls `db/database.py` or a repository for persistence.
4. If business logic is needed, handler calls `analytics/` modules.
5. Response is returned as JSON; errors are normalized by exception handlers.

## Rules

- No circular imports across layers.
- No direct `sqlite3` usage in `api/` or `analytics/` — always use `db/database.py` or repositories.
- External secrets are read from `settings.py` or environment variables, never hardcoded.
- All user-facing errors return structured JSON with `detail` field.
- Health checks live in `monitoring.py` and are aggregated by `/health/comprehensive`.
- DB exceptions are wrapped by global exception handlers in `api/app_factory.py` (`sqlite3.IntegrityError` → 409, `ValueError` → 400).
- No PII in logs: use redaction rules in `logging_config.py`.
- `analytics/` must not import `api/` or FastAPI types. If it needs HTTP, use plain functions from `settings/` or stdlib.

## Data contracts

- Repository functions return plain `dict` or Pydantic models, never raw tuples/cursors outside `db/`.
- `api/schemas.py` is the single source of truth for request/response shapes.
- `analytics/` functions receive domain models (e.g. `AthleteProfile`, `Ride`) or plain dicts, never SQLAlchemy ORM objects.
- Errors propagate as Python exceptions up to `api/`; `analytics/` must not catch and swallow silently.

## Repository pattern

- Preferred path: `api/routes.py` → `db/repositories/*` → `db/database.py`.
- Inline `db.database` calls are allowed only when no repository exists yet.
- New endpoints must use repositories from day one.

## Logging

- Use `logging_config.py` everywhere. Do not use `print()` in backend code.
- In production, logs must be JSON with `timestamp`, `level`, `logger`, `message`, and optional extras (`user_id`, `request_id`, `tenant_id`).
- Never log raw secrets/tokens. Redaction rules are centralized.

## Testing

- Unit tests mirror the layer structure under `tests/`.
- Integration tests use `TestClient` against `create_app()` with a temporary SQLite DB.
- Flaky or external-dependency tests must be marked `missing_greenlet` or `slow`.
- Every new error handler or health check must have at least one test in `tests/test_error_branches.py` or `tests/test_monitoring.py`.
