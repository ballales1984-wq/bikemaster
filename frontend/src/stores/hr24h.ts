/**
 * BikeMaster Frontend — store tracciamento HR 24h.
 *
 * Gestisce lo stato del monitoraggio continuo della frequenza cardiaca
 * (24h), le impostazioni, l'acquisizione da dispositivi BLE e la
 * persistenza dei campioni sul backend.
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { ApiCallOptions } from "../utils/api";
import { apiGet, apiPost, apiPut, apiDelete } from "../utils/api";
import { useAuthStore } from "./auth";
import type { Hr24hSample, Hr24hSettings, HrDailySummary } from "../types";

export type Hr24hViewHours = 1 | 6 | 12 | 24;

export const useHr24hStore = defineStore("hr24h", () => {
  const auth = useAuthStore();
  const settings = ref<Hr24hSettings>({
    enabled: false,
    interval_seconds: 30,
    source: "ble",
    device_id: null,
    max_hr: null,
    resting_hr: null,
  });
  const samples = ref<Hr24hSample[]>([]);
  const dailyHistory = ref<HrDailySummary[]>([]);
  const todaySummary = ref<HrDailySummary | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const currentHr = computed(
    () => samples.value[samples.value.length - 1]?.heart_rate ?? null,
  );
  const isCollecting = ref(false);

  function _headers(): Record<string, string> {
    const token = auth.token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function loadSettings() {
    if (!auth.isLoggedIn) return;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<Hr24hSettings>("/api/v1/hr/settings", {}, {
        headers: _headers(),
      } as ApiCallOptions);
      settings.value = data;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Errore caricamento impostazioni";
    } finally {
      loading.value = false;
    }
  }

  async function saveSettings(updates: Partial<Hr24hSettings>) {
    if (!auth.isLoggedIn) throw new Error("Non autenticato");
    const merged = { ...settings.value, ...updates };
    settings.value = merged;
    try {
      const data = await apiPut<Hr24hSettings>("/api/v1/hr/settings", merged, {
        headers: _headers(),
      } as ApiCallOptions);
      settings.value = data;
      return data;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Errore salvataggio impostazioni";
      throw e;
    }
  }

  async function enable(updates?: Partial<Hr24hSettings>) {
    await saveSettings({ ...updates, enabled: true });
  }

  async function disable() {
    await saveSettings({ enabled: false });
    isCollecting.value = false;
  }

  async function load24h() {
    if (!auth.isLoggedIn) return;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<{ samples: Hr24hSample[] }>(
        "/api/v1/hr/24h",
        { hours: "24" },
        { headers: _headers() } as ApiCallOptions,
      );
      samples.value = data.samples ?? [];
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Errore caricamento HR 24h";
      samples.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function loadDailyHistory(days = 30) {
    if (!auth.isLoggedIn) return;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<{ history: HrDailySummary[] }>(
        "/api/v1/hr/summary/history",
        { days: String(days) },
        { headers: _headers() } as ApiCallOptions,
      );
      dailyHistory.value = data.history ?? [];
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Errore caricamento storico HR";
      dailyHistory.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function loadTodaySummary() {
    if (!auth.isLoggedIn) return;
    try {
      const data = await apiGet<HrDailySummary | null>(
        "/api/v1/hr/summary",
        {},
        {
          headers: _headers(),
        } as ApiCallOptions,
      );
      todaySummary.value = data;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Errore caricamento riepilogo HR";
    }
  }

  async function logSamples(hrSamples: Hr24hSample[]) {
    if (!auth.isLoggedIn) return 0;
    try {
      const data = await apiPost<{ saved: number }>(
        "/api/v1/hr/samples",
        {
          samples: hrSamples,
          source: settings.value.source,
        },
        { headers: _headers() } as ApiCallOptions,
      );
      return data.saved ?? 0;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Errore salvataggio campioni HR";
      return 0;
    }
  }

  async function deleteOldSamples(olderThan?: string) {
    if (!auth.isLoggedIn) return 0;
    try {
      const params: Record<string, string> = {};
      if (olderThan) params.older_than = olderThan;
      const data = await apiDelete<{ deleted: number }>(
        `/api/v1/hr/samples${olderThan ? `?older_than=${encodeURIComponent(olderThan)}` : ""}`,
        { headers: _headers() } as ApiCallOptions,
      );
      return data.deleted ?? 0;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Errore cancellazione campioni HR";
      return 0;
    }
  }

  return {
    settings,
    samples,
    dailyHistory,
    todaySummary,
    loading,
    error,
    isCollecting,
    currentHr,
    loadSettings,
    saveSettings,
    enable,
    disable,
    load24h,
    loadDailyHistory,
    loadTodaySummary,
    logSamples,
    deleteOldSamples,
  };
});
