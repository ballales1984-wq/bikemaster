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
        <button class="btn btn-primary" @click="loadHeatmap">
          {{ t("heatmap.loadHeatmap") }}
        </button>
      </div>
    </div>

    <div v-if="loading && !heatmapData" class="loading-text">
      {{ t("heatmap.loading") }}
    </div>

    <div
      v-if="heatmapData && heatmapData.points && heatmapData.points.length"
      class="heatmap-container"
    >
      <div id="leaflet-heatmap" class="heatmap-map" />
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

<script setup>
import "leaflet/dist/leaflet.css";
import { ref, onMounted, watch } from "vue";
import { useI18n } from "../composables/useI18n";
import { apiGet } from "../utils/api";

const { t } = useI18n();

const athleteId = ref(null);
const loading = ref(false);
const heatmapData = ref(null);

async function loadAthleteId() {
  const data = await apiGet("/api/v1/athletes");
  athleteId.value = data.athletes?.[0]?.id ?? null;
}

async function loadHeatmap() {
  if (!athleteId.value) return;
  loading.value = true;
  heatmapData.value = null;
  try {
    heatmapData.value = await apiGet("/api/v1/heatmap", {
      athlete_id: athleteId.value,
    });
  } catch (e) {
    console.error("heatmap error", e);
    heatmapData.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadAthleteId().then(loadHeatmap).catch(console.error);
});
watch(athleteId, loadHeatmap);
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
