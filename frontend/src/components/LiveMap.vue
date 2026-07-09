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
};

const mapEl = ref<HTMLElement | null>(null);
const map = ref<LeafletMap | null>(null);
const polyline = ref<LeafletPolyline | null>(null);

const tracking = useTrackingStore();
const points = ref<Array<[number, number]>>([]);

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
