import { defineStore } from "pinia";
import { ref } from "vue";
import { apiGet } from "../utils/api";

const REFRESH_INTERVAL_MS = 5000;
const MIN_REFRESH_INTERVAL_MS = 1000;

export const useMonitoringStore = defineStore("monitoring", () => {
  const health = ref<Record<string, unknown> | null>(null);
  const loading = ref(false);
  const error = ref("");
  const lastUpdated = ref("");
  const refreshTimer = ref<number | null>(null);

  async function fetchHealth() {
    loading.value = true;
    error.value = "";
    try {
      const data = await apiGet<Record<string, unknown>>(
        "/api/v1/health/comprehensive",
      );
      health.value = data;
      lastUpdated.value = new Date().toLocaleTimeString();
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    const interval = Math.max(REFRESH_INTERVAL_MS, MIN_REFRESH_INTERVAL_MS);
    refreshTimer.value = window.setInterval(() => {
      void fetchHealth();
    }, interval);
  }

  function stopAutoRefresh() {
    if (refreshTimer.value !== null) {
      clearInterval(refreshTimer.value);
      refreshTimer.value = null;
    }
  }

  return {
    health,
    loading,
    error,
    lastUpdated,
    refreshTimer,
    fetchHealth,
    startAutoRefresh,
    stopAutoRefresh,
  };
});
