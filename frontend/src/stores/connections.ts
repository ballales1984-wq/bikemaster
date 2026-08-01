/**
 * BikeMaster Frontend — store connessioni servizi esterni.
 *
 * Tiene traccia dello stato OAuth/API key per servizi come Strava,
 * Google Fit/Wahoo/Garmin, con caricamento e disconnessione.
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiGet } from "../utils/api";
import { useAuthStore } from "./auth";

export type ConnectionMethod = "oauth" | "apikey";

export interface ConnectionStatus {
  service: string;
  method: ConnectionMethod;
  connected: boolean;
  available: boolean;
  label: string;
  description?: string;
  lastConnectedAt?: string | null;
}

export const useConnectionsStore = defineStore("connections", () => {
  const auth = useAuthStore();
  const items = ref<ConnectionStatus[]>([]);
  const loading = ref(false);
  const error = ref("");

  const services = computed(() => items.value);
  const connectedServices = computed(() =>
    items.value.filter((s) => s.connected),
  );

  async function load() {
    loading.value = true;
    error.value = "";
    try {
      const data = await apiGet<{ connections?: ConnectionStatus[] }>(
        "/api/v1/import/providers",
      );
      const mapped = (data.connections || []).map((c) => ({
        service: c.service,
        method: c.method,
        connected: !!c.connected,
        available: c.available !== false,
        label: c.label || c.service,
        description: c.description || "",
        lastConnectedAt: c.lastConnectedAt || null,
      }));
      // Assicurati che i servizi noti siano presenti anche se non tornati dal backend.
      const known = [
        {
          service: "strava",
          method: "oauth" as ConnectionMethod,
          label: "Strava",
        },
        {
          service: "google_fit",
          method: "oauth" as ConnectionMethod,
          label: "Google Fit",
        },
        {
          service: "google_health",
          method: "oauth" as ConnectionMethod,
          label: "Google Health",
        },
        {
          service: "wahoo",
          method: "oauth" as ConnectionMethod,
          label: "Wahoo",
        },
        {
          service: "garmin",
          method: "apikey" as ConnectionMethod,
          label: "Garmin Connect",
        },
      ];
      const merged = known.map((k) => {
        const existing = mapped.find((m) => m.service === k.service);
        return existing || { ...k, connected: false, available: true };
      });
      items.value = merged;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Impossibile caricare le connessioni";
    } finally {
      loading.value = false;
    }
  }

  async function disconnect(service: string) {
    loading.value = true;
    error.value = "";
    try {
      const token = auth.token;
      const resp = await fetch(`/api/v1/import/${service}/disconnect`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(
          (err as { detail?: string }).detail ||
            `Disconnessione ${service} fallita`,
        );
      }
      const target = items.value.find((s) => s.service === service);
      if (target) {
        target.connected = false;
        target.lastConnectedAt = null;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Disconnessione fallita";
    } finally {
      loading.value = false;
    }
  }

  return {
    items,
    loading,
    error,
    services,
    connectedServices,
    load,
    disconnect,
  };
});
