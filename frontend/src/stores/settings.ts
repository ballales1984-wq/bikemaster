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
  getStoredMobileApiBase,
  setStoredMobileApiBase,
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
  const _apiBase = ref(getStoredApiBase());
  const mobileApiBase = ref(getStoredMobileApiBase());
  const fallbackEnabled = ref(isFallbackEnabled());
  const fallbackBase = ref(RENDER_FALLBACK_BASE);

  const backendMode = computed(() => getBackendMode());
  const resolvedBase = computed(() => resolveApiBase());

  const apiBase = computed({
    get: () => {
      if (backendMode.value === "mobile") {
        return mobileApiBase.value;
      }
      return _apiBase.value;
    },
    set: (val: string) => {
      const trimmed = val.trim();
      if (backendMode.value === "mobile") {
        mobileApiBase.value = trimmed;
        setStoredMobileApiBase(trimmed);
      } else {
        _apiBase.value = trimmed;
        setStoredApiBase(trimmed);
      }
    },
  });

  function setUseFallback(enabled: boolean) {
    fallbackEnabled.value = enabled;
    setFallbackEnabled(enabled);
  }

  function resetApiBase() {
    if (backendMode.value === "mobile") {
      mobileApiBase.value = "";
      setStoredMobileApiBase("");
    } else {
      _apiBase.value = "";
      setStoredApiBase("");
    }
  }

  return {
    apiBase,
    mobileApiBase,
    fallbackEnabled,
    fallbackBase,
    backendMode,
    resolvedBase,
    setUseFallback,
    resetApiBase,
  };
});
