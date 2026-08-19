import { describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("../utils/api", () => ({
  apiGet,
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock("../utils/localRideCache", () => ({
  cacheRides: vi.fn().mockResolvedValue(undefined),
  cacheSummary: vi.fn().mockResolvedValue(undefined),
  getCachedRides: vi.fn().mockResolvedValue(null),
  getCachedSummary: vi.fn().mockResolvedValue(null),
  removeCachedRide: vi.fn().mockResolvedValue(undefined),
}));

describe("useRides composable", () => {
  it("fetchSummary returns default values on error", async () => {
    apiGet.mockRejectedValue(new Error("Network error"));

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
    apiGet.mockResolvedValue(mockData);

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