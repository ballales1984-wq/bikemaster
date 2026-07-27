import { describe, it, expect } from "vitest";
import { useGpsOutlierFilter } from "./useGpsOutlierFilter";
import type { GpsPoint } from "../types/index";

function sample(
  lat: number,
  lon: number,
  tsOffsetMs: number,
  base = 1_000_000_000_000,
): GpsPoint {
  return {
    lat,
    lon,
    timestamp: new Date(base + tsOffsetMs).toISOString(),
  };
}

describe("useGpsOutlierFilter", () => {
  it("accepts the first point", () => {
    const { isOutlier } = useGpsOutlierFilter();
    expect(isOutlier(sample(45.0, 7.0, 0))).toBe(false);
  });

  it("accepts a plausible movement (~10 m/s over 1s)", () => {
    const { isOutlier } = useGpsOutlierFilter();
    isOutlier(sample(45.0, 7.0, 0));
    const next = sample(45.00009, 7.00009, 1000); // ~12.7 m in 1s
    expect(isOutlier(next)).toBe(false);
  });

  it("rejects a jump that implies an impossible speed (>5000m or >30 m/s)", () => {
    const { isOutlier } = useGpsOutlierFilter();
    isOutlier(sample(45.0, 7.0, 0));
    const jump400m = sample(45.0036, 7.0, 1000); // ~400m in 1s => 400 m/s
    expect(isOutlier(jump400m)).toBe(true);
  });

  it("does not use a rejected point as the new reference", () => {
    const { isOutlier } = useGpsOutlierFilter();
    isOutlier(sample(45.0, 7.0, 0));
    expect(isOutlier(sample(45.0036, 7.0, 1000))).toBe(true); // outlier, rejected
    // next point near the rejected one should be measured from the original
    const back = sample(45.00009, 7.00009, 2000);
    expect(isOutlier(back)).toBe(false);
  });

  it("respects a custom max speed threshold", () => {
    const { isOutlier } = useGpsOutlierFilter({ maxSpeedMetersPerSecond: 5 });
    isOutlier(sample(45.0, 7.0, 0));
    // ~12.7 m in 1s => 12.7 m/s, above 5 m/s custom threshold
    expect(isOutlier(sample(45.00009, 7.00009, 1000))).toBe(true);
  });

  it("rejects points with non-finite coordinates or timestamps", () => {
    const { isOutlier } = useGpsOutlierFilter();
    expect(
      isOutlier({
        lat: NaN,
        lon: 7,
        timestamp: new Date().toISOString(),
      } as GpsPoint),
    ).toBe(true);
  });

  it("reset clears the accepted reference", () => {
    const { isOutlier, reset } = useGpsOutlierFilter();
    isOutlier(sample(45.0, 7.0, 0));
    reset();
    expect(isOutlier(sample(45.5, 7.5, 0))).toBe(false); // treated as first point
  });
});
