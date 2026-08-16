/**
 * Store delle impostazioni di connessione backend.
 *
 * Il backend URL &egrave; fissato a build-time tramite VITE_API_BASE
 * per motivi di sicurezza: non &egrave; modificabile a runtime.
 * Render &egrave; il backend di produzione con fallback opzionale.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  isFallbackEnabled,
  setFallbackEnabled,
  resolveApiBase,
  getBackendMode,
  RENDER_FALLBACK_BASE,
} from "../utils/backend-config";

export const useSettingsStore = defineStore("settings", () => {
  const fallbackEnabled = ref(isFallbackEnabled());
  const fallbackBase = ref(RENDER_FALLBACK_BASE);

  const backendMode = computed(() => getBackendMode());
  const resolvedBase = computed(() => resolveApiBase());

  function setUseFallback(enabled: boolean) {
    fallbackEnabled.value = enabled;
    setFallbackEnabled(enabled);
  }

  return {
    fallbackEnabled,
    fallbackBase,
    backendMode,
    resolvedBase,
    setUseFallback,
  };
});
