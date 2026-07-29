/**
 * Composable to load terrain enrichment data for a ride.
 * Fetches /api/v1/rides/{rideId}/terrain?enabled=true and exposes
 * enriched GPS points plus terrain metadata.
 */
import { ref, watch, type Ref } from "vue";
import { apiGet } from "../utils/api";

export interface TerrainEnrichedPoint {
  lat: number;
  lon: number;
  timestamp: string | null;
  altitude: number | null;
  speed: number | null;
  power: number | null;
  heart_rate: number | null;
  cadence: number | null;
  slope_pct: number;
  surface_type: string;
  shade: boolean;
  traffic_level: number;
  terrain_confidence: number;
}

export interface TerrainFeature {
  id: string;
  tipo: string;
  [key: string]: any;
}

export interface TerrainSummary {
  ride_id: number;
  enriched: TerrainEnrichedPoint[];
  terrain_features: TerrainFeature[];
  h3_summary: Record<string, Record<string, number>>;
}

export interface RideTerrainState {
  data: Ref<TerrainSummary | null>;
  loading: Ref<boolean>;
  error: Ref<string | null>;
  reload: () => void;
}

export function useRideTerrain(rideId: Ref<number | null>): RideTerrainState {
  const data = ref<TerrainSummary | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function load(): Promise<void> {
    const rid = rideId.value;
    if (!rid || rid <= 0) {
      data.value = null;
      error.value = null;
      loading.value = false;
      return;
    }
    loading.value = true;
    error.value = null;
    try {
      const summary = await apiGet<TerrainSummary>(
        `/api/v1/rides/${rid}/terrain`,
        { enabled: "true" },
        { suppressAuthClear: true },
      );
      data.value = summary;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
      data.value = null;
    } finally {
      loading.value = false;
    }
  }

  watch(rideId, () => void load(), { immediate: true });

  return { data, loading, error, reload: () => void load() };
}
