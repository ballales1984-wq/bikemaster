# AGENTS.md — BikeMaster

BikeMaster is a GPS-based cycling performance intelligence system (FastAPI + Vue 3 + TypeScript) with a BikeMaster 2.0 simulation engine and an independent AetherMap R&D cartography project.

## Architecture (local-first, effective 2026-07-15)

- **Primary platform**: Tauri 2 desktop app (Rust + WebView) — native `.exe`/`.dmg`/`.AppImage`.
- **Frontend**: Vue 3 + Vite + TypeScript, bundled inside Tauri WebView.
- **Backend**: FastAPI (Python) or Rust Axum embedded in the Tauri app; runs on `localhost` inside the user's device.
- **Database**: SQLite (local file on disk) is the primary store for every user. PostgreSQL is optional/cloud-only for sync and community features.
- **Sync**: optional, user-controlled bidirectional sync with a cloud PostgreSQL instance. Users can run "Mai" (never sync) and use the app 100% offline.
- **PWA**: still supported for web-only users, but desktop (Tauri) is the reference distribution.
- **AetherMap**: independent R&D cartography project (`aethermap/`), separate from BikeMaster product.

## Quick Reference

- **Backend tests:** `pytest` (from repo root)
- **Frontend tests:** `cd frontend && npm run test`
- **Lint/typecheck:** `cd frontend && npm run lint && npm run typecheck`
- **Build frontend:** `cd frontend && npm run build`
- **Tauri build:** `cd frontend && npm run tauri build` (or equivalent Cargo command)
- **Simulator:** `cd bike_analyzer && python -m bm2.simulation.demo`

## Universal Rules

- Do not introduce new dependencies without verifying they are already in `package.json` / `requirements`.
- Never commit secrets or API keys.
- Run relevant tests before considering a task complete.
- For detailed instructions, see [docs/agent/README.md](./agent/README.md).
