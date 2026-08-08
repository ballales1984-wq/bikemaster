/**
 * Composable to load terrain enrichment data for a ride from the backend.
 *
 * Fetches `/api/v1/rides/{rideId}/terrain` and exposes enriched GPS points
 * with slope_pct, surface_type, shade, traffic_level, terrain_confidence.
 */
import { ref, computed, watch, type Ref } from "vue";
import { apiGet } from "../utils/api";

export interface TerrainEnrichedPoint {
  lat: number;
  lon: number;
  timestamp?: string;
  altitude?: number;
  speed?: number;
  power?: number;
  heart_rate?: number;
  cadence?: number;
  slope_pct: number;
  surface_type: string;
  shade: boolean | null;
  traffic_level: number;
  terrain_confidence: number;
}

export interface TerrainEnrichmentData {
  ride_id: number;
  enriched: TerrainEnrichedPoint[];
  terrain_features: Array<Record<string, any>>;
  h3_summary: Record<string, Record<string, number>>;
}

export function useAetherMapTerrain(rideId: Ref<number | null>, enabled: Ref<boolean>) {
  const data = ref<TerrainEnrichmentData | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const abortCtrl = ref<AbortController | null>(null);
  let debounceTimer: number | null = null;

  async function load(): Promise<void> {
    abortCtrl.value?.abort();
    const ctrl = new AbortController();
    abortCtrl.value = ctrl;

    const rid = rideId.value;
    if (!rid || !enabled.value) {
      data.value = null;
      return;
    }
    loading.value = true;
    error.value = null;
    try {
      const res = await apiGet<TerrainEnrichmentData>(
        `/api/v1/rides/${rid}/terrain`,
        { enabled: "true" },
        { signal: ctrl.signal },
      );
      if (ctrl.signal.aborted) return;
      data.value = res;
    } catch (e) {
      if (ctrl.signal.aborted) return;
      error.value = e instanceof Error ? e.message : String(e);
      data.value = null;
    } finally {
      if (!ctrl.signal.aborted) loading.value = false;
    }
  }

  watch([rideId, enabled], () => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => void load(), 300);
  }, { immediate: false });

  const points = computed(() => data.value?.enriched ?? []);
  const features = computed(() => data.value?.terrain_features ?? []);
  const h3Summary = computed(() => data.value?.h3_summary ?? {});

  return {
    data,
    loading,
    error,
    points,
    features,
    h3Summary,
    reload: () => void load(),
  };
}
