import { describe, it, expect, beforeEach } from "vitest";
import type { Ride } from "../types/index";
import {
  cacheRides,
  getCachedRides,
  removeCachedRide,
  cacheSummary,
  getCachedSummary,
  clearLocalRideCache,
} from "../utils/localRideCache";

const rideA: Ride = {
  id: 1,
  distance_km: 10,
  calories: 200,
  avg_speed_kmh: 25,
  duration_minutes: 24,
} as Ride;

const rideB: Ride = {
  id: 2,
  distance_km: 20,
  calories: 400,
  avg_speed_kmh: 30,
  duration_minutes: 40,
} as Ride;

const summary = {
  rides: 2,
  distance_km: 30,
  calories: 600,
  avg_speed_kmh: 27.5,
  duration_minutes: 64,
  ridesList: [rideA, rideB],
};

describe("localRideCache", () => {
  beforeEach(async () => {
    await clearLocalRideCache();
  });

  it("returns null when no cached rides", async () => {
    expect(await getCachedRides()).toBe(null);
  });

  it("caches and reads rides", async () => {
    await cacheRides([rideA, rideB]);
    const rides = await getCachedRides();
    expect(rides).not.toBe(null);
    expect(rides!.map((r) => r.id).sort()).toEqual([1, 2]);
  });

  it("removes a single cached ride", async () => {
    await cacheRides([rideA, rideB]);
    await removeCachedRide(1);
    const rides = await getCachedRides();
    expect(rides!.map((r) => r.id)).toEqual([2]);
  });

  it("caches and reads summary", async () => {
    expect(await getCachedSummary()).toBe(null);
    await cacheSummary(summary);
    const cached = await getCachedSummary();
    expect(cached).not.toBe(null);
    expect(cached!.rides).toBe(2);
  });

  it("clears the cache", async () => {
    await cacheRides([rideA]);
    await cacheSummary(summary);
    await clearLocalRideCache();
    expect(await getCachedRides()).toBe(null);
    expect(await getCachedSummary()).toBe(null);
  });
});
