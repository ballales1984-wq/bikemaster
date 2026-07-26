<!-- Ride detail: full screen for a ride with main metrics, detailed analysis and charts.
     Props: rideId (number). Events: close (click on close button). Loads ride from /api/v1/rides/:id and chart images.
     UI: header with date, metrics grid, analysis section (elevation/HR/fatigue), SpeedMap (if API key) and speed/elevation charts. -->
<template>
  <section v-if="ride">
    <div class="panel">
      <div class="detail-header">
        <h2>{{ t("rideDetail.title") }}</h2>
<div class="header-actions">
          <button class="edit-btn" @click="startEdit" aria-label="Modifica">
            ✏️
          </button>
          <button
            class="edit-btn"
            @click="goToBm2"
            aria-label="BM2 Analysis"
          >
            ⚡ BM2
          </button>
          <button class="close-btn" @click="emit('close')" aria-label="Chiudi">
            ✕
          </button>
        </div>
      </div>

      <div v-if="editMode" class="edit-form">
        <label>
          Data
          <input v-model="editForm.date" type="date" />
        </label>
        <label>
          Titolo
          <input v-model="editForm.title" type="text" maxlength="150" />
        </label>
        <label>
          Distanza (km)
          <input v-model.number="editForm.distance_km" type="number" min="0" max="500" step="0.1" />
        </label>
        <label>
          Durata (min)
          <input v-model.number="editForm.duration_minutes" type="number" min="1" max="1440" step="1" />
        </label>
        <label>
          FC media (bpm)
          <input v-model.number="editForm.heart_rate_avg" type="number" min="30" max="220" step="1" />
        </label>
        <label>
          Dislivello (m)
          <input v-model.number="editForm.elevation_gain_m" type="number" min="0" max="15000" step="1" />
        </label>
        <label>
          Tipo
          <select v-model="editForm.activity_type">
            <option value="ride">Bici</option>
            <option value="walk">Passeggiata</option>
            <option value="hike">Trekking</option>
            <option value="run">Corsa</option>
            <option value="indoor">Indoor</option>
            <option value="other">Altro</option>
          </select>
        </label>
        <div class="edit-actions">
          <button class="save-btn" :disabled="saving" @click="saveEdit">
            {{ saving ? "Salvataggio…" : "Salva" }}
          </button>
          <button class="cancel-btn" :disabled="saving" @click="cancelEdit">
            Annulla
          </button>
        </div>
        <p v-if="editError" class="edit-error">{{ editError }}</p>
      </div>

      <div v-else class="ride-date-large">
        {{ formatDate(ride.date) }}
      </div>

      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon"></div>
          <div class="metric-value">{{ fmt(ride.distance_km) }} km</div>
          <div class="metric-label">Distanza</div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">⏱</div>
          <div class="metric-value">
            {{ formatDuration(ride.duration_minutes) }}
          </div>
          <div class="metric-label">Durata</div>
        </div>
        <div class="metric-card">
          <div class="metric-icon"></div>
          <div class="metric-value">{{ fmt(ride.avg_speed_kmh) }} km/h</div>
          <div class="metric-label">{{ t("rideDetail.avgSpeed") }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-icon"></div>
          <div class="metric-value">{{ fmt(ride.calories, 0) }} kcal</div>
          <div class="metric-label">Calorie</div>
        </div>
      </div>

      <div
        v-if="
          ride.elevation_gain_m || ride.max_speed_kmh || ride.heart_rate_avg
        "
        class="analysis-section"
      >
        <h3> Analisi Dettagliata</h3>
        <div class="analysis-grid">
          <div
v-if="ride.elevation_gain_m" class="a-item"
>
            <span class="a-lbl"> Dislivello</span>
            <span class="a-val">{{ fmt(ride.elevation_gain_m, 0) }} m</span>
          </div>
          <div
v-if="ride.max_speed_kmh" class="a-item"
>
            <span class="a-lbl"> {{ t("rideDetail.maxSpeed") }}</span>
            <span class="a-val">{{ fmt(ride.max_speed_kmh) }} km/h</span>
          </div>
        <div
          v-if="ride.heart_rate_avg" class="a-item"
        >
          <span class="a-lbl"> FC Media</span>
          <span class="a-val">{{ fmt(ride.heart_rate_avg, 0) }} bpm</span>
        </div>
          <div
v-if="ride.max_heart_rate" class="a-item"
>
            <span class="a-lbl"> FC Massima</span>
            <span class="a-val">{{ fmt(ride.max_heart_rate, 0) }} bpm</span>
          </div>
          <div
v-if="ride.fatigue_score !== undefined" class="a-item"
>
            <span class="a-lbl"> Affaticamento</span>
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
        <h3> Grafici</h3>
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
import { useRouter } from "vue-router";
import { apiGet, apiPut } from "../utils/api";
import { useI18n } from "../composables/useI18n";
import type { Ride } from "../types/index";
import SpeedMap from "./SpeedMap.vue";

const { t } = useI18n();
const router = useRouter();

const props = defineProps({ rideId: Number });
const emit = defineEmits(["close"]);

const ride = ref<Ride | null>(null);
const speedChart = ref("");
const elevationChart = ref("");
const googleMapsApiKey = ref("");

const editMode = ref(false);
const saving = ref(false);
const editError = ref("");
const editForm = ref<{
  date: string;
  title: string;
  distance_km: number;
  duration_minutes: number;
  heart_rate_avg: number | null;
  elevation_gain_m: number | null;
  activity_type: string;
}>({
  date: "",
  title: "",
  distance_km: 0,
  duration_minutes: 0,
  heart_rate_avg: null,
  elevation_gain_m: null,
  activity_type: "ride",
});

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

function goToBm2() {
  if (ride.value?.id) {
    router.push({ path: "/bm2", query: { rideId: ride.value.id } });
  }
}

function startEdit() {
  if (!ride.value) return;
  editForm.value = {
    date: ride.value.date || "",
    title: ride.value.title || "",
    distance_km: ride.value.distance_km || 0,
    duration_minutes: ride.value.duration_minutes || 0,
    heart_rate_avg: ride.value.heart_rate_avg ?? null,
    elevation_gain_m: ride.value.elevation_gain_m ?? null,
    activity_type: ride.value.activity_type || "ride",
  };
  editError.value = "";
  editMode.value = true;
}

function cancelEdit() {
  editMode.value = false;
  editError.value = "";
}

async function saveEdit() {
  if (!ride.value) return;
  saving.value = true;
  editError.value = "";
  try {
    const payload = {
      date: editForm.value.date,
      title: editForm.value.title || null,
      distance_km: editForm.value.distance_km,
      duration_minutes: editForm.value.duration_minutes,
      heart_rate_avg: editForm.value.heart_rate_avg,
      elevation_gain_m: editForm.value.elevation_gain_m,
      activity_type: editForm.value.activity_type,
    };
    const updated = await apiPut<Ride>(`/api/v1/rides/${props.rideId}`, payload);
    ride.value = updated;
    editMode.value = false;
  } catch (err) {
    editError.value = err instanceof Error ? err.message : "Salvataggio fallito";
  } finally {
    saving.value = false;
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edit-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1.2rem;
  padding: 4px;
  line-height: 1;
}

.edit-btn:hover {
  color: var(--accent);
}

.edit-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  margin-bottom: 20px;
}

.edit-form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.edit-form input,
.edit-form select {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px;
  color: var(--text-primary);
}

.edit-actions {
  grid-column: 1 / -1;
  display: flex;
  gap: 12px;
}

.save-btn,
.cancel-btn {
  border: none;
  border-radius: var(--radius-sm);
  padding: 8px 16px;
  cursor: pointer;
  font-weight: 600;
}

.save-btn {
  background: var(--accent);
  color: #fff;
}

.cancel-btn {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.edit-error {
  grid-column: 1 / -1;
  color: var(--error);
  font-size: 0.85rem;
  margin: 0;
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
