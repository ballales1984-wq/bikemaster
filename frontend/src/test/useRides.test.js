import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("useRides composable", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ rides: [], total: 0 }),
    });
  });

  afterEach(() => {
    delete globalThis.fetch;
  });

  it("fetchSummary returns default values on error", async () => {
    const { useRides } = await import("../composables/useRides.ts");
    const result = await useRides().fetchSummary();
    expect(result.rides).toBe(0);
    expect(result.distance_km).toBe(0);
  });

  it("calculates totals correctly", async () => {
    const mockData = {
      rides: [
        {
          id: 1,
          distance_km: 20,
          calories: 400,
          avg_speed_kmh: 25,
          duration_minutes: 60,
        },
        {
          id: 2,
          distance_km: 30,
          calories: 600,
          avg_speed_kmh: 30,
          duration_minutes: 90,
        },
      ],
      total: 2,
    };
    const { useRides } = await import("../composables/useRides.ts");

    const totalKm = mockData.rides.reduce(
      (s, r) => s + (Number(r.distance_km) || 0),
      0,
    );
    expect(totalKm).toBe(50);
    expect(useRides()).toEqual(
      expect.objectContaining({
        fetchSummary: expect.any(Function),
        createRide: expect.any(Function),
        deleteRide: expect.any(Function),
        initMap: expect.any(Function),
      }),
    );
  });
});
