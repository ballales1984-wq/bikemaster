# AGENTS.md — BikeMaster

BikeMaster is a GPS-based cycling performance intelligence system (FastAPI + Vue 3 + TypeScript) with a BikeMaster 2.0 simulation engine and an independent AetherMap R&D cartography project.

## Quick Reference

- **Backend tests:** `pytest` (from repo root)
- **Frontend tests:** `cd frontend && npm run test`
- **Lint/typecheck:** `cd frontend && npm run lint && npm run typecheck`
- **Build frontend:** `cd frontend && npm run build`

## Universal Rules

- Do not introduce new dependencies without verifying they are already in `package.json` / `requirements`.
- Never commit secrets or API keys.
- Run relevant tests before considering a task complete.
- For detailed instructions, see [docs/agent/README.md](./agent/README.md).
