/**
 * Composable to load AetherMap map scenes for a list of rides.
 * For each ride it fetches the AetherMap map URL and aggregates the entities
 * and statistics into a single scene, reloading when `rideIds` change.
 * Exposes the reactive states `scene`, `loading`, `error` and the `reload` action.
 */
import { ref, watch, type Ref } from "vue";
import { apiGet } from "../utils/api";

export interface AetherEntity {
  tipo: string;
  pts: number[][];
  char: string;
  colors?: string[];
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

interface GeoJSONLike {
  type: string;
  features?: Array<{
    type: string;
    properties?: Record<string, any>;
    geometry?: {
      type: string;
      coordinates?: any[];
    };
  }>;
  metadata?: Record<string, any>;
}

function featureToEntity(
  feature: NonNullable<GeoJSONLike["features"]>[number],
): AetherEntity | null {
  const props = feature.properties || {};
  const tipo = props.tipo;
  if (!tipo) return null;

  const prop = props.proprieta || {};
  const colors: string[] | undefined =
    prop.colors && Array.isArray(prop.colors) ? prop.colors : undefined;
  const char =
    typeof prop.color === "string"
      ? prop.color
      : typeof prop.char === "string"
        ? prop.char
        : typeof props.char === "string"
          ? props.char
          : "#FF6B00";
  const geom = feature.geometry;
  if (!geom) return { tipo, pts: [], char, colors };

  let coords: number[][] = [];
  if (geom.type === "LineString") {
    coords = geom.coordinates as number[][];
  } else if (geom.type === "Point") {
    coords = [geom.coordinates as number[]];
  } else {
    return null;
  }

  const pts = coords.map((c) => {
    if (Array.isArray(c) && c.length >= 2) {
      return [c[1], c[0], c[2] ?? 0];
    }
    return [0, 0, 0];
  });

  return { tipo, pts, char, colors };
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
            `/api/v1/rides/${id}/map`,
            { provider: "aethermap" },
            { suppressAuthClear: true },
          );
          if (meta.engine !== "aethermap" || !meta.map_url) return;
          const raw = await apiGet<GeoJSONLike | AetherScene>(
            meta.map_url,
            {},
            { suppressAuthClear: true },
          );
          if ((raw as GeoJSONLike).type === "FeatureCollection") {
            const fc = raw as GeoJSONLike;
            for (const feature of fc.features || []) {
              const ent = featureToEntity(feature);
              if (ent) entities.push(ent);
            }
            const md = (fc as any).metadata;
            if (md?.statistics) statistics = md.statistics;
          } else {
            const legacy = raw as AetherScene;
            if (legacy.entities?.length) entities.push(...legacy.entities);
            if (legacy.statistics) statistics = legacy.statistics;
          }
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
