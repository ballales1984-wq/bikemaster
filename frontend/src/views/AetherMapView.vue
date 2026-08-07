<!--
  Vista di visualizzazione AetherMap.
  Allows selecting one or more rides from a sidebar and visualizing them
  sovrapposte nella mappa del componente AetherMapViewer.
  Includes speed coloring option and bulk selections.
  Componente: AetherMapViewer.
-->
<template>
  <section class="panel aethermap-page">
    <div class="aethermap-header">
      <div>
        <h2>{{ t("aethermap.title") }}</h2>
        <p class="aethermap-subtitle">
          {{ t("aethermap.subtitle") }}
        </p>
      </div>
      <div class="aethermap-actions">
        <button
          class="btn btn-secondary"
          :disabled="!rides.length"
          @click="selectAll"
        >
          {{ t("aethermap.selectAll") }}
        </button>
        <button
          class="btn btn-secondary"
          :disabled="!selectedIds.length"
          @click="clearAll"
        >
          {{ t("aethermap.clear") }}
        </button>
        <label class="checkbox-control aethermap-color">
          <input v-model="colorBySpeed" type="checkbox" />
          <span>{{ t("aethermap.colorBySpeed") }}</span>
        </label>
      </div>
    </div>

    <div class="aethermap-body">
      <aside class="aethermap-sidebar">
        <div class="aethermap-sidebar-head">
          <span>{{ t("aethermap.rides") }}</span>
          <span class="aethermap-count"
            >{{ selectedIds.length }}/{{ rides.length }}</span
          >
        </div>
        <div v-if="loading" class="aethermap-loading">
          <span class="spinner" /> {{ t("aethermap.loading") }}
        </div>
        <ul v-else-if="rides.length" class="aethermap-ride-list">
          <li v-for="ride in rides" :key="ride.id" class="aethermap-ride-item">
            <label class="checkbox-control">
              <input v-model="selectedIds" type="checkbox" :value="ride.id" />
              <span class="aethermap-ride-name">{{
                ride.title || ride.date
              }}</span>
            </label>
            <span class="aethermap-ride-meta">{{ formatDistance(ride) }}</span>
          </li>
        </ul>
        <p v-else class="aethermap-empty">{{ t("aethermap.noRides") }}</p>
      </aside>

      <div class="aethermap-stage">
        <AetherMapViewer
          :ride-ids="selectedIds"
          :color-by-speed="colorBySpeed"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "../composables/useI18n";
import { useRides } from "../composables/useRides";
import AetherMapViewer from "../components/AetherMapViewer.vue";
import type { Ride } from "../types/index";

const { t } = useI18n();
const { fetchSummary } = useRides();

const rides = ref<Ride[]>([]);
const selectedIds = ref<number[]>([]);
const loading = ref(false);
const colorBySpeed = ref(true);

function formatDistance(ride: Ride): string {
  const km = ride.distance_km;
  if (!km) return "";
  return `${km.toFixed(1)} km`;
}

function selectAll() {
  selectedIds.value = rides.value.map((r) => r.id);
}
function clearAll() {
  selectedIds.value = [];
}

onMounted(async () => {
  loading.value = true;
  try {
    const data = await fetchSummary();
    rides.value = data.ridesList ?? [];
    if (rides.value.length) {
      selectedIds.value = [rides.value[0].id];
    }
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.aethermap-page {
  display: flex;
  flex-direction: column;
}
.aethermap-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.aethermap-subtitle {
  margin: 6px 0 0;
  color: var(--text-secondary);
  max-width: 720px;
}
.aethermap-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.aethermap-color {
  min-height: 42px;
}
.aethermap-body {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
}
.aethermap-sidebar {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-secondary);
  padding: 12px;
  overflow-y: auto;
  max-height: 70vh;
}
.aethermap-sidebar-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--text-primary);
}
.aethermap-count {
  font-size: 0.8rem;
  color: var(--text-muted);
}
.aethermap-ride-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.aethermap-ride-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
}
.aethermap-ride-item:hover {
  border-color: var(--border);
  background: var(--bg-primary);
}
.aethermap-ride-name {
  color: var(--text-primary);
}
.aethermap-ride-meta {
  font-size: 0.78rem;
  color: var(--text-muted);
  padding-left: 24px;
}
.aethermap-loading,
.aethermap-empty {
  color: var(--text-secondary);
  font-size: 0.9rem;
  padding: 8px 4px;
}
.aethermap-stage {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  min-height: 560px;
  height: 70vh;
}
@media (max-width: 768px) {
  .aethermap-body {
    grid-template-columns: 1fr;
  }
  .aethermap-stage {
    height: 60vh;
    min-height: 360px;
  }
}
</style>
