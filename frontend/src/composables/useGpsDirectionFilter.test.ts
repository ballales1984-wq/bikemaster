import { describe, it, expect } from "vitest";
import {
  bearing,
  angleDiff,
  averageBearing,
  useGpsDirectionFilter,
} from "./useGpsDirectionFilter";
import type { GpsPoint } from "../types/index";

function pt(lat: number, lon: number): GpsPoint {
  return { lat, lon, timestamp: new Date().toISOString() };
}

describe("bearing", () => {
  it("north (0°) for a due-north step", () => {
    const b = bearing(pt(45.0, 7.0), pt(45.001, 7.0));
    expect(b).toBeCloseTo(0, 0);
  });

  it("east (90°) for a due-east step", () => {
    const b = bearing(pt(45.0, 7.0), pt(45.0, 7.001));
    expect(b).toBeCloseTo(90, 0);
  });

  it("south (180°) for a due-south step", () => {
    const b = bearing(pt(45.001, 7.0), pt(45.0, 7.0));
    expect(b).toBeCloseTo(180, 0);
  });
});

describe("angleDiff", () => {
  it("handles normal differences", () => {
    expect(angleDiff(30, 50)).toBe(20);
  });

  it("handles wraparound (359 -> 1)", () => {
    expect(angleDiff(359, 1)).toBe(2);
    expect(angleDiff(10, 350)).toBe(20);
  });

  it("never exceeds 180", () => {
    expect(angleDiff(0, 270)).toBe(90);
  });
});

describe("averageBearing", () => {
  it("returns 0 for empty input", () => {
    expect(averageBearing([])).toBe(0);
  });

  it("averages bearings without wraparound bias", () => {
    // 10° and 350° should average to ~0°, NOT 180°
    const avg = averageBearing([10, 350]);
    expect(angleDiff(avg, 0)).toBeLessThan(1);
  });

  it("averages a straight cluster", () => {
    const avg = averageBearing([90, 92, 88]);
    expect(angleDiff(avg, 90)).toBeLessThan(2);
  });
});

describe("useGpsDirectionFilter", () => {
  it("accepts the first point", () => {
    const { isDirectionOutlier } = useGpsDirectionFilter();
    expect(isDirectionOutlier(pt(45.0, 7.0), 10, false)).toBe(false);
  });

  it("accepts the first bearing of the series", () => {
    const f = useGpsDirectionFilter();
    f.accept(pt(45.0, 7.0), 0, false);
    expect(f.isDirectionOutlier(pt(45.001, 7.0), 10, false)).toBe(false);
  });

  it("accepts a point aligned with the average bearing", () => {
    const f = useGpsDirectionFilter();
    f.accept(pt(45.0, 7.0), 0, false);
    f.accept(pt(45.001, 7.0), 10, false); // bearing ~0°
    f.accept(pt(45.002, 7.0), 10, false); // bearing ~0°
    // still heading north -> aligned
    expect(f.isDirectionOutlier(pt(45.003, 7.0), 10, false)).toBe(false);
  });

  it("rejects a point that deviates too far from the bearing", () => {
    const f = useGpsDirectionFilter({ maxBearingDeviationDeg: 45 });
    f.accept(pt(45.0, 7.0), 0, false);
    f.accept(pt(45.001, 7.0), 10, false); // north
    f.accept(pt(45.002, 7.0), 10, false); // north
    // a sharp eastward step (90° off) is suspicious
    expect(f.isDirectionOutlier(pt(45.002, 7.001), 10, false)).toBe(true);
  });

  it("does NOT reject during an active turn (gyro signal)", () => {
    const f = useGpsDirectionFilter({ maxBearingDeviationDeg: 45 });
    f.accept(pt(45.0, 7.0), 0, false);
    f.accept(pt(45.001, 7.0), 10, false);
    f.accept(pt(45.002, 7.0), 10, false);
    // big deviation but the device is turning
    expect(f.isDirectionOutlier(pt(45.002, 7.001), 10, true)).toBe(false);
  });

  it("ignores sub-threshold distance (bearing noise)", () => {
    const f = useGpsDirectionFilter({ minDistanceForBearing: 3 });
    f.accept(pt(45.0, 7.0), 0, false);
    f.accept(pt(45.001, 7.0), 10, false);
    // 1m move -> too small to judge direction
    expect(f.isDirectionOutlier(pt(45.001001, 7.000001), 1, false)).toBe(false);
  });

  it("resets the bearing window after a turn", () => {
    const f = useGpsDirectionFilter({ maxBearingDeviationDeg: 45 });
    f.accept(pt(45.0, 7.0), 0, false);
    f.accept(pt(45.001, 7.0), 10, false); // north ref
    f.accept(pt(45.002, 7.001), 10, true); // turning: window reset to this bearing
    // next point continues the new (eastward) direction -> accepted
    expect(f.isDirectionOutlier(pt(45.002, 7.002), 10, false)).toBe(false);
  });

  it("reset clears state", () => {
    const f = useGpsDirectionFilter();
    f.accept(pt(45.0, 7.0), 0, false);
    f.reset();
    expect(f.isDirectionOutlier(pt(45.5, 7.5), 100, false)).toBe(false);
  });
});
