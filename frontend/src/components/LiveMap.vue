<template>
  <div class="live-map-wrapper">
    <div ref="mapEl" class="live-map" />
  </div>
</template>

<!-- Mappa live del tracking: mappa Leaflet che disegna in tempo reale il percorso GPS durante un'uscita.
      Props: mapStyle ('osm' | 'cyclosm'), showPois (boolean), points (GpsPoint[]) per tracciare il percorso completo
      come mappa statica. Eventi: nessuno.
      Espone addPoint/clear/centerMap/setRoute via defineExpose. Cambia stile mappa dinamicamente. -->
<script setup lang="ts">
import "leaflet/dist/leaflet.css";
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import L from "leaflet";
import { useTrackingStore } from "../stores/trackingStore";
import { apiGet } from "../utils/api";

const Ln = L as unknown as {
  map(element: HTMLElement, options?: Record<string, unknown>): any;
  tileLayer(
    url: string,
    options?: Record<string, unknown>,
  ): { addTo(map: any): unknown; remove(): void };
  polyline(
    latlngs: Array<[number, number]>,
    options?: Record<string, unknown>,
  ): {
    addTo(map: any): any;
    addLatLng(latlng: [number, number]): any;
    getBounds(): any;
  };
  circleMarker(
    latlng: [number, number],
    options?: Record<string, unknown>,
  ): {
    addTo(map: any): { bindPopup(html: string): unknown };
    bindPopup(html: string): unknown;
  };
  layerGroup(): { addTo(map: any): any; clearLayers(): void };
};

const props = defineProps<{
  mapStyle?: string;
  showPois?: boolean;
  points?: Array<{ lat: number; lon: number }>;
}>();

const mapEl = ref<HTMLElement | null>(null);
const map = ref<any>(null);
const polyline = ref<any>(null);
const tileLayer = ref<{ remove(): void } | null>(null);
const poiLayer = ref<any>(null);

const tracking = useTrackingStore();
const trackingPoints = ref<Array<[number, number]>>([]);
const poisLoaded = ref(false);

const POI_COLORS: Record<string, string> = {
  cafe: "#b45309",
  bakery: "#b45309",
  restaurant: "#dc2626",
  water: "#2563eb",
  viewpoint: "#7c3aed",
  bike_shop: "#059669",
  emergency: "#dc2626",
  other: "#64748b",
};

const MAP_STYLES: Record<string, { url: string; attribution: string }> = {
  osm: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap",
  },
  cyclosm: {
    url: "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | &copy; <a href="http://cyclosm.org">CyclOSM</a>',
  },
};

function setTileLayer(style: string) {
  if (!map.value) return;
  if (tileLayer.value) {
    tileLayer.value.remove();
    tileLayer.value = null;
  }
  const cfg = MAP_STYLES[style] || MAP_STYLES.osm;
  tileLayer.value = Ln.tileLayer(cfg.url, {
    attribution: cfg.attribution,
    maxZoom: 19,
  }).addTo(map.value) as unknown as { remove(): void };
}

async function loadNearbyPois(lat: number, lon: number) {
  if (!props.showPois) return;
  if (!poiLayer.value) {
    poiLayer.value = L.layerGroup().addTo(map.value);
  }
  if (poisLoaded.value) return;
  poisLoaded.value = true;
  try {
    const data = await apiGet<{
      pois: Array<{
        name: string;
        lat: number;
        lon: number;
        type?: string;
        description?: string;
      }>;
    }>("/api/v1/maps/pois/nearby", {
      lat: String(lat),
      lon: String(lon),
      radius: "5",
    });
    for (const poi of data.pois || []) {
      if (!Number.isFinite(poi.lat) || !Number.isFinite(poi.lon)) continue;
      const color = POI_COLORS[poi.type || "other"] || POI_COLORS.other;
      L.circleMarker([poi.lat, poi.lon], {
        radius: 6,
        color,
        fillColor: color,
        fillOpacity: 0.9,
        weight: 2,
      })
        .addTo(poiLayer.value)
        .bindPopup(
          `<strong>${poi.name}</strong><br>${poi.type || ""}${poi.description ? "<br>" + poi.description : ""}`,
        );
    }
  } catch {
    /* POIs are optional; ignore failures so tracking keeps working */
  }
}

function addPoint(lat: number, lon: number) {
  trackingPoints.value.push([lat, lon]);
  if (!polyline.value && map.value) {
    polyline.value = Ln.polyline(trackingPoints.value, {
      color: "#4ecca3",
      weight: 5,
      opacity: 0.9,
    }).addTo(map.value);
  } else if (polyline.value) {
    polyline.value.addLatLng([lat, lon]);
  }
  map.value?.setView([lat, lon], 16);
  void loadNearbyPois(lat, lon);
}

function centerMap() {
  const pts = tracking.routePoints;
  if (pts.length > 0 && map.value) {
    const last = pts[pts.length - 1];
    map.value.setView([last.lat, last.lon], 16);
  } else if (map.value) {
    map.value.setView([45.4642, 9.19], 16);
  }
}

function clear() {
  trackingPoints.value = [];
  polyline.value = null;
  poisLoaded.value = false;
  if (poiLayer.value) {
    poiLayer.value.clearLayers();
  }
}

function setRoute(routePoints: Array<{ lat: number; lon: number }>) {
  clear();
  if (!map.value || routePoints.length === 0) return;
  const latlngs = routePoints.map((p) => [p.lat, p.lon] as [number, number]);
  polyline.value = L.polyline(latlngs, {
    color: "#4ecca3",
    weight: 5,
    opacity: 0.9,
  }).addTo(map.value);
  map.value.fitBounds(polyline.value.getBounds().pad(0.1));
}

watch(
  () => props.points,
  (pts) => {
    if (pts && pts.length) {
      setRoute(pts);
    }
  },
);

watch(
  () => tracking.routePoints.length,
  () => {
    const pts = tracking.routePoints;
    const point = pts[pts.length - 1];
    if (point && map.value) {
      addPoint(point.lat, point.lon);
    }
  },
);

watch(
  () => props.mapStyle,
  (style) => {
    if (style) setTileLayer(style);
  },
);

watch(
  () => props.showPois,
  (show) => {
    if (!show) {
      if (poiLayer.value && map.value) {
        poiLayer.value.clearLayers();
        poiLayer.value = null;
      }
      poisLoaded.value = false;
    }
  },
);

onMounted(() => {
  if (!mapEl.value) return;
  map.value = Ln.map(mapEl.value, { preferCanvas: true }).setView(
    [45.4642, 9.19],
    16,
  );
  setTileLayer(props.mapStyle || "osm");
});

onBeforeUnmount(() => {
  if (map.value) {
    map.value.remove();
    map.value = null;
    polyline.value = null;
    poiLayer.value = null;
    tileLayer.value = null;
  }
});

defineExpose({
  addPoint,
  centerMap,
  clear,
  setRoute,
});
</script>

<style scoped>
.live-map-wrapper {
  width: 100%;
  height: 400px;
  min-height: 400px;
}
.live-map {
  height: 100%;
  width: 100%;
  border-radius: var(--radius-sm);
}
</style>
