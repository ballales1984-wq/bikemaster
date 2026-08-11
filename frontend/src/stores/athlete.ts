/**
 * Athlete profile store.
 *
 * Holds the athlete profile (age, weight, FTP, max HR, etc.),
 * handles loading and updating from the backend.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type {
  Athlete,
  AthleteMetricLogEntry,
  AthleteMetricLogResponse,
} from "../types/index";
import { apiGet, apiPut } from "../utils/api";
import { useAuthStore } from "./auth";

export interface AthleteProfile extends Athlete {
  name?: string;
  age?: number;
  weight_kg?: number;
  height_cm?: number;
  ftp_watts?: number;
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
  body_water_percentage?: number;
  muscle_mass_percentage?: number;
  bmr_kcal?: number;
  fat_mass_kg?: number;
  subcutaneous_fat_kg?: number;
  subcutaneous_fat_percentage?: number;
  visceral_fat_level?: number;
  visceral_fat_percentage?: number;
  visceral_fat_kg?: number;
  muscle_mass_kg?: number;
  bone_mass_kg?: number;
  protein_percentage?: number;
  protein_kg?: number;
  body_age?: number;
  apparent_age?: number;
  bmi?: number | null;
  lean_body_mass_kg?: number | null;
  max_hr?: number | null;
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
  const displayName = computed(
    () => profile.value?.username || auth.user?.username || "Athlete",
  );

  async function fetchProfile(): Promise<AthleteProfile | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<{
        athlete: AthleteProfile | null;
        profile_complete: boolean;
      }>("/api/v1/athletes/me");
      profile.value = data.athlete;
      profileComplete.value = data.profile_complete;
      return data.athlete;
    } catch (e) {
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
      const data = await apiPut<{
        athlete: AthleteProfile;
        profile_complete: boolean;
      }>("/api/v1/athletes/me", updates);
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

  async function fetchMetricLog(
    metricType: string,
    days = 365,
  ): Promise<AthleteMetricLogEntry[]> {
    if (!auth.isLoggedIn) return [];
    metricLogLoading.value = true;
    error.value = null;
    try {
      const data = await apiGet<AthleteMetricLogResponse>(
        "/api/v1/athletes/me/metric-log",
        {
          metric_type: metricType,
          days: String(days),
        },
      );
      const series = data.series ?? [];
      metricLog.value[metricType] = series;
      return series;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to load metric history";
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
