# AetherMap

## AetherMap — Terrain Intelligence Module (converged into BikeMaster)

`aethermap/` è ora un modulo di BikeMaster per l'intelligenza del terreno (terrain intelligence). Il progetto è stato fuso nel prodotto come dipendenza opzionale.

- **Stato**: Fasi 1-5 complete. Convergence decision: `aethermap/` converges into BikeMaster.
- **Codice**: `aethermap/src/aethermap/` (`core/`, `ai/`, `data/`, `render/`, `twin/`), demo via `cd aethermap/src && python -m aethermap.ai.demo|.render.demo|.twin.demo`.
- **Integrazione**: Adapter in `bike_analyzer/backend/maps/aethermap_adapter.py`. Feature flag `BIKEMASTER_MAP_PROVIDER=aethermap` / `VITE_AETHERMAP_ENABLED=true`. Installazione: `pip install -e ".[maps]"`.
- **Contratto dati**: `Ride/GPSPoint → terrain input` definito in `docs/agent/aethermap-convergence.md`.
- **Agenti dedicati**: `.kilo/agent/aethermap-*.md` (lead, earth-model, data-model, ai, ml, gis, graphics, rendering, digital-twin).
- **Fasi**: 1→2→3→4→5 (vedi `aethermap/docs/phase-*.md`). Tracciato in git; non rimuovere senza consenso esplicito.
