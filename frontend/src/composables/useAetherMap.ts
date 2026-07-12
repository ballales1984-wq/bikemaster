import { ref, watch, type Ref } from "vue";
import { apiGet } from "../utils/api";

export interface AetherEntity {
  tipo: string;
  pts: number[][];
  char: string;
}

export interface AetherScene {
  engine: string;
  entities: AetherEntity[];
  statistics?: Record<string, number>;
}

export interface AetherMapState {
  scene: Ref<AetherScene | null>;
  loading: Ref<boolean>;
  error: Ref<string | null>;
  reload: () => void;
}

export function hexToRgb(hex: string): [number, number, number] {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
  if (!m) return [0.4, 0.53, 1.0];
  const n = parseInt(m[1], 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

export function useAetherMap(rideIds: Ref<number[]>): AetherMapState {
  const scene = ref<AetherScene | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function load(): Promise<void> {
    const ids = rideIds.value;
    if (!ids.length) {
      scene.value = null;
      error.value = null;
      loading.value = false;
      return;
    }
    loading.value = true;
    error.value = null;
    const entities: AetherEntity[] = [];
    let statistics: Record<string, number> | undefined;
    const errors: string[] = [];
    await Promise.all(
      ids.map(async (id) => {
        try {
          const meta = await apiGet<{ map_url: string; engine: string }>(
            `/rides/${id}/map`,
            { provider: "aethermap" },
            { suppressAuthClear: true },
          );
          if (meta.engine !== "aethermap" || !meta.map_url) return;
          const s = await apiGet<AetherScene>(
            meta.map_url,
            {},
            { suppressAuthClear: true },
          );
          if (s.entities?.length) entities.push(...s.entities);
          if (s.statistics) statistics = s.statistics;
        } catch (e) {
          errors.push(e instanceof Error ? e.message : String(e));
        }
      }),
    );
    loading.value = false;
    if (errors.length && entities.length === 0) {
      error.value = errors[0];
      scene.value = null;
      return;
    }
    scene.value = { engine: "aethermap", entities, statistics };
  }

  watch(rideIds, () => void load(), { immediate: true });

  return { scene, loading, error, reload: () => void load() };
}
