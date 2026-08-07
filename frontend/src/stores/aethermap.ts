import { defineStore } from "pinia";
import { ref } from "vue";
import type { Ride } from "../types/index";
import { apiGet } from "../utils/api";

export const useAetherMapStore = defineStore("aethermap", () => {
  const rides = ref<Ride[]>([]);
  const selectedIds = ref<number[]>([]);
  const loading = ref(false);
  const colorBySpeed = ref(true);

  async function fetchRides() {
    loading.value = true;
    try {
      const data = await apiGet<{ rides: Ride[] }>("/api/v1/rides", {
        page_size: "200",
      });
      rides.value = data.rides || [];
      if (rides.value.length) {
        selectedIds.value = [rides.value[0].id];
      }
    } catch (e) {
      console.error("Failed to load rides for aethermap", e);
    } finally {
      loading.value = false;
    }
  }

  function selectAll() {
    selectedIds.value = rides.value.map((r) => r.id);
  }

  function clearAll() {
    selectedIds.value = [];
  }

  return {
    rides,
    selectedIds,
    loading,
    colorBySpeed,
    fetchRides,
    selectAll,
    clearAll,
  };
});
