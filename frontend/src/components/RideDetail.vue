<!-- Dettaglio uscita: schermata completa di una ride con metriche principali, analisi dettagliata e grafici.
     Props: rideId (number). Eventi: close (click sul pulsante chiudi). Carica la ride da /api/v1/rides/:id e le immagini chart.
     UI: header con data, griglia metriche, sezione analisi (dislivello/FC/fatica), SpeedMap (se API key) e grafici velocità/dislivello. -->
<template>
  <section v-if="ride">
    <div class="panel">
      <div class="detail-header">
        <h2>🚴 Dettaglio Uscita</h2>
        <button class="close-btn" @click="$emit('close')" aria-label="Chiudi">
          ✕
        </button>
      </div>

      <div class="ride-date-large">
        {{ formatDate(ride.date) }}
      </div>

      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon">📏</div>
          <div class="metric-value">{{ fmt(ride.distance_km) }} km</div>
          <div class="metric-label">Distanza</div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">⏱️</div>
          <div class="metric-value">
            {{ formatDuration(ride.duration_minutes) }}
          </div>
          <div class="metric-label">Durata</div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">⚡</div>
          <div class="metric-value">{{ fmt(ride.avg_speed_kmh) }} km/h</div>
          <div class="metric-label">Velocità Media</div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">🔥</div>
          <div class="metric-value">{{ fmt(ride.calories, 0) }} kcal</div>
          <div class="metric-label">Calorie</div>
        </div>
      </div>

      <div
        v-if="
          ride.elevation_gain_m || ride.max_speed_kmh || ride.avg_heart_rate
        "
        class="analysis-section"
      >
        <h3>📊 Analisi Dettagliata</h3>
        <div class="analysis-grid">
          <div
v-if="ride.elevation_gain_m" class="a-item"
>
            <span class="a-lbl">⛰️ Dislivello</span>
            <span class="a-val">{{ fmt(ride.elevation_gain_m, 0) }} m</span>
          </div>
          <div
v-if="ride.max_speed_kmh" class="a-item"
>
            <span class="a-lbl">💨 Velocità Max</span>
            <span class="a-val">{{ fmt(ride.max_speed_kmh) }} km/h</span>
          </div>
          <div
v-if="ride.avg_heart_rate" class="a-item"
>
            <span class="a-lbl">❤️ FC Media</span>
            <span class="a-val">{{ fmt(ride.avg_heart_rate, 0) }} bpm</span>
          </div>
          <div
v-if="ride.max_heart_rate" class="a-item"
>
            <span class="a-lbl">❤️ FC Massima</span>
            <span class="a-val">{{ fmt(ride.max_heart_rate, 0) }} bpm</span>
          </div>
          <div
v-if="ride.fatigue_score !== undefined" class="a-item"
>
            <span class="a-lbl">😰 Affaticamento</span>
            <span
class="a-val" :class="fatigueClass"
            >{{ ride.fatigue_score }}/10</span>
          </div>
        </div>
      </div>

      <SpeedMap
        v-if="googleMapsApiKey"
        :ride-id="ride.id"
        :api-key="googleMapsApiKey"
      />

      <div
v-if="speedChart || elevationChart" class="chart-section"
>
        <h3>📈 Grafici</h3>
        <div class="chart-row">
          <img
            v-if="speedChart"
            :src="speedChart"
            alt="Speed chart"
            class="chart-img"
          >
          <img
            v-if="elevationChart"
            :src="elevationChart"
            alt="Elevation chart"
            class="chart-img"
          >
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { apiGet } from "../utils/api";
import type { Ride } from "../types/index";
import SpeedMap from "./SpeedMap.vue";

const props = defineProps({ rideId: Number });
const emit = defineEmits(["close"]);

const ride = ref<Ride | null>(null);
const speedChart = ref("");
const elevationChart = ref("");
const googleMapsApiKey = ref("");

const fatigueClass = computed(() => {
  const score = ride.value?.fatigue_score ?? 0;
  if (score <= 3) return "fatigue-low";
  if (score <= 6) return "fatigue-medium";
  return "fatigue-high";
});

function fmt(v: number | undefined, dec = 1) {
  if (v == null || isNaN(Number(v))) return "—";
  return Number(v).toFixed(dec);
}

function formatDuration(minutes: number | string | undefined) {
  const mins = Number(minutes) || 0;
  const h = Math.floor(mins / 60);
  const m = Math.floor(mins % 60);
  const s = Math.floor((mins % 1) * 60);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatDate(dateStr: string | undefined) {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("it-IT", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

async function load() {
  try {
    const data = await apiGet<Ride>(`/api/v1/rides/${props.rideId}`);
    ride.value = data;
    speedChart.value = `/api/v1/charts/speed/${props.rideId}`;
    elevationChart.value = `/api/v1/charts/elevation/${props.rideId}`;
    const config = await apiGet<{ google_maps_api_key: string }>("/api/v1/config/google-maps-key");
    googleMapsApiKey.value = config.google_maps_api_key || "";
  } catch {
    // ignore load errors
  }
}

onMounted(() => load());
</script>

<style scoped>
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.detail-header h2 {
  margin: 0;
  color: var(--accent);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1.3rem;
  padding: 4px;
  line-height: 1;
}

.close-btn:hover {
  color: var(--text-primary);
}

.ride-date-large {
  color: var(--text-muted);
  font-size: 0.95rem;
  margin-bottom: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}

.metric-card {
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  padding: 16px 12px;
  text-align: center;
  border: 1px solid var(--border);
  transition: var(--transition);
}

.metric-card:hover {
  border-color: var(--accent);
}

.metric-icon {
  font-size: 1.4rem;
  margin-bottom: 6px;
}

.metric-value {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--accent);
  font-family: "Outfit", sans-serif;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.analysis-section {
  margin-bottom: 24px;
}

.analysis-section h3 {
  color: var(--text-secondary);
  font-size: 1rem;
  margin-bottom: 12px;
}

.analysis-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.a-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.a-lbl {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.a-val {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.fatigue-low {
  color: var(--success);
}
.fatigue-medium {
  color: var(--warning);
}
.fatigue-high {
  color: var(--error);
}

.chart-section {
  margin-top: 24px;
}

.chart-section h3 {
  color: var(--text-secondary);
  font-size: 1rem;
  margin-bottom: 12px;
}

.chart-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.chart-img {
  width: 100%;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}
</style>
