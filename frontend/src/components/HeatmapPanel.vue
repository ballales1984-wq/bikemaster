<!-- Pannello heatmap personale: mappa Leaflet con layer heat (leaflet.heat) dei punti GPS percorsi dall'atleta.
     Props: nessuna. Eventi: nessuno (usa /api/v1/heatmap). Inserisci Athlete ID e carica; mostra mappa e conteggi celle/punti.
     UI: form Athlete ID + pulsante, contenitore mappa 500px e badge con statistiche; gestisce stati loading/no-data. -->
<template>
  <div class="panel">
    <h2>🔥 Personal Heatmap</h2>

    <div class="form-grid">
      <div class="form-group">
        <label for="heatmap-athlete-id">{{ t("heatmap.athleteId") }}</label>
        <input
          id="heatmap-athlete-id"
          v-model.number="athleteId"
          type="number"
          min="1"
        >
      </div>
      <div class="form-group">
        <button class="btn btn-primary"
@click="loadHeatmap">
          {{ t("heatmap.loadHeatmap") }}
        </button>
      </div>
    </div>

    <div v-if="loading && !heatmapData"
class="loading-text">
      {{ t("heatmap.loading") }}
    </div>

    <div
      v-if="heatmapData && heatmapData.points && heatmapData.points.length"
      class="heatmap-container"
    >
      <div id="leaflet-heatmap"
class="heatmap-map" />
      <div class="heatmap-stats">
        <span class="badge badge-info">{{ heatmapData.total_points }} GPS points</span>
        <span class="badge badge-info">{{ heatmapData.points.length }} cells</span>
      </div>
    </div>
    <div
      v-if="heatmapData && (!heatmapData.points || !heatmapData.points.length)"
      class="loading-text"
    >
      {{ t("heatmap.noData") }}
    </div>
  </div>
</template>

<script setup lang="ts">
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "leaflet.heat";
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { useI18n } from "../composables/useI18n";
import { apiGet } from "../utils/api";

const { t } = useI18n();

interface HeatmapCell {
  lat: number;
  lon: number;
  count?: number;
}
interface HeatmapData {
  points: HeatmapCell[];
  bounds?: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  };
  total_points: number;
}

const athleteId = ref<number | null>(null);
const loading = ref(false);
const heatmapData = ref<HeatmapData | null>(null);
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let map: any = null;

async function loadAthleteId() {
  const data = (await apiGet("/api/v1/athletes")) as {
    athletes?: { id: number }[];
  };
  athleteId.value = data.athletes?.[0]?.id ?? null;
}

async function loadHeatmap() {
  if (!athleteId.value) return;
  loading.value = true;
  heatmapData.value = null;
  try {
    heatmapData.value = (await apiGet("/api/v1/heatmap", {
      athlete_id: String(athleteId.value),
    })) as HeatmapData;
  } catch (e) {
    console.error("heatmap error", e);
    heatmapData.value = null;
  } finally {
    loading.value = false;
  }
}

async function renderMap() {
  await nextTick();
  const el = document.getElementById("leaflet-heatmap");
  if (!el || !heatmapData.value?.points?.length) return;
  if (map) {
    map.remove();
    map = null;
  }
  const points = heatmapData.value.points;
  const bounds = heatmapData.value.bounds;
  const center: [number, number] = bounds?.min_lat
    ? [
        (bounds.min_lat + bounds.max_lat) / 2,
        (bounds.min_lon + bounds.max_lon) / 2,
      ]
    : [41.9, 12.5];
  map = L.map(el).setView(center, 6);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 18,
  }).addTo(map);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (L as any)
    .heatLayer(
      points.map((p: { lat: number; lon: number; count?: number }) => [
        p.lat,
        p.lon,
        p.count ?? 1,
      ]),
      { radius: 20, blur: 15, maxZoom: 12 },
    )
    .addTo(map);
  setTimeout(() => map && map.invalidateSize(), 0);
}

onMounted(() => {
  loadAthleteId().catch(console.error);
});
watch(athleteId, loadHeatmap);
watch(heatmapData, renderMap);

onBeforeUnmount(() => {
  if (map) {
    map.remove();
    map = null;
  }
});
</script>

<style scoped>
.heatmap-container {
  margin-top: 15px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.heatmap-map {
  height: 500px;
  width: 100%;
}

.heatmap-stats {
  padding: 10px;
  background: var(--bg-tertiary);
  display: flex;
  gap: 10px;
}

.badge-info {
  background: var(--accent);
  color: var(--bg-primary);
}
</style>
