/**
 * Store delle impostazioni di connessione backend.
 *
 * Permette di configurare l'URL del backend locale (es. PC utente)
 * e l'eventuale fallback su Render, con persistenza in localStorage.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  getStoredApiBase,
  setStoredApiBase,
  isFallbackEnabled,
  setFallbackEnabled,
  resolveApiBase,
  getBackendMode,
  RENDER_FALLBACK_BASE,
} from "../utils/backend-config";

// Store delle impostazioni di connessione al backend.
// The URL is modifiable at runtime by the user (e.g. points to their own PC) and
// persistito in localStorage. Render resta un failover opzionale.
export const useSettingsStore = defineStore("settings", () => {
  const apiBase = ref(getStoredApiBase());
  const fallbackEnabled = ref(isFallbackEnabled());
  const fallbackBase = ref(RENDER_FALLBACK_BASE);

  const backendMode = computed(() => getBackendMode());
  const resolvedBase = computed(() => resolveApiBase());

  function setApiBase(url: string) {
    apiBase.value = url.trim();
    setStoredApiBase(apiBase.value);
  }

  function setUseFallback(enabled: boolean) {
    fallbackEnabled.value = enabled;
    setFallbackEnabled(enabled);
  }

  function resetApiBase() {
    apiBase.value = "";
    setStoredApiBase("");
  }

  return {
    apiBase,
    fallbackEnabled,
    fallbackBase,
    backendMode,
    resolvedBase,
    setApiBase,
    setUseFallback,
    resetApiBase,
  };
});
