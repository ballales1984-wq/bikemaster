/**
 * Store metabolismo: profilo metabolico, log alimentari, riepiloghi giornalieri.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { MetabolicProfile, FoodLog, MetabolicDailySummary } from "../types/index";
import { apiGet, apiPut, apiPost, apiDelete, ApiError } from "../utils/api";
import { useAuthStore } from "./auth";

export const useMetabolismStore = defineStore("metabolism", () => {
  const auth = useAuthStore();
  const profile = ref<MetabolicProfile | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref<string | null>(null);
  const todaySummary = ref<MetabolicDailySummary | null>(null);
  const rangeSummaries = ref<MetabolicDailySummary[]>([]);
  const foodLogs = ref<FoodLog[]>([]);

  const bmr = computed(() => profile.value?.bmr_kcal ?? 0);
  const tdee = computed(() => profile.value?.tdee_kcal ?? 0);
  const intake = computed(() => foodLogs.value.reduce((sum, f) => sum + (f.kcal || 0), 0));
  const balance = computed(() => intake.value - (todaySummary.value?.tdee_kcal || 0));

  async function fetchProfile(): Promise<MetabolicProfile | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<MetabolicProfile>("/api/v1/metabolism/profile");
      profile.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load metabolic profile";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateProfile(updates: Partial<MetabolicProfile>): Promise<MetabolicProfile> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    saving.value = true;
    error.value = null;
    try {
      const data = await apiPut<MetabolicProfile>("/api/v1/metabolism/profile", updates);
      profile.value = { ...profile.value, ...data } as MetabolicProfile;
      return profile.value;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to update profile";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  async function fetchFoodLogs(date: string): Promise<FoodLog[]> {
    if (!auth.isLoggedIn) return [];
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<FoodLog[]>(`/api/v1/metabolism/food-log?date=${encodeURIComponent(date)}`);
      foodLogs.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load food logs";
      return [];
    } finally {
      loading.value = false;
    }
  }

  async function createFoodLog(log: Partial<FoodLog>): Promise<FoodLog> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    saving.value = true;
    error.value = null;
    try {
      const data = await apiPost<FoodLog>("/api/v1/metabolism/food-log", log);
      foodLogs.value.push(data);
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to create food log";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  async function updateFoodLog(logId: number, updates: Partial<FoodLog>): Promise<FoodLog> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    saving.value = true;
    error.value = null;
    try {
      const data = await apiPut<FoodLog>(`/api/v1/metabolism/food-log/${logId}`, updates);
      const idx = foodLogs.value.findIndex((f) => f.id === logId);
      if (idx >= 0) {
        foodLogs.value[idx] = data;
      }
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to update food log";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  async function removeFoodLog(logId: number): Promise<void> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    saving.value = true;
    error.value = null;
    try {
      await apiDelete(`/api/v1/metabolism/food-log/${logId}`);
      foodLogs.value = foodLogs.value.filter((f) => f.id !== logId);
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete food log";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  async function fetchDailySummary(date: string): Promise<MetabolicDailySummary | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<MetabolicDailySummary>(
        `/api/v1/metabolism/daily-summary?date=${encodeURIComponent(date)}`
      );
      todaySummary.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load daily summary";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function fetchRangeSummary(startDate: string, endDate: string): Promise<MetabolicDailySummary[]> {
    if (!auth.isLoggedIn) return [];
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<MetabolicDailySummary[]>(
        `/api/v1/metabolism/range-summary?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
      );
      rangeSummaries.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load range summary";
      return [];
    } finally {
      loading.value = false;
    }
  }

  async function recalculateSummary(date: string): Promise<MetabolicDailySummary | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiPost<MetabolicDailySummary>(
        `/api/v1/metabolism/recalculate?date=${encodeURIComponent(date)}`,
        {}
      );
      todaySummary.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to recalculate summary";
      return null;
    } finally {
      loading.value = false;
    }
  }

  function clear() {
    profile.value = null;
    todaySummary.value = null;
    rangeSummaries.value = [];
    foodLogs.value = [];
    error.value = null;
  }

  return {
    profile,
    loading,
    saving,
    error,
    todaySummary,
    rangeSummaries,
    foodLogs,
    bmr,
    tdee,
    intake,
    balance,
    fetchProfile,
    updateProfile,
    fetchFoodLogs,
    createFoodLog,
    updateFoodLog,
    removeFoodLog,
    fetchDailySummary,
    fetchRangeSummary,
    recalculateSummary,
    clear,
  };
});
