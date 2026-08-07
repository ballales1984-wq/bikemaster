/**
 * Store performance: metriche di potenza (NP/IF/TSS) e storico FTP.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type {
  PerformanceMetrics,
  FtpRecord,
  FtpHistoryResponse,
  PowerComputeResult,
} from "../types/index";
import { apiGet, apiPost } from "../utils/api";
import { useAuthStore } from "./auth";

export const usePerformanceStore = defineStore("performance", () => {
  const auth = useAuthStore();
  const metrics = ref<PerformanceMetrics[]>([]);
  const ftpHistory = ref<FtpRecord[]>([]);
  const latestFtp = ref<number | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref<string | null>(null);

  const hasData = computed(
    () => metrics.value.length > 0 || ftpHistory.value.length > 0,
  );

  async function fetchMetrics(rideId?: number): Promise<PerformanceMetrics[]> {
    if (!auth.isLoggedIn) return [];
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<{
        athlete_id: number;
        metrics: PerformanceMetrics[];
      }>(
        "/api/v1/performance/metrics",
        rideId != null ? { ride_id: String(rideId) } : {},
      );
      metrics.value = data.metrics || [];
      return metrics.value;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to load performance metrics";
      return [];
    } finally {
      loading.value = false;
    }
  }

  async function fetchFtpHistory(): Promise<FtpHistoryResponse | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<FtpHistoryResponse>("/api/v1/performance/ftp");
      ftpHistory.value = data.history || [];
      latestFtp.value = data.latest_ftp ?? null;
      return data;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to load FTP history";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function recordFtp(payload: {
    ftp_watts: number;
    date?: string | null;
    source?: string;
    note?: string | null;
  }): Promise<FtpRecord> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    saving.value = true;
    error.value = null;
    try {
      const data = await apiPost<FtpRecord>("/api/v1/performance/ftp", payload);
      const idx = ftpHistory.value.findIndex((f) => f.date === data.date);
      if (idx >= 0) {
        ftpHistory.value[idx] = data;
      } else {
        ftpHistory.value.push(data);
      }
      ftpHistory.value.sort((a, b) => a.date.localeCompare(b.date));
      latestFtp.value = data.ftp_watts;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to record FTP";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  async function estimateFtp(payload: {
    test_power: number;
    test_duration_min?: number;
    ftp_fraction?: number;
  }): Promise<number> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    error.value = null;
    try {
      const data = await apiPost<{ estimated_ftp: number }>(
        "/api/v1/performance/ftp/estimate",
        payload,
      );
      return data.estimated_ftp;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to estimate FTP";
      throw e;
    }
  }

  async function computeRide(
    rideId: number,
  ): Promise<PerformanceMetrics | null> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    saving.value = true;
    error.value = null;
    try {
      const data = await apiPost<{
        ride_id: number;
        metrics: PerformanceMetrics;
      }>(`/api/v1/performance/ride/${rideId}/compute`, {});
      const m = data.metrics;
      const idx = metrics.value.findIndex((x) => x.ride_id === rideId);
      if (idx >= 0) {
        metrics.value[idx] = m;
      } else {
        metrics.value.push(m);
      }
      return m;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to compute ride metrics";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  async function computeFromStream(payload: {
    power_stream: number[];
    duration_seconds?: number | null;
    ftp?: number | null;
  }): Promise<PowerComputeResult> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    error.value = null;
    try {
      const data = await apiPost<PowerComputeResult>(
        "/api/v1/performance/compute",
        payload,
      );
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to compute power";
      throw e;
    }
  }

  // NOTE: `duration_seconds` is in SECONDS because the backend
  // `/api/v1/performance/compute` endpoint expects seconds for the
  // power-stream analysis. This is distinct from ride `duration_minutes`
  // used elsewhere in the app.

  async function recomputeAll(): Promise<number> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    saving.value = true;
    error.value = null;
    try {
      const data = await apiPost<{
        processed: number;
        metrics: PerformanceMetrics[];
      }>("/api/v1/performance/recompute", {});
      metrics.value = data.metrics || [];
      return data.processed;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to recompute";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  function clear() {
    metrics.value = [];
    ftpHistory.value = [];
    latestFtp.value = null;
    error.value = null;
  }

  return {
    metrics,
    ftpHistory,
    latestFtp,
    loading,
    saving,
    error,
    hasData,
    fetchMetrics,
    fetchFtpHistory,
    recordFtp,
    estimateFtp,
    computeRide,
    computeFromStream,
    recomputeAll,
    clear,
  };
});
