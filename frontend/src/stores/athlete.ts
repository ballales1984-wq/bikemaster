/**
 * Athlete profile store.
 *
 * Holds the athlete profile (age, weight, FTP, max HR, etc.),
 * handles loading and updating from the backend.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Athlete } from "../types/index";
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

  const hasProfile = computed(() => profile.value !== null);
  const displayName = computed(() => profile.value?.username || auth.user?.username || "Athlete");

  async function fetchProfile(): Promise<AthleteProfile | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<AthleteProfile>("/api/v1/athletes/me");
      profile.value = data;
      profileComplete.value = true;
      return data;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        // No athlete record yet: create a default one so the user is never
        // stuck on the onboarding screen with an empty state.
        try {
          const created = await apiPut<AthleteProfile>("/api/v1/athletes/me", {
            experience_level: "Beginner",
          });
          profile.value = created;
          profileComplete.value = false;
          return created;
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
      const data = await apiPut<AthleteProfile>("/api/v1/athletes/me", updates);
      profile.value = { ...profile.value, ...data } as AthleteProfile;
      profileComplete.value = true;
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
    hasProfile,
    displayName,
    fetchProfile,
    updateProfile,
    setProfile,
    clearProfile,
  };
});
