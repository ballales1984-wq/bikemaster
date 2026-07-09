import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const useUIStore = defineStore("ui", () => {
  const isDark = ref(true);

  const oauthLoading = ref(false);
  const sidebarCollapsed = ref(false);

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
  };
});
