import { ref } from "vue";
import { apiPost } from "../utils/api";
import type { Bm2Answer, Bm2AskPayload } from "../types/bm2";

/**
 * Composable per interrogare il motore BikeMaster 2.0 (AI Orchestrator).
 * Segue le stesse convenzioni di useRides: usa apiPost di utils/api.ts.
 */
export function useBm2() {
  const answer = ref<Bm2Answer | null>(null);
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

  return { answer, loading, error, ask, simulate };
}
