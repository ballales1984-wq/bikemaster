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
// L'URL è modificabile a runtime dall'utente (es. punta al proprio PC) e
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
