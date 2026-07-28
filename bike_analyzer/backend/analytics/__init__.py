"""Analytics package.

Subpackages:
    terrain_enrichment: Terrain enrichment via AetherMap pipeline.
    terrain_twin: Digital twin module for ride context analysis.
"""
from __future__ import annotations

from .terrain_enrichment import EnrichedGPSPoint, TerrainEnricher
from .terrain_twin import RideContext, SurfaceProfile, TerrainTwin