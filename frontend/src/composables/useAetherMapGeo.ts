/**
 * Composable to load AetherMap geographic layers (roads, cities, peaks)
 * from the backend GeoJSON endpoints.
 */
import { ref, computed } from "vue";
import { apiGet } from "../utils/api";

export interface GeoFeature {
  type: "Feature";
  properties: Record<string, unknown>;
  geometry: {
    type: string;
    coordinates: GeoCoord | GeoLineCoords | GeoCoord[][] | unknown;
  };
}

export type GeoCoord = [number, number] | [number, number, number];
export type GeoLineCoords = GeoCoord[];
export type GeoCoordinates = GeoCoord | GeoLineCoords;

export interface GeoJSON {
  type: "FeatureCollection";
  features: GeoFeature[];
}

export interface GeoLayer {
  id: string;
  name: string;
  type: "roads" | "cities" | "peaks";
  data: GeoJSON | null;
  loading: boolean;
  error: string | null;
  visible: boolean;
  color: string;
}

export function useAetherMapGeo() {
  const layers = ref<Map<string, GeoLayer>>(new Map());

  const visibleLayers = computed(() =>
    Array.from(layers.value.values()).filter((l) => l.visible && l.data),
  );

  function getLayer(id: string): GeoLayer | undefined {
    return layers.value.get(id);
  }

  async function loadLayer(
    id: string,
    type: GeoLayer["type"],
    params: Record<string, string | number | boolean>,
  ): Promise<void> {
    const existing = layers.value.get(id);
    if (existing) {
      existing.loading = true;
      existing.error = null;
    } else {
      const color =
        type === "roads"
          ? "#f2c738"
          : type === "cities"
            ? "#47eb6b"
            : "#eb5247";
      layers.value.set(id, {
        id,
        name: layerName(type),
        type,
        data: null,
        loading: true,
        error: null,
        visible: true,
        color,
      });
    }

    const path =
      type === "roads"
        ? "/aethermap/geo/roads"
        : type === "cities"
          ? "/aethermap/geo/cities"
          : "/aethermap/geo/peaks";

    try {
      const stringParams: Record<string, string> = {};
      for (const [k, v] of Object.entries(params)) {
        stringParams[k] = String(v);
      }
      const data = await apiGet<GeoJSON>(path, stringParams);
      const layer = layers.value.get(id);
      if (layer) {
        layer.data = data;
        layer.loading = false;
      }
    } catch (e) {
      const layer = layers.value.get(id);
      if (layer) {
        layer.error = e instanceof Error ? e.message : String(e);
        layer.loading = false;
      }
    }
  }

  function toggleLayer(id: string): void {
    const layer = layers.value.get(id);
    if (layer) {
      layer.visible = !layer.visible;
    }
  }

  function removeLayer(id: string): void {
    layers.value.delete(id);
  }

  function clearLayers(): void {
    layers.value.clear();
  }

  return {
    layers,
    visibleLayers,
    getLayer,
    loadLayer,
    toggleLayer,
    removeLayer,
    clearLayers,
  };
}

function layerName(type: GeoLayer["type"]): string {
  switch (type) {
    case "roads":
      return "Strade";
    case "cities":
      return "Città";
    case "peaks":
      return "Montagne";
  }
}
