<!-- Pannello metriche in tempo reale: griglia di card con distanza, velocità corrente/media, tempo, dislivello, FC, cadenza e potenza.
     Props: nessuna. Eventi: nessuno (legge trackingStore). Mostra le card solo se il dato è disponibile; evidenzia velocità alta e stile.
     UI: card metrica con icona, valore e label; la distanza è la card primaria in evidenza. -->
<template>
  <div class="metrics-grid">
    <div class="metric-card primary">
      <div class="metric-icon">🛣️</div>
      <div class="metric-content">
        <span class="metric-value">{{ formattedDistance }}</span>
        <span class="metric-label">Distance (km)</span>
      </div>
    </div>

    <div class="metric-card" :class="{ 'highlight-fast': currentSpeed > 25 }">
      <div class="metric-icon">⚡</div>
      <div class="metric-content">
        <span class="metric-value">{{ currentSpeed.toFixed(1) }}</span>
        <span class="metric-label">Speed (km/h)</span>
      </div>
    </div>

    <div class="metric-card">
      <div class="metric-icon">⏱️</div>
      <div class="metric-content">
        <span class="metric-value">{{ formattedTime }}</span>
        <span class="metric-label">Time</span>
      </div>
    </div>

    <div class="metric-card">
      <div class="metric-icon">📊</div>
      <div class="metric-content">
        <span class="metric-value">{{ avgSpeed.toFixed(1) }}</span>
        <span class="metric-label">Avg (km/h)</span>
      </div>
    </div>

    <div v-if="elevation" class="metric-card elevation">
      <div class="metric-icon">⛰️</div>
      <div class="metric-content">
        <span class="metric-value">{{ elevation.toFixed(0) }}</span>
        <span class="metric-label">Elevation (m)</span>
      </div>
    </div>

    <div v-if="heartRate" class="metric-card hr">
      <div class="metric-icon">❤️</div>
      <div class="metric-content">
        <span class="metric-value">{{ heartRate }}</span>
        <span class="metric-label">HR (bpm)</span>
      </div>
    </div>

    <div v-if="cadence" class="metric-card">
      <div class="metric-icon">🔄</div>
      <div class="metric-content">
        <span class="metric-value">{{ cadence }}</span>
        <span class="metric-label">Cadence (rpm)</span>
      </div>
    </div>

    <div v-if="power" class="metric-card">
      <div class="metric-icon">⚡</div>
      <div class="metric-content">
        <span class="metric-value">{{ power }}</span>
        <span class="metric-label">Power (W)</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useTrackingStore } from "../stores/trackingStore";

const tracking = useTrackingStore();

const distance = computed(() => tracking.distance);
const currentSpeed = computed(() => tracking.currentSpeed);
const avgSpeed = computed(() => tracking.avgSpeed);
const elapsedTime = computed(() => tracking.elapsedTime);
const elevation = computed(() => tracking.elevation);
const heartRate = computed(() => tracking.heartRate);
const cadence = computed(() => tracking.cadence);
const power = computed(() => tracking.power);

const formattedTime = computed(() => {
  const totalSeconds = Math.floor(elapsedTime.value);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${hours > 0 ? hours + ':' : ''}${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
});

const formattedDistance = computed(() => {
  return (distance.value / 1000).toFixed(2);
});
</script>

<style scoped>
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.metric-icon {
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 50%;
}

.metric-content {
  display: flex;
  flex-direction: column;
}

.metric-card.primary {
  background: linear-gradient(135deg, var(--accent), #2563eb);
  color: #ffffff;
  border: none;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

.metric-card.primary .metric-icon {
  background: rgba(255, 255, 255, 0.2);
}

.metric-card.primary .metric-label {
  color: rgba(255, 255, 255, 0.8);
}

.metric-value {
  display: block;
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 2px;
}

.metric-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  font-weight: 500;
}

.highlight-fast .metric-value {
  color: #ef4444; /* red for fast */
}

.elevation .metric-value {
  color: #10b981; /* green for elevation */
}

.hr .metric-value {
  color: #f43f5e; /* rose for HR */
}
</style>
