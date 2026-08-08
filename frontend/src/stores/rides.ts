/**
 * Store delle uscite/ride.
 *
 * Gestisce la lista delle ride, i filtri, il riepilogo aggregato
 * e la persistenza offline in SQLite locale.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Ride, Summary } from "../types/index";
import { apiGet, apiDelete, apiPost, apiPut } from "../utils/api";
import { useAuthStore } from "./auth";
import { isLocalDbReady, upsertRide, getCachedRides } from "../db/localDb";

export interface RideFilters {
  search?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export const useRidesStore = defineStore("rides", () => {
  const auth = useAuthStore();
  const rides = ref<Ride[]>([]);
  const offline = ref(false);
  const summary = ref<Summary>({
    rides: 0,
    distance_km: 0,
    calories: 0,
    avg_speed_kmh: 0,
    duration_minutes: 0,
  });
  const loading = ref(false);
  const error = ref<string | null>(null);
  const filters = ref<RideFilters>({
    sort: "date",
    page: 1,
    page_size: 20,
  });

  const filteredRides = computed(() => {
    let result = rides.value;
    if (filters.value.search) {
      const q = filters.value.search.toLowerCase();
      result = result.filter((r) => (r.title || "").toLowerCase().includes(q));
    }
    if (filters.value.sort) {
      const key = filters.value.sort;
      result = [...result].sort((a, b) => {
        const va = (a as Record<string, unknown>)[key];
        const vb = (b as Record<string, unknown>)[key];
        if (va == null && vb == null) return 0;
        if (va == null) return 1;
        if (vb == null) return -1;
        return va < vb ? -1 : va > vb ? 1 : 0;
      });
    }
    return result;
  });
  const totalPages = computed(() =>
    Math.max(
      1,
      Math.ceil(rides.value.length / (filters.value.page_size || 20)),
    ),
  );

  function loadFilters() {
    try {
      const saved = localStorage.getItem("bikemaster_ride_filters");
      if (saved) {
        const parsed = JSON.parse(saved) as RideFilters;
        filters.value = { ...filters.value, ...parsed };
      }
    } catch {
      // ignore parse errors
    }
  }

  function saveFilters() {
    try {
      localStorage.setItem(
        "bikemaster_ride_filters",
        JSON.stringify(filters.value),
      );
    } catch {
      // ignore storage errors
    }
  }

  function setFilter(key: keyof RideFilters, value: unknown) {
    filters.value = {
      ...filters.value,
      [key]: value as RideFilters[keyof RideFilters],
    };
    saveFilters();
  }

  function clearFilters() {
    filters.value = {
      sort: "date",
      page: 1,
      page_size: 20,
    };
    saveFilters();
  }

  async function seedFromCache(): Promise<void> {
    if (!isLocalDbReady()) return;
    try {
      const cached = getCachedRides(filters.value.page_size || 20);
      rides.value = cached
        .map((c) => c.data as Ride)
        .filter((r) => r && typeof r === "object");
      offline.value = true;
    } catch {
      offline.value = false;
    }
  }

  async function fetchRides(): Promise<void> {
    if (!auth.isLoggedIn) return;
    loading.value = true;
    error.value = null;
    offline.value = false;
    try {
      const params: Record<string, string> = {};
      if (filters.value.search) params.search = filters.value.search;
      if (filters.value.sort) params.sort = filters.value.sort;
      if (filters.value.page) params.page = String(filters.value.page);
      if (filters.value.page_size)
        params.page_size = String(filters.value.page_size);

      const data = await apiGet<{ rides: Ride[] }>("/api/v1/rides", params);
      rides.value = data.rides || [];
      // Persisti in SQLite locale per uso offline (cache/seed).
      if (isLocalDbReady()) {
        for (const r of rides.value) {
          if (typeof r.id === "number") upsertRide(r.id, r);
        }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load rides";
      // Fallback offline: servi dalla cache SQLite locale se disponibile.
      await seedFromCache();
      if (!offline.value) rides.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function fetchSummary(): Promise<Summary> {
    if (!auth.isLoggedIn) return summary.value;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<Summary>("/api/v1/rides/summary");
      summary.value = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load summary";
      return summary.value;
    } finally {
      loading.value = false;
    }
  }

  async function deleteRide(rideId: number): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await apiDelete(`/api/v1/rides/${rideId}`);
      rides.value = rides.value.filter((r) => r.id !== rideId);
      summary.value.rides = Math.max(0, summary.value.rides - 1);
      await fetchSummary();
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete ride";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function addRide(ride: Partial<Ride>): Promise<Ride> {
    loading.value = true;
    error.value = null;
    try {
      const data = await apiPost<Ride>("/api/v1/rides", ride);
      rides.value.unshift(data);
      summary.value.rides += 1;
      await fetchSummary();
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to add ride";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchRide(rideId: number): Promise<Ride | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiGet<Ride>(`/api/v1/rides/${rideId}`);
      const idx = rides.value.findIndex((r) => r.id === rideId);
      if (idx >= 0) rides.value[idx] = data;
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load ride";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateRide(
    rideId: number,
    payload: Partial<Ride>,
  ): Promise<Ride | null> {
    if (!auth.isLoggedIn) return null;
    loading.value = true;
    error.value = null;
    try {
      const data = await apiPut<Ride>(`/api/v1/rides/${rideId}`, payload);
      const idx = rides.value.findIndex((r) => r.id === rideId);
      if (idx >= 0) rides.value[idx] = data;
      else rides.value.unshift(data);
      await fetchSummary();
      return data;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to update ride";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchAllRides(): Promise<void> {
    if (!auth.isLoggedIn) return;
    loading.value = true;
    error.value = null;
    offline.value = false;
    try {
      const all: Ride[] = [];
      const pageSize = 100;
      const first = await apiGet<{ rides: Ride[]; total?: number }>(
        "/api/v1/rides",
        { page: "1", page_size: String(pageSize) },
      );
      const firstBatch = first.rides || [];
      all.push(...firstBatch);
      let total = typeof first.total === "number" ? first.total : null;
      if (total === null && firstBatch.length < pageSize) {
        total = all.length;
      }
      if (total !== null && all.length < total) {
        const remaining = total - all.length;
        const pages = Math.ceil(remaining / pageSize);
        const promises = Array.from({ length: pages }, (_, i) =>
          apiGet<{ rides: Ride[] }>("/api/v1/rides", {
            page: String(2 + i),
            page_size: String(pageSize),
          }),
        );
        const results = await Promise.all(promises);
        for (const r of results) {
          all.push(...(r.rides || []));
        }
      } else if (total === null) {
        let page = 2;
        while (true) {
          const data = await apiGet<{ rides: Ride[]; total?: number }>(
            "/api/v1/rides",
            { page: String(page), page_size: String(pageSize) },
          );
          const batch = data.rides || [];
          all.push(...batch);
          if (batch.length === 0) break;
          page += 1;
        }
      }
      rides.value = all;
      if (isLocalDbReady()) {
        for (const r of rides.value) {
          if (typeof r.id === "number") upsertRide(r.id, r);
        }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load rides";
      await seedFromCache();
      if (!offline.value) rides.value = [];
    } finally {
      loading.value = false;
    }
  }

  function reset() {
    rides.value = [];
    summary.value = {
      rides: 0,
      distance_km: 0,
      calories: 0,
      avg_speed_kmh: 0,
      duration_minutes: 0,
    };
    error.value = null;
  }

  loadFilters();

  return {
    rides,
    summary,
    loading,
    error,
    offline,
    filters,
    filteredRides,
    totalPages,
    loadFilters,
    saveFilters,
    setFilter,
    clearFilters,
    fetchRides,
    fetchAllRides,
    fetchRide,
    fetchSummary,
    deleteRide,
    addRide,
    updateRide,
    reset,
  };
});
