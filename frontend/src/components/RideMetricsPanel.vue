<template>
  <div class="metrics-grid">
    <div class="metric-card primary">
      <span class="metric-value">{{ (distance / 1000).toFixed(2) }} km</span>
<span class="metric-label">Distance</span>
     </div>

     <div class="metric-card">
       <span class="metric-value">{{ currentSpeed.toFixed(1) }}</span>
       <span class="metric-label">Speed (km/h)</span>
     </div>

     <div class="metric-card">
       <span class="metric-value">{{ avgSpeed.toFixed(1) }}</span>
       <span class="metric-label">Avg (km/h)</span>
     </div>

     <div class="metric-card">
       <span class="metric-value">{{ formattedTime }}</span>
       <span class="metric-label">Time</span>
     </div>

     <div v-if="elevation" class="metric-card">
       <span class="metric-value">{{ elevation.toFixed(0) }}</span>
       <span class="metric-label">Elevation (m)</span>
     </div>

     <div v-if="heartRate" class="metric-card">
       <span class="metric-value">{{ heartRate }}</span>
       <span class="metric-label">HR (bpm)</span>
     </div>

     <div v-if="cadence" class="metric-card">
       <span class="metric-value">{{ cadence }}</span>
       <span class="metric-label">Cadence (rpm)</span>
     </div>

     <div v-if="power" class="metric-card">
       <span class="metric-value">{{ power }}</span>
       <span class="metric-label">Power (W)</span>
     </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTrackingStore } from '../stores/trackingStore'

const tracking = useTrackingStore()

const distance = computed(() => tracking.distance)
const currentSpeed = computed(() => tracking.currentSpeed)
const avgSpeed = computed(() => tracking.avgSpeed)
const elapsedTime = computed(() => tracking.elapsedTime)
const elevation = computed(() => tracking.elevation)
const heartRate = computed(() => tracking.heartRate)
const cadence = computed(() => tracking.cadence)
const power = computed(() => tracking.power)

const formattedTime = computed(() => {
  const totalSeconds = Math.floor(elapsedTime.value)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
})
</script>

<style scoped>
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 16px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  text-align: center;
}

.metric-card.primary {
  background: var(--accent);
  color: var(--bg);
}

.metric-value {
  display: block;
  font-size: 1.4rem;
  font-weight: 600;
  margin-bottom: 4px;
}

.metric-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
}
</style>