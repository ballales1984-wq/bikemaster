/**
 * Athlete profile store.
 *
 * Holds the athlete profile (age, weight, FTP, max HR, etc.),
 * handles loading and updating from the backend.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Athlete, AthleteMetricLogEntry, AthleteMetricLogResponse } from "../types/index";
import { apiGet, apiPut, ApiError } from "../utils/api";
import { useAuthStore } from "./auth";

export interface AthleteProfile extends Athlete {
  name?: string;
  age?: number;
  weight_kg?: number;
  height_cm?: number;
  ftp?: number;
  ftp_watts?: number;
  max_hr?: number;
  resting_hr?: number;
  fat_percentage?: number;
  years_active?: number;
  weekly_sessions?: number;
  monthly_hours?: number;
  annual_hours?: number;
  experience_level?: string;
  goals?: string | null;
  preferred_terrain?: string | null;
  weekly_volume_km?: number;
  best_segments?: string | null;
  medical_notes?: string | null;
  equipment?: string | null;
}

export const useAthleteStore = defineStore("athlete", () => {
  const auth = useAuthStore();
  const profile = ref<AthleteProfile | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref<string | null>(null);
  const profileComplete = ref(false);
  const metricLog = ref<Record<string, AthleteMetricLogEntry[]>>({});
  const metricLogLoading = ref(false);

  const hasProfile = computed(() => profile.value !== null);
  const displayName = computed(() => profile.value?.username || auth.user?.username || "Athlete");

  async function fetchProfile(): Promise<AthleteProfile | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<{ athlete: AthleteProfile; profile_complete: boolean }>("/api/v1/athletes/me");
      profile.value = data.athlete;
      profileComplete.value = data.profile_complete;
      return data.athlete;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        try {
          const created = await apiPut<{ athlete: AthleteProfile; profile_complete: boolean }>("/api/v1/athletes/me", {
            experience_level: "Beginner",
          });
          profile.value = created.athlete;
          profileComplete.value = created.profile_complete;
          return created.athlete;
        } catch {
          profile.value = null;
          profileComplete.value = false;
          return null;
        }
      }
      error.value = e instanceof Error ? e.message : "Failed to load profile";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateProfile(
    updates: Partial<AthleteProfile>,
  ): Promise<AthleteProfile> {
    if (!auth.isLoggedIn) throw new Error("Not authenticated");
    saving.value = true;
    error.value = null;
    try {
      const data = await apiPut<{ athlete: AthleteProfile; profile_complete: boolean }>("/api/v1/athletes/me", updates);
      profile.value = data.athlete;
      profileComplete.value = data.profile_complete;
      return profile.value;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to update profile";
      throw e;
    } finally {
      saving.value = false;
    }
  }

  function setProfile(data: AthleteProfile) {
    profile.value = data;
    profileComplete.value = true;
  }

  async function fetchMetricLog(metricType: string, days = 365): Promise<AthleteMetricLogEntry[]> {
    if (!auth.isLoggedIn) return [];
    metricLogLoading.value = true;
    error.value = null;
    try {
      const data = await apiGet<AthleteMetricLogResponse>("/api/v1/athletes/me/metric-log", {
        metric_type: metricType,
        days: String(days),
      });
      const series = data.series ?? [];
      metricLog.value[metricType] = series;
      return series;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load metric history";
      return [];
    } finally {
      metricLogLoading.value = false;
    }
  }

  function clearProfile() {
    profile.value = null;
    profileComplete.value = false;
    error.value = null;
  }

  return {
    profile,
    loading,
    saving,
    error,
    profileComplete,
    metricLog,
    metricLogLoading,
    hasProfile,
    displayName,
    fetchProfile,
    updateProfile,
    fetchMetricLog,
    setProfile,
    clearProfile,
  };
});
