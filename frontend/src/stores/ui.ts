import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const useUIStore = defineStore("ui", () => {
  const isDark = ref(true);

  const oauthLoading = ref(
    typeof sessionStorage !== "undefined"
      ? sessionStorage.getItem("bikemaster_oauth_loading") === "true"
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
        sessionStorage.setItem("bikemaster_oauth_loading", "true");
      } else {
        sessionStorage.removeItem("bikemaster_oauth_loading");
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
