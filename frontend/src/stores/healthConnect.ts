/**
 * BikeMaster Frontend — store gestione Android Health Connect.
 *
 * Espone lo stato di connessione Health Connect, le autorizzazioni
 * e la sincronizzazione dei dati sanitari dal sistema Android.
 */

import { defineStore } from "pinia";
import { ref } from "vue";
import type { ApiCallOptions } from "../utils/api";
import { apiGet, apiPost } from "../utils/api";
import { isTauri } from "../utils/backend-config";
import { useAuthStore } from "./auth";

export type HealthConnectPermission =
  | "weight"
  | "height"
  | "heart_rate"
  | "steps"
  | "sleep"
  | "blood_pressure"
  | "activity";

export interface HealthMetric {
  metric_type: string;
  value: number;
  unit?: string | null;
  source?: string;
  recorded_at?: string | null;
}

export interface HealthConnectStatus {
  available: boolean;
  connected: boolean;
  permissions: HealthConnectPermission[];
  lastSyncAt: string | null;
}

export const useHealthConnectStore = defineStore("healthConnect", () => {
  const auth = useAuthStore();
  const status = ref<HealthConnectStatus>({
    available: false,
    connected: false,
    permissions: [],
    lastSyncAt: null,
  });
  const loading = ref(false);
  const error = ref("");

  const permissionLabels: Record<HealthConnectPermission, string> = {
    weight: "Peso",
    height: "Altezza",
    heart_rate: "Frequenza cardiaca",
    steps: "Passi",
    sleep: "Sonno",
    blood_pressure: "Pressione sangue",
    activity: "Attivita'",
  };

  function getPermissionLabel(p: HealthConnectPermission): string {
    return permissionLabels[p] || p;
  }

  async function checkAvailability() {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const providers = await apiGet<Record<string, boolean>>(
        "/api/v1/import/providers",
        {},
        { headers } as ApiCallOptions,
      );
      status.value.available = !!providers.health_connect;
    } catch (e) {
      error.value =
        e instanceof Error
          ? e.message
          : "Impossibile verificare Health Connect";
    } finally {
      loading.value = false;
    }
  }

  async function connect() {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const result = await apiPost<{ status: string; permissions: string[] }>(
        "/api/v1/health-connect/connect",
        {},
        { headers } as ApiCallOptions,
      );
      status.value.connected = result.status === "connected";
      status.value.permissions = (result.permissions ||
        []) as HealthConnectPermission[];
      return result;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Connessione Health Connect fallita";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function disconnect() {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await apiPost("/api/v1/health-connect/disconnect", {}, {
        headers,
      } as ApiCallOptions);
      status.value.connected = false;
      status.value.permissions = [];
      status.value.lastSyncAt = null;
    } catch (e) {
      error.value =
        e instanceof Error
          ? e.message
          : "Disconnessione Health Connect fallita";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function readMetricsTauri(): Promise<HealthMetric[]> {
    const core = await import("@tauri-apps/api/core");
    const result = (await core.invoke("health_connect_read_metrics")) as Record<
      string,
      unknown
    >;
    const metrics: HealthMetric[] = [];
    const map: Record<string, { value: number; unit?: string }> = {
      weight_kg: { value: (result.weight_kg as number) || 0, unit: "kg" },
      heart_rate_bpm: {
        value: (result.heart_rate_bpm as number) || 0,
        unit: "bpm",
      },
      steps: { value: (result.steps as number) || 0, unit: "steps" },
      sleep_hours: {
        value: (result.sleep_hours as number) || 0,
        unit: "hours",
      },
      blood_pressure_systolic: {
        value: (result.blood_pressure_systolic as number) || 0,
        unit: "mmHg",
      },
      activity_minutes: {
        value: (result.activity_minutes as number) || 0,
        unit: "minutes",
      },
    };
    for (const [metric_type, data] of Object.entries(map)) {
      if (data.value > 0) {
        metrics.push({
          metric_type,
          value: data.value,
          unit: data.unit || null,
          source: "health_connect",
          recorded_at: new Date().toISOString(),
        });
      }
    }
    return metrics;
  }

  async function sync(metrics: HealthMetric[] = []) {
    loading.value = true;
    error.value = "";
    try {
      if (metrics.length === 0 && isTauri()) {
        metrics = await readMetricsTauri();
      }
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const result = await apiPost<{ synced: number; connected: boolean }>(
        "/api/v1/health-connect/sync",
        { metrics },
        { headers } as ApiCallOptions,
      );
      status.value.connected = result.connected;
      status.value.lastSyncAt = new Date().toISOString();
      return result;
    } catch (e) {
      error.value =
        e instanceof Error
          ? e.message
          : "Sincronizzazione Health Connect fallita";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  return {
    status,
    loading,
    error,
    permissionLabels,
    checkAvailability,
    connect,
    disconnect,
    sync,
    getPermissionLabel,
  };
});
