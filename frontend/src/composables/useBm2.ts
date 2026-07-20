/**
 * Composable to query the BikeMaster 2.0 engine (AI Orchestrator).
 * Exposes `ask`/`simulate` calls (questions), `simulateRide` (a "what if"
 * scenario on a ride) and `validate` (physical kernel vs power-meter), with
 * reactive states `answer`, `rideSimulation`, `validation`, `loading`, `error`.
 */
import { ref } from "vue";
import { apiPost } from "../utils/api";
import type {
  Bm2Answer,
  Bm2AskPayload,
  Bm2SimulateRidePayload,
  Bm2SimulateRideResult,
  Bm2ValidatePayload,
  Bm2ValidateResult,
} from "../types/bm2";

/**
 * Composable to query the BikeMaster 2.0 engine (AI Orchestrator).
 * Follows the same conventions as useRides: uses apiPost from utils/api.ts.
 */
export function useBm2() {
  const answer = ref<Bm2Answer | null>(null);
  const rideSimulation = ref<Bm2SimulateRideResult | null>(null);
  const validation = ref<Bm2ValidateResult | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function ask(payload: Bm2AskPayload): Promise<Bm2Answer | null> {
    loading.value = true;
    error.value = null;
    try {
      const data = (await apiPost<Bm2Answer>(
        "/api/v1/bm2/ask",
        payload,
      )) as Bm2Answer;
      answer.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Errore di analisi";
      answer.value = null;
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function simulate(payload: Bm2AskPayload): Promise<Bm2Answer | null> {
    loading.value = true;
    error.value = null;
    try {
      const data = (await apiPost<Bm2Answer>(
        "/api/v1/bm2/simulate",
        payload,
      )) as Bm2Answer;
      answer.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Errore di simulazione";
      answer.value = null;
      return null;
    } finally {
      loading.value = false;
    }
  }

  /** Scenario "what if" su una Ride reale (per ride_id o gps_points inline). */
  async function simulateRide(
    payload: Bm2SimulateRidePayload,
  ): Promise<Bm2SimulateRideResult | null> {
    loading.value = true;
    error.value = null;
    try {
      const data = (await apiPost<Bm2SimulateRideResult>(
        "/api/v1/bm2/simulate-ride",
        payload,
      )) as Bm2SimulateRideResult;
      rideSimulation.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Errore di simulazione ride";
      rideSimulation.value = null;
      return null;
    } finally {
      loading.value = false;
    }
  }

  /** Valida il kernel fisico contro i power-meter di una Ride reale. */
  async function validate(
    payload: Bm2ValidatePayload,
  ): Promise<Bm2ValidateResult | null> {
    loading.value = true;
    error.value = null;
    try {
      const data = (await apiPost<Bm2ValidateResult>(
        "/api/v1/bm2/validate",
        payload,
      )) as Bm2ValidateResult;
      validation.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Errore di validazione";
      validation.value = null;
      return null;
    } finally {
      loading.value = false;
    }
  }

  return {
    answer,
    rideSimulation,
    validation,
    loading,
    error,
    ask,
    simulate,
    simulateRide,
    validate,
  };
}
