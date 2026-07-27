/**
 * Store degli itinerari (tour multi-giorno, tappe).
 *
 * Carica/crea itinerari e tappe dell'atleta autenticato via API.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiGet, apiPost } from "../utils/api";
import type { Itinerary, Stage } from "../types/index";

export const useItineraryStore = defineStore("itinerary", () => {
  const itineraries = ref<Itinerary[]>([]);
  const current = ref<{ itinerary: Itinerary; stages: Stage[] } | null>(null);
  const loading = ref(false);
  const error = ref("");

  async function loadList() {
    loading.value = true;
    error.value = "";
    try {
      const data = await apiGet<{ itineraries: Itinerary[] }>(
        "/api/v1/itineraries",
      );
      itineraries.value = data.itineraries || [];
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Caricamento fallito";
    } finally {
      loading.value = false;
    }
  }

  async function loadOne(id: number) {
    loading.value = true;
    error.value = "";
    try {
      const data = await apiGet<{ itinerary: Itinerary; stages: Stage[] }>(
        `/api/v1/itineraries/${id}`,
      );
      current.value = data;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Caricamento fallito";
    } finally {
      loading.value = false;
    }
  }

  async function create(payload: Partial<Itinerary>): Promise<number | null> {
    error.value = "";
    try {
      const data = await apiPost<{ id: number } & Partial<Itinerary>>(
        "/api/v1/itineraries",
        payload,
      );
      await loadList();
      return data.id ?? null;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Creazione fallita";
      return null;
    }
  }

  async function addStage(
    itineraryId: number,
    payload: Partial<Stage>,
  ): Promise<boolean> {
    error.value = "";
    try {
      await apiPost(`/api/v1/itineraries/${itineraryId}/stages`, payload);
      await loadOne(itineraryId);
      return true;
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "Creazione tappa fallita";
      return false;
    }
  }

  const totalKm = computed(() =>
    (current.value?.stages || []).reduce(
      (s, st) => s + (st.distance_km || 0),
      0,
    ),
  );

  return {
    itineraries,
    current,
    loading,
    error,
    totalKm,
    loadList,
    loadOne,
    create,
    addStage,
  };
});
