/**
 * Store dell'interfaccia utente.
 *
 * Gestisce tema (chiaro/scuro), sidebar collassata, stato OAuth
 * in caricamento e flag per AetherMap.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { AUTH_OAUTH_LOADING_KEY } from "../utils/auth-storage";

export const useUIStore = defineStore("ui", () => {
  const isDark = ref(true);

  const oauthLoading = ref(
    typeof sessionStorage !== "undefined"
      ? sessionStorage.getItem(AUTH_OAUTH_LOADING_KEY) === "true"
      : false,
  );
  const sidebarCollapsed = ref(false);

  const useAetherMap = ref(
    typeof import.meta !== "undefined" &&
      (import.meta as ImportMeta).env?.VITE_AETHERMAP_ENABLED === "true",
  );
  const theme = computed({
    get: () => (isDark.value ? "dark" : "light"),
    set: (val: string) => {
      isDark.value = val === "dark";
    },
  });

  function loadTheme() {
    const saved = localStorage.getItem("bikemaster_theme");
    isDark.value = saved !== "light";
  }

  function toggleTheme() {
    isDark.value = !isDark.value;
    localStorage.setItem("bikemaster_theme", isDark.value ? "dark" : "light");
  }

  function setOauthLoading(value: boolean) {
    oauthLoading.value = value;
    if (typeof sessionStorage !== "undefined") {
      if (value) {
        sessionStorage.setItem(AUTH_OAUTH_LOADING_KEY, "true");
      } else {
        sessionStorage.removeItem(AUTH_OAUTH_LOADING_KEY);
      }
    }
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  }

  return {
    isDark,
    oauthLoading,
    sidebarCollapsed,
    theme,
    loadTheme,
    toggleTheme,
    setOauthLoading,
    toggleSidebar,
    useAetherMap,
  };
});
