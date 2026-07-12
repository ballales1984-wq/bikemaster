# AetherMap

## Progetto AetherMap (R&D, separato)

`aethermap/` è un progetto di ricerca/distribuzione **indipendente** da BikeMaster (motore cartografico "dal nulla": cube-sphere + S2/H3, data model, pipeline IA "ricercatore", rendering WebGL, digital twin). Condivide solo lo stack (Vue + FastAPI) ma **non** è importato dal backend/da BikeMaster.

- Codice: `aethermap/src/aethermap/` (`core/`, `ai/`, `data/`, `render/`, `twin/`), demo via `cd aethermap/src && python -m aethermap.ai.demo|.render.demo|.twin.demo`.
- Agenti dedicati: `.kilo/agent/aethermap-*.md` (lead, earth-model, data-model, ai, ml, gis, graphics, rendering, digital-twin).
- Fasi: 1→2→{3,4}→5 (vedi `aethermap/docs/phase-*.md`). Tracciato in git; non rimuovere senza consenso esplicito.
