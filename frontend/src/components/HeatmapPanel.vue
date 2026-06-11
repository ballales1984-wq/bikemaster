<template>
  <div class="panel">
    <h2>🔥 Heatmap Personale</h2>
    
    <div class="form-grid">
      <div class="form-group">
        <label for="heatmap-athlete-id">Atleta ID (0 = tutti)</label>
        <input id="heatmap-athlete-id" type="number" v-model.number="athleteId" min="0" />
      </div>
      <div class="form-group">
        <button class="btn btn-primary" @click="loadHeatmap">🔄 Carica Heatmap</button>
      </div>
    </div>
    
    <div v-if="loading && !heatmapData" class="loading-text">
      <span class="spinner"></span> Caricamento heatmap...
    </div>
    
    <div v-if="heatmapData && heatmapData.points && heatmapData.points.length" class="heatmap-container">
      <div id="leaflet-heatmap" class="heatmap-map"></div>
      <div class="heatmap-stats">
        <span class="badge badge-info">{{ heatmapData.total_points }} punti GPS</span>
        <span class="badge badge-info">{{ heatmapData.points.length }} celle</span>
      </div>
    </div>
    
    <div v-if="heatmapData && (!heatmapData.points || !heatmapData.points.length)" class="loading-text">
      Nessun dato GPS disponibile
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { apiGet } from '../utils/api.js'

const athleteId = ref(0)
const loading = ref(false)
const heatmapData = ref(null)

async function loadHeatmap() {
  loading.value = true
  heatmapData.value = null
  try {
    heatmapData.value = await apiGet('/api/v1/heatmap', { athlete_id: athleteId.value })
  } catch (e) {
    console.error('heatmap error', e)
    heatmapData.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => loadHeatmap())
watch(athleteId, loadHeatmap)
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