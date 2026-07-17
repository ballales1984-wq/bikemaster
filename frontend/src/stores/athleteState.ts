import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { AthleteState } from "../types/athlete_state";
import { apiGet, ApiError } from "../utils/api";
import { useAuthStore } from "./auth";

export const useAthleteStateStore = defineStore("athleteState", () => {
  const auth = useAuthStore();
  const state = ref<AthleteState | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastComputedAt = ref<string | null>(null);

  const hasState = computed(() => state.value !== null);
  const readinessPercent = computed(() => state.value?.readiness ?? 0);
  const fatigueLevel = computed(() => state.value?.fatigue_score ?? 0);
  const riskLevel = computed(() => state.value?.risk_level ?? "ok");
  const isOvertrainingRisk = computed(() => state.value?.is_overtraining_risk ?? false);
  const isFresh = computed(() => state.value?.is_fresh ?? false);
  const isReadyForHardEffort = computed(() => state.value?.is_ready_for_hard_effort ?? false);

  async function fetchState(): Promise<AthleteState | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<{ state?: AthleteState } | AthleteState>(
        "/api/v1/athlete/state",
      );
      const resolved: AthleteState | null =
        "state" in data ? data.state ?? null : (data as AthleteState);
      state.value = resolved;
      lastComputedAt.value = resolved?.computed_at ?? null;
      return state.value;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        state.value = null;
        lastComputedAt.value = null;
        return null;
      }
      error.value = e instanceof Error ? e.message : "Failed to load athlete state";
      return null;
    } finally {
      loading.value = false;
    }
  }

  function setState(data: AthleteState) {
    state.value = data;
    lastComputedAt.value = data.computed_at;
  }

  function clearState() {
    state.value = null;
    lastComputedAt.value = null;
    error.value = null;
  }

  return {
    state,
    loading,
    error,
    lastComputedAt,
    hasState,
    readinessPercent,
    fatigueLevel,
    riskLevel,
    isOvertrainingRisk,
    isFresh,
    isReadyForHardEffort,
    fetchState,
    setState,
    clearState,
  };
});
