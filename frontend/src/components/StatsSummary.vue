<template>
  <div class="stats" aria-label="Statistiche generali">
    <div class="stat-card" role="status">
      <div class="stat-value">{{ formatValue(stats?.rides, 0) }}</div>
      <div class="stat-label">Rides</div>
    </div>
    <div class="stat-card" role="status">
      <div class="stat-value">{{ formatValue(stats?.distance_km, 1) }}</div>
      <div class="stat-label">Km Totali</div>
    </div>
    <div class="stat-card" role="status">
      <div class="stat-value">{{ formatValue(stats?.calories, 0) }}</div>
      <div class="stat-label">Calorie</div>
    </div>
    <div class="stat-card" role="status">
      <div class="stat-value">{{ formatValue(stats?.avg_speed_kmh, 1) }}</div>
      <div class="stat-label">Vel Media</div>
    </div>
    <div class="stat-card" role="status">
      <div class="stat-value">{{ hoursFromMin }}</div>
      <div class="stat-label">Ore Totali</div>
    </div>
    <button class="stat-card stat-refresh" @click="$emit('refresh')" :disabled="loading" :aria-label="loading ? 'Aggiornamento in corso' : 'Aggiorna statistiche'">
      <span :class="{ spinner: loading }">{{ loading ? '' : '🔄' }}</span>
      <div class="stat-label">{{ loading ? 'Aggiorno...' : 'Aggiorna' }}</div>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

defineEmits(['refresh'])

function formatValue(v, decimals = 1) {
  if (v == null || isNaN(v)) return '0'
  return Number(v).toFixed(decimals)
}

const hoursFromMin = computed(() => {
  const m = props.stats?.duration_minutes
  if (m == null || isNaN(m)) return '0'
  return (Number(m) / 60).toFixed(1)
})
</script>
