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
import { useAuthStore } from "./auth";

export type HealthConnectPermission =
  | "weight"
  | "height"
  | "heart_rate"
  | "steps"
  | "sleep"
  | "blood_pressure"
  | "activity";

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

  async function sync() {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const result = await apiPost<{ synced: number }>(
        "/api/v1/health-connect/sync",
        {},
        { headers } as ApiCallOptions,
      );
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
