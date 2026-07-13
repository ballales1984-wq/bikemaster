<template>
  <section class="rides-section">
    <!-- Add ride form -->
    <div class="panel add-panel">
      <div
        class="add-header"
        role="button"
        tabindex="0"
        @click="showForm = !showForm"
        @keydown.enter="showForm = !showForm"
        @keydown.space.prevent="showForm = !showForm"
      >
        <h2>➕ {{ t("rides.addTitle") }}</h2>
        <span class="toggle-icon">{{ showForm ? "▲" : "▼" }}</span>
      </div>
      <transition name="slide-down">
        <form v-if="showForm" @submit.prevent="handleAdd" class="ride-form">
          <div class="form-grid">
            <div class="form-group">
              <label for="ride-date">{{ t("common.date") }}</label>
              <input
                id="ride-date"
                v-model="form.date"
                type="date"
                required
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label for="ride-dist">{{ t("rides.distance") }} (km)</label>
              <input
                id="ride-dist"
                v-model="form.distance_km"
                type="number"
                step="0.01"
                placeholder="0.0"
                required
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label for="ride-dur">{{ t("rides.duration") }} (min)</label>
              <input
                id="ride-dur"
                v-model="form.duration_minutes"
                type="number"
                placeholder="0"
                required
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label for="ride-speed">{{ t("rides.avgSpeed") }} (km/h)</label>
              <input
                id="ride-speed"
                v-model="form.avg_speed_kmh"
                type="number"
                step="0.01"
                placeholder="0.0"
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label for="ride-elev">{{ t("rides.elevation") }} (m)</label>
              <input
                id="ride-elev"
                v-model="form.elevation_gain_m"
                type="number"
                placeholder="0"
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label for="ride-cal">{{ t("common.calories") }}</label>
              <input
                id="ride-cal"
                v-model="form.calories"
                type="number"
                placeholder="0"
                class="form-input"
              >
            </div>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn" :disabled="adding">
              {{
                adding
                  ? "⏳ " + t("common.loading")
                  : "✅ " + t("rides.addTitle")
              }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              @click="showForm = false"
            >
              {{ t("common.cancel") }}
            </button>
          </div>
          <p
v-if="addError" class="error-text">⚠️ {{ addError }}</p>
        </form>
      </transition>
    </div>

    <!-- Rides list panel -->
    <div class="panel">
      <div class="list-header">
        <h2>
          🏍️ {{ t("rides.title") }}
          <span v-if="!loading"
class="ride-count">{{
            filteredRides.length
          }}</span>
        </h2>
        <div class="list-controls">
          <button
            class="btn btn-sm btn-secondary"
            :disabled="rides.length === 0"
            :aria-label="t('common.download') + ' CSV'"
            @click="exportCSV"
          >
            📥 CSV
          </button>
          <button
            class="btn btn-sm btn-secondary"
            :aria-label="'Filters'"
            @click="toggleFilters"
          >
            🔧 {{ t("common.filter") }}{{ hasActiveFilters ? " ●" : "" }}
          </button>
          <select
            id="ride-sort-by"
            v-model="sortBy"
            class="sort-select"
            :aria-label="t('common.filter')"
          >
            <option value="date_desc">📅 {{ t("common.date") }} ▼
</option>
            <option value="date_asc">📅 {{ t("common.date") }} ▲
</option>
            <option value="distance_desc">
              🛣️ {{ t("rides.distance") }} ↓
            </option>
            <option value="speed_desc">⚡ {{ t("rides.avgSpeed") }} ↓
</option>
          </select>
        </div>
      </div>

      <!-- Filters -->
      <transition name="slide-down">
        <div v-if="filtersOpen" class="filters-panel">
          <div class="filters-grid">
            <div class="form-group">
              <label>{{ t("common.date") }} {{ t("common.from") }}</label>
              <input
                id="ride-filter-date-from"
                v-model="filters.dateFrom"
                type="date"
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label>{{ t("common.date") }} {{ t("common.to") }}</label>
              <input
                id="ride-filter-date-to"
v-model="filters.dateTo" type="date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t("rides.distance") }} min (km)</label>
              <input
                id="ride-filter-dist-min"
                v-model.number="filters.distMin"
                type="number"
                min="0"
                placeholder="0"
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>{{ t("rides.distance") }} max (km)</label>
              <input
                id="ride-filter-dist-max"
                v-model.number="filters.distMax"
                type="number"
                min="0"
                placeholder="∞"
                class="form-input"
              />
            </div>
          </div>
          <div class="filter-actions">
            <button class="btn btn-sm btn-secondary" @click="resetFilters">
              🗑️ {{ t("common.clear") }}
            </button>
          </div>
        </div>
      </transition>

      <!-- Loading skeleton -->
      <div v-if="loading" class="skeleton-container">
        <div
          v-for="i in 5"
          :key="i"
          class="skeleton"
          style="height: 60px; border-radius: var(--radius); margin-bottom: 8px"
        />
      </div>

      <!-- Guest state -->
      <div v-else-if="guest" class="empty-state">
        <div class="empty-icon">🔐</div>
        <div class="empty-title">
          {{ t("rides.noRides") }}
        </div>
        <div class="empty-desc">Accedi per vedere le tue uscite.</div>
        <router-link to="/" class="btn btn-sm" style="margin-top: 14px">
          🔑 Accedi
        </router-link>
      </div>

      <!-- Empty state -->
      <div v-else-if="rides.length === 0" class="empty-state">
        <div class="empty-icon">🚵</div>
        <div class="empty-title">
          {{ t("rides.noRides") }}
        </div>
        <div class="empty-desc">
          {{ t("import.selectFile") }}
        </div>
        <button
          class="btn btn-sm"
          style="margin-top: 14px"
          @click="showForm = true"
        >
          ➕ {{ t("rides.addTitle") }}
        </button>
      </div>

      <!-- Filtered empty -->
      <div v-else-if="filteredRides.length === 0" class="empty-state">
        <div class="empty-icon">🔍</div>
        <div class="empty-title">
          {{ t("common.none") }}
        </div>
        <button
          class="btn btn-sm btn-secondary"
          style="margin-top: 14px"
          @click="resetFilters"
        >
          {{ t("common.clear") }}
        </button>
      </div>

      <!-- Ride list -->
      <div v-else class="rides-list">
        <div
          v-for="ride in filteredRides"
          :key="ride.id"
          class="ride-item"
          role="button"
          tabindex="0"
          :aria-label="`Uscita del ${ride.date}`"
          @click="openDetail(ride)"
        >
          <div class="ride-left">
            <div class="ride-date">
              {{ formatDate(ride.date) }}
            </div>
            <div
v-if="ride.title" class="ride-title"
>
              {{ ride.title }}
            </div>
            <div class="ride-stats">
              <span class="stat-chip">🛣️ {{ fmt(ride.distance_km) }} km</span>
              <span class="stat-chip">⏱️ {{ formatDuration(ride.duration_minutes) }}</span>
              <span v-if="ride.avg_speed_kmh"
class="stat-chip"
                >⚡ {{ fmt(ride.avg_speed_kmh) }} km/h</span
              >
              <span v-if="ride.elevation_gain_m"
class="stat-chip"
                >⛰️ {{ fmt(ride.elevation_gain_m, 0) }}m</span
              >
              <span v-if="ride.calories"
class="stat-chip cal"
                >🔥 {{ fmt(ride.calories, 0) }} kcal</span
              >
            </div>
          </div>
          <div class="ride-right">
            <div
v-if="ride.external_source" class="source-badge"
>
              {{ ride.external_source }}
            </div>
            <button
              class="delete-btn"
              :aria-label="`Elimina uscita del ${ride.date}`"
              @click.stop="askDelete(ride)"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div
v-if="totalPages > 1" class="pagination"
>
        <button
          class="btn btn-sm btn-secondary"
          :disabled="page === 1"
          :aria-label="t('common.back')"
          @click="page--"
        >
          ← {{ t("common.back") }}
        </button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button
          class="btn btn-sm btn-secondary"
          :disabled="page === totalPages"
          :aria-label="t('common.next')"
          @click="page++"
        >
          {{ t("common.next") }} →
        </button>
      </div>
    </div>

    <!-- Ride detail modal -->
    <transition name="fade">
      <div
        v-if="selectedRide"
        class="modal-overlay"
        @click.self="selectedRide = null"
      >
        <div class="modal-dialog ride-detail-modal">
          <div class="detail-header">
            <h3>🚴 Dettaglio Uscita</h3>
            <button
class="close-btn" @click="selectedRide = null">✕</button>
          </div>
          <div class="detail-date">
            {{ formatDate(selectedRide.date) }}
          </div>
          <div class="detail-grid">
            <div class="detail-stat">
              <div class="ds-val">
                {{ fmt(selectedRide.distance_km) }}
              </div>
              <div class="ds-lbl">km</div>
            </div>
            <div class="detail-stat">
              <div class="ds-val">
                {{ formatDuration(selectedRide.duration_minutes) }}
              </div>
              <div class="ds-lbl">Durata</div>
            </div>
            <div
v-if="selectedRide.avg_speed_kmh" class="detail-stat"
>
              <div class="ds-val">
                {{ fmt(selectedRide.avg_speed_kmh) }}
              </div>
              <div class="ds-lbl">km/h</div>
            </div>
            <div
v-if="selectedRide.elevation_gain_m" class="detail-stat"
>
              <div class="ds-val">
                {{ fmt(selectedRide.elevation_gain_m, 0) }}
              </div>
              <div class="ds-lbl">m salita</div>
            </div>
            <div
v-if="selectedRide.calories" class="detail-stat"
>
              <div class="ds-val">
                {{ fmt(selectedRide.calories, 0) }}
              </div>
              <div class="ds-lbl">kcal</div>
            </div>
            <div
v-if="selectedRide.heart_rate_avg" class="detail-stat"
>
              <div class="ds-val">
                {{ fmt(selectedRide.heart_rate_avg, 0) }}
              </div>
              <div class="ds-lbl">bpm</div>
            </div>
          </div>
          <!-- Analysis -->
          <div v-if="analysis" class="analysis-section">
            <h4>📊 Analisi</h4>
            <div class="analysis-grid">
              <div
v-if="analysis.fatigue_score" class="a-stat"
>
                <span class="a-lbl">Affaticamento</span>
                <div class="a-bar">
                  <div
                    class="a-fill"
                    :style="{
                      width: (analysis.fatigue_score / 10) * 100 + '%',
                      background: fatigueColor(analysis.fatigue_score),
                    }"
                  />
                </div>
                <span class="a-val">{{ fmt(analysis.fatigue_score) }}/10</span>
              </div>
              <div
v-if="analysis.recovery_hours" class="a-item"
>
                <span class="a-lbl">Recupero consigliato</span>
                <span class="a-val accent">{{ analysis.recovery_hours }}h</span>
              </div>
              <div
v-if="analysis.calories_per_km" class="a-item"
>
                <span class="a-lbl">Calorie/km</span>
                <span class="a-val">{{ fmt(analysis.calories_per_km) }}</span>
              </div>
            </div>
          </div>
          <div v-if="analysisLoading" class="loading-text">
            ⏳ Caricamento analisi...
          </div>
          <div class="modal-actions">
            <button
              class="btn btn-sm"
              :disabled="analysisLoading"
              @click="analyzeRide(selectedRide.id)"
            >
              {{ analysisLoading ? "⏳" : "🔬 Analizza" }}
            </button>
            <button
              class="btn btn-sm btn-secondary"
              @click="selectedRide = null"
            >
              Chiudi
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Delete modal -->
    <ConfirmModal
      v-model="showDeleteModal"
      title="Elimina Uscita"
      :message="`Eliminare l'uscita del ${deleteTargetDate}?`"
      confirm-label="Elimina"
      cancel-label="Annulla"
      @confirm="handleDelete"
    />
  </section>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "../composables/useI18n";
import { apiGet, apiDelete, apiPost } from "../utils/api";
import { useAuthStore } from "../stores/auth";
import ConfirmModal from "./ConfirmModal.vue";

const { t } = useI18n();
const auth = useAuthStore();

const emit = defineEmits(["summary-change"]);

const loading = ref(true);
const adding = ref(false);
const addError = ref("");
const rides = ref([]);
const guest = ref(false);
const showForm = ref(false);
const filtersOpen = ref(false);
const selectedRide = ref(null);
const analysis = ref(null);
const analysisLoading = ref(false);
const page = ref(1);
const pageSize = 15;
const sortBy = ref("date_desc");

const form = ref({
  date: new Date().toISOString().slice(0, 10),
  distance_km: "",
  duration_minutes: "",
  avg_speed_kmh: "",
  elevation_gain_m: "",
  calories: "",
});

const filters = ref({ dateFrom: "", dateTo: "", distMin: null, distMax: null });

const showDeleteModal = ref(false);
const deleteTargetId = ref(null);
const deleteTargetDate = ref("");

function fmt(v, dec = 1) {
  if (v == null || isNaN(Number(v))) return "—";
  return Number(v).toFixed(dec);
}

function formatDuration(minutes) {
  const mins = Number(minutes) || 0;
  const h = Math.floor(mins / 60);
  const m = Math.floor(mins % 60);
  const s = Math.floor((mins % 1) * 60);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("it-IT", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function fatigueColor(score) {
  if (score <= 3) return "#00ffcc";
  if (score <= 6) return "#ffb800";
  return "#ff3366";
}

const sortedRides = computed(() => {
  const r = [...rides.value];
  if (sortBy.value === "date_desc")
    return r.sort((a, b) => b.date.localeCompare(a.date));
  if (sortBy.value === "date_asc")
    return r.sort((a, b) => a.date.localeCompare(b.date));
  if (sortBy.value === "distance_desc")
    return r.sort((a, b) => b.distance_km - a.distance_km);
  if (sortBy.value === "speed_desc")
    return r.sort((a, b) => (b.avg_speed_kmh || 0) - (a.avg_speed_kmh || 0));
  return r;
});

const filteredRides = computed(() => {
  let r = sortedRides.value;
  if (filters.value.dateFrom)
    r = r.filter((ride) => ride.date >= filters.value.dateFrom);
  if (filters.value.dateTo)
    r = r.filter((ride) => ride.date <= filters.value.dateTo);
  if (filters.value.distMin != null && filters.value.distMin > 0)
    r = r.filter((ride) => ride.distance_km >= filters.value.distMin);
  if (filters.value.distMax != null && filters.value.distMax > 0)
    r = r.filter((ride) => ride.distance_km <= filters.value.distMax);
  const start = (page.value - 1) * pageSize;
  return r.slice(start, start + pageSize);
});

const totalPages = computed(() =>
  Math.max(1, Math.ceil(sortedRides.value.length / pageSize)),
);

const hasActiveFilters = computed(
  () =>
    filters.value.dateFrom ||
    filters.value.dateTo ||
    filters.value.distMin ||
    filters.value.distMax,
);

function toggleFilters() {
  filtersOpen.value = !filtersOpen.value;
}

function resetFilters() {
  filters.value = { dateFrom: "", dateTo: "", distMin: null, distMax: null };
  page.value = 1;
}

watch(
  filters,
  () => {
    page.value = 1;
  },
  { deep: true },
);

async function load() {
  loading.value = true;
  try {
    const all = [];
    let page = 1;
    const pageSize = 100;
    while (true) {
      const data = await apiGet("/api/v1/rides", {
        page,
        page_size: pageSize,
      });
      const batch = data.rides || [];
      all.push(...batch);
      const total = typeof data.total === "number" ? data.total : all.length;
      if (batch.length === 0 || all.length >= total) break;
      page += 1;
    }
    rides.value = all;
  } catch (e) {
    if (!auth.isLoggedIn) {
      guest.value = true;
      rides.value = [];
    } else {
      console.error("load rides", e);
    }
  } finally {
    loading.value = false;
  }
}

async function handleAdd() {
  adding.value = true;
  addError.value = "";
  try {
    const dist = Number(form.value.distance_km);
    const dur = Number(form.value.duration_minutes);
    if (dist <= 0) {
      addError.value = "La distanza deve essere maggiore di 0";
      return;
    }
    if (dur < 1) {
      addError.value = "La durata deve essere di almeno 1 minuto";
      return;
    }
    if (dur > 1440) {
      addError.value = "La durata non può superare 24 ore";
      return;
    }
    if (dist > 500) {
      addError.value = "La distanza non può superare 500 km";
      return;
    }
    const speed = form.value.avg_speed_kmh
      ? Number(form.value.avg_speed_kmh)
      : undefined;
    if (speed && speed > 150) {
      addError.value = "Velocità nonrealistica (>150 km/h)";
      return;
    }
    await apiPost("/api/v1/rides", {
      date: form.value.date,
      distance_km: dist,
      duration_minutes: dur,
      avg_speed_kmh: speed,
      elevation_gain_m: form.value.elevation_gain_m
        ? Number(form.value.elevation_gain_m)
        : undefined,
      calories: form.value.calories ? Number(form.value.calories) : undefined,
    });
    form.value = {
      date: new Date().toISOString().slice(0, 10),
      distance_km: "",
      duration_minutes: "",
      avg_speed_kmh: "",
      elevation_gain_m: "",
      calories: "",
    };
    showForm.value = false;
    await load();
    emit("summary-change");
  } catch (e) {
    addError.value = e.message;
  } finally {
    adding.value = false;
  }
}

async function openDetail(ride) {
  selectedRide.value = ride;
  analysis.value = null;
  await analyzeRide(ride.id);
}

async function analyzeRide(id) {
  analysisLoading.value = true;
  try {
    const data = await apiGet(`/api/v1/rides/${id}`);
    analysis.value = data;
  } catch (e) {
    console.warn("analyze", e);
  } finally {
    analysisLoading.value = false;
  }
}

function askDelete(ride) {
  deleteTargetId.value = ride.id;
  deleteTargetDate.value = formatDate(ride.date);
  showDeleteModal.value = true;
}

async function handleDelete() {
  if (!deleteTargetId.value) return;
  try {
    await apiDelete(`/api/v1/rides/${deleteTargetId.value}`);
    rides.value = rides.value.filter((r) => r.id !== deleteTargetId.value);
    emit("summary-change");
  } catch (e) {
    console.error("delete", e);
  } finally {
    deleteTargetId.value = null;
    deleteTargetDate.value = "";
  }
}

function exportCSV() {
  const headers = [
    "Date",
    "Distance (km)",
    "Duration (min)",
    "Avg Speed (km/h)",
    "Elevation (m)",
    "Calories",
  ];
  const rows = filteredRides.value.map((r) => [
    r.date,
    r.distance_km,
    r.duration_minutes,
    r.avg_speed_kmh ?? "",
    r.elevation_gain_m ?? "",
    r.calories ?? "",
  ]);
  const csv = [headers.join(","), ...rows.map((row) => row.join(","))].join(
    "\n",
  );
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `rides_export_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(() => load());
</script>

<style scoped>
.rides-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.add-panel {
  cursor: default;
}

.add-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.add-header h2 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--accent);
}
.toggle-icon {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.ride-form {
  margin-top: 18px;
}

/* Slide transition */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.25s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* List header */
.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.list-header h2 {
  margin: 0;
  color: var(--accent);
  font-size: 1.2rem;
}

.ride-count {
  background: var(--accent);
  color: #000;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 20px;
  margin-left: 8px;
}

.list-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sort-select {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
  font-size: 0.85rem;
  font-family: inherit;
  cursor: pointer;
  outline: none;
}

/* Filters */
.filters-panel {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  margin-bottom: 16px;
}

.filters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
}

/* Rides list */
@media (max-width: 768px) {
  .ride-item {
    flex-direction: column;
    align-items: flex-start;
  }
  .ride-right {
    align-self: flex-end;
  }
  .list-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .list-controls {
    width: 100%;
    justify-content: space-between;
  }
  .sort-select {
    flex: 1;
  }
}
</style>
