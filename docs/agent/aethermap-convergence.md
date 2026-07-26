# AetherMap Convergence Decision

**Decision date**: 2026-07-26
**Status**: CONFIRMED — AetherMap converges into BikeMaster
**Decision maker**: Product/Architecture decision ( documented per ROADMAP.md Phase 5, item 17 )

## Background

AetherMap (`aethermap/`) has been developed as an independent R&D cartography project alongside BikeMaster since Phase 1 (earth model). As of this decision, Phases 1-5 are complete:

- **Phase 1**: Cube-sphere earth model + S2/H3 coordinate system
- **Phase 2**: Data model (Oggetto with temporal state) + GeoJSON/Parquet I/O
- **Phase 3**: AI pipeline ("Ricercatore") — ingest → researcher → proposals → pipeline → world
- **Phase 4**: WebGL2 rendering with cube-sphere viewer, S2 grid overlay, entity LOD
- **Phase 5**: Digital Twin — live objects (Strada, Albero, Montagna) + SVO + Environment-driven state

All 129 tests pass across `test_ai.py` and `test_twin.py`.

The `docs/agent/aethermap.md` previously described AetherMap as "progetto di ricerca/distribuzione **indipendente** da BikeMaster (non importato dal backend/da BikeMaster)". This is now outdated. The integration contract (`aethermap/docs/integration-contract.md`) already existed with runtime integration via adapter pattern.

## Decision: CONVERGENCE

**AetherMap converges into BikeMaster as the terrain intelligence module.**

### Rationale

1. **Shared stack**: Both projects use Vue 3 + FastAPI + Python. No cross-language barrier.
2. **Complementary domains**: BikeMaster is cycling health intelligence; AetherMap provides terrain/cartography intelligence. Together they form a complete "ride context" system.
3. **Integration already exists**: The adapter pattern (`aethermap_adapter.py`) and feature flags (`BIKEMASTER_MAP_PROVIDER`, `VITE_AETHERMAP_ENABLED`) are already in place. Convergence formalizes what is already functional.
4. **Digital Twin value for cyclists**: The digital twin provides terrain context (elevation, slope, surface, shade, snow) that directly enriches ride analysis and AI coaching.
5. **AI pipeline enriches rides**: The researcher pipeline can propose terrain features from GPX data (road identification, traffic prediction, surface classification).
6. **Single product identity**: Maintaining separate distribution for a tightly integrated module adds unnecessary complexity for users and CI/CD.

### What Converges

| AetherMap component | BikeMaster integration point |
|---|---|
| `aethermap.core.coordinates` | `bike_analyzer/core/` — shared coordinate conversion |
| `aethermap.ai.pipeline` | `bike_analyzer/analytics/` — terrain enrichment pipeline |
| `aethermap.ai.researcher` | `bike_analyzer/analytics/` — GPX → terrain feature proposals |
| `aethermap.ai.models_ml` | `bike_analyzer/analytics/` — road plausibility + NN models |
| `aethermap.twin` | `bike_analyzer/analytics/terrain_twin/` — digital twin for ride context |
| `aethermap.render` | `frontend/src/components/` — WebGL2 terrain viewer |
| `aethermap.data` | `bike_analyzer/backend/` — GeoJSON/Parquet I/O for ride data |

### What Stays Independent

- AetherMap's standalone demo/documentation remains accessible for R&D purposes
- `aethermap/` directory is preserved as the canonical source of the terrain engine code
- The `pyproject.toml` in `aethermap/` is maintained; the package is installed as a dependency of `bike_analyzer` via `pip install -e ".[maps]"`

## Data Contract: Ride/GPSPoint → Terrain Input

### Contract Definition

```
+------------------+       +------------------------+       +-------------------+
| BikeMaster Ride   |------>| Terrain Enrichment     |------>| AetherMap Engine  |
| GPSPoint[]        |       | Adapter                |       | Digital Twin      |
+------------------+       +------------------------+       +-------------------+
```

**Input**: `Ride` object with `GPSPoint[]` (lat, lon, ele, time) from `bike_analyzer/core/models.py`

**Output**: Enriched `GPSPoint[]` with terrain attributes:
- `slope_pct`: slope percentage at point
- `surface_type`: road surface classification
- `shade`: whether point is in shadow (solar elevation dependent)
- `traffic_level`: estimated traffic density
- `terrain_confidence`: confidence score from ML model

### Interface

```python
# In bike_analyzer/analytics/terrain_enrichment.py

from aethermap.ai.pipeline import Pipeline, WorldStore
from aethermap.ai.ingest import ingest_gpx
from aethermap.twin.world import DigitalTwin, Environment

class TerrainEnricher:
    def __init__(self) -> None:
        self.store = WorldStore()
        self.pipeline = Pipeline(self.store)
        self.twin = DigitalTwin()

    def enrich_ride(self, points: list[GPSPoint]) -> list[EnrichedGPSPoint]:
        """Enrich GPS points with terrain data from AetherMap engine."""
        # 1. Research terrain features from GPX
        raw_points = [RawPoint(lat=p.lat, lon=p.lon, ele=p.ele) for p in points]
        proposals = self.pipeline.research_gpx(raw_points)
        for p in proposals:
            self.pipeline.submit(p)
        self.pipeline.flush()

        # 2. Apply environment to digital twin
        env = Environment(temp_c=15.0, solar_elev_deg=45.0, ora="12:00")
        self.twin.step(env)

        # 3. Produce enriched points with terrain attributes
        return self._build_enriched(points, self.twin.snapshot())
```

### Feature Flag

- Backend: `BIKEMASTER_TERRAIN_ENRICHMENT=true` (default: `false`)
- Frontend: `VITE_TERRAIN_ENRICHMENT_ENABLED=true` (default: `false`)

### Backward Compatibility

When disabled, rides are processed exactly as before. No breaking changes to existing APIs or data models.

## References

- ROADMAP.md Phase 5 items 16-18
- `aethermap/docs/integration-contract.md` — existing integration contract
- `aethermap/docs/phase-3-ai-researcher.md` — AI pipeline design doc
- `aethermap/docs/phase-5-digital-twin.md` — digital twin design doc
- `aethermap/README.md` — AetherMap project overview
