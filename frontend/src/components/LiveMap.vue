<template>
  <div class="live-map-wrapper">
    <div
ref="mapEl" class="live-map" />
  </div>
</template>

<script setup lang="ts">
import "leaflet/dist/leaflet.css";
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import L from "leaflet";
import { useTrackingStore } from "../stores/trackingStore";
import { apiGet } from "../utils/api";

interface LeafletMap {
  setView(center: [number, number], zoom: number): LeafletMap;
  remove(): void;
}
interface LeafletPolyline {
  addTo(map: LeafletMap): LeafletPolyline;
  addLatLng(latlng: [number, number]): LeafletPolyline;
}

const Ln = L as unknown as {
  map(element: HTMLElement, options?: Record<string, unknown>): LeafletMap;
  tileLayer(
    url: string,
    options?: Record<string, unknown>,
  ): { addTo(map: LeafletMap): unknown };
  polyline(
    latlngs: Array<[number, number]>,
    options?: Record<string, unknown>,
  ): LeafletPolyline;
  circleMarker(
    latlng: [number, number],
    options?: Record<string, unknown>,
  ): {
    addTo(map: LeafletMap): { bindPopup(html: string): unknown };
    bindPopup(html: string): unknown;
  };
};

const mapEl = ref<HTMLElement | null>(null);
const map = ref<LeafletMap | null>(null);
const polyline = ref<LeafletPolyline | null>(null);

const tracking = useTrackingStore();
const points = ref<Array<[number, number]>>([]);
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

async function loadNearbyPois(lat: number, lon: number) {
  if (poisLoaded.value) return;
  poisLoaded.value = true;
  try {
    const data = await apiGet<{ pois: Array<{ name: string; lat: number; lon: number; type?: string; description?: string }> }>(
      "/api/v1/maps/pois/nearby",
      { lat: String(lat), lon: String(lon), radius: "5" },
    );
    for (const poi of data.pois || []) {
      if (!Number.isFinite(poi.lat) || !Number.isFinite(poi.lon)) continue;
      const color = POI_COLORS[poi.type || "other"] || POI_COLORS.other;
      Ln.circleMarker([poi.lat, poi.lon], {
        radius: 6,
        color,
        fillColor: color,
        fillOpacity: 0.9,
        weight: 2,
      })
        .addTo(map.value as unknown as LeafletMap)
        .bindPopup(`<strong>${poi.name}</strong><br>${poi.type || ""}${poi.description ? "<br>" + poi.description : ""}`);
    }
  } catch {
    /* POIs are optional; ignore failures so tracking keeps working */
  }
}

function addPoint(lat: number, lon: number) {
  points.value.push([lat, lon]);
  if (!polyline.value && map.value) {
    polyline.value = Ln.polyline(points.value, {
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

onMounted(() => {
  if (!mapEl.value) return;
  map.value = Ln.map(mapEl.value, { preferCanvas: true }).setView(
    [45.4642, 9.19],
    16,
  );
  Ln.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
    maxZoom: 19,
  }).addTo(map.value);
});

onBeforeUnmount(() => {
  if (map.value) {
    map.value.remove();
    map.value = null;
  }
});

defineExpose({
  addPoint,
  clear() {
    points.value = [];
    polyline.value = null;
    poisLoaded.value = false;
  },
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
