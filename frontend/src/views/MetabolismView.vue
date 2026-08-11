<template>
  <div class="panel">
    <h2>Metabolismo</h2>
    <div v-if="loading" class="loading">Caricamento...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else>
      <MetabolismPanel />
      <div class="section-divider" />
      <FoodLogPanel :date="selectedDate" />
      <div class="section-divider" />
      <MetabolicCharts :summaries="rangeSummaries" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useMetabolismStore } from "../stores/metabolism";
import MetabolismPanel from "../components/MetabolismPanel.vue";
import FoodLogPanel from "../components/FoodLogPanel.vue";
import MetabolicCharts from "../components/MetabolicCharts.vue";

const store = useMetabolismStore();
const loading = ref(true);
const error = ref<string | null>(null);
const selectedDate = ref(new Date().toISOString().slice(0, 10));
const rangeSummaries = ref<any[]>([]);

onMounted(async () => {
  const auth = useAuthStore();
  if (!auth.isLoggedIn) {
    error.value = "Sessione scaduta. Effettua di nuovo il login.";
    loading.value = false;
    return;
  }
  try {
    await store.fetchProfile();
    await store.fetchFoodLogs(selectedDate.value);
    await store.fetchDailySummary(selectedDate.value);
    const end = selectedDate.value;
    const start = new Date(new Date(end).getTime() - 30 * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10);
    const range = await store.fetchRangeSummary(start, end);
    rangeSummaries.value = range;
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Errore caricamento metabolismo";
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
