<template>
  <div class="panel">
    <h2>Analisi Prestazioni</h2>
    <div v-if="loading" class="loading">Caricamento...</div>
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    <template v-else>
      <PerformancePanel />
      <div class="section-divider" />
      <PowerMetricsTable
        :metrics="metrics"
        :loading="recomputing"
        @recompute="onRecompute"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { usePerformanceStore } from "../stores/performance";
import PerformancePanel from "../components/PerformancePanel.vue";
import PowerMetricsTable from "../components/PowerMetricsTable.vue";

const store = usePerformanceStore();
const loading = ref(true);
const recomputing = ref(false);
const error = ref<string | null>(null);
const metrics = ref(store.metrics);

async function onRecompute() {
  recomputing.value = true;
  try {
    await store.recomputeAll();
    metrics.value = store.metrics;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Errore ricalcolo";
  } finally {
    recomputing.value = false;
  }
}

onMounted(async () => {
  try {
    await store.fetchMetrics();
    await store.fetchFtpHistory();
    metrics.value = store.metrics;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Errore caricamento";
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.loading {
  padding: 1rem;
  color: var(--text-muted);
}
.error {
  padding: 1rem;
  color: #b91c1c;
}
.section-divider {
  height: 1px;
  background: var(--border);
  margin: 1.5rem 0;
}
</style>
