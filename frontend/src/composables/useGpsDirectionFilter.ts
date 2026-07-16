import type { GpsPoint } from "../types/index";

export interface DirectionFilterOptions {
  maxBearingDeviationDeg?: number;
  bearingWindowSize?: number;
  minDistanceForBearing?: number;
}

function toRad(d: number): number {
  return (d * Math.PI) / 180;
}

function toDeg(r: number): number {
  return (r * 180) / Math.PI;
}

export function bearing(a: GpsPoint, b: GpsPoint): number {
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const dLon = toRad(b.lon - a.lon);
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

export function angleDiff(a: number, b: number): number {
  const diff = Math.abs(a - b) % 360;
  return diff > 180 ? 360 - diff : diff;
}

export function averageBearing(bearings: number[]): number {
  if (bearings.length === 0) return 0;
  const sum = bearings.reduce(
    (acc, deg) => {
      const r = toRad(deg);
      return { x: acc.x + Math.cos(r), y: acc.y + Math.sin(r) };
    },
    { x: 0, y: 0 },
  );
  const avg = toDeg(Math.atan2(sum.y, sum.x));
  return (avg + 360) % 360;
}

export function useGpsDirectionFilter(options: DirectionFilterOptions = {}) {
  const maxDeviation = options.maxBearingDeviationDeg ?? 45;
  const windowSize = options.bearingWindowSize ?? 5;
  const minDist = options.minDistanceForBearing ?? 3;

  let lastAccepted: GpsPoint | null = null;
  let bearingHistory: number[] = [];

  function isDirectionOutlier(
    point: GpsPoint,
    distanceFromLast: number,
    isTurning: boolean,
  ): boolean {
    if (!lastAccepted || distanceFromLast < minDist) {
      return false;
    }

    const candidateBearing = bearing(lastAccepted, point);

    if (bearingHistory.length === 0) {
      return false;
    }

    if (isTurning) {
      return false;
    }

    const avgBearing = averageBearing(bearingHistory);
    const deviation = angleDiff(candidateBearing, avgBearing);
    return deviation > maxDeviation;
  }

  function accept(
    point: GpsPoint,
    distanceFromLast: number,
    isTurning: boolean,
  ): void {
    if (lastAccepted && distanceFromLast >= minDist) {
      const b = bearing(lastAccepted, point);
      if (isTurning) {
        bearingHistory = [b];
      } else {
        bearingHistory.push(b);
        if (bearingHistory.length > windowSize) bearingHistory.shift();
      }
    }
    lastAccepted = point;
  }

  function reset(): void {
    lastAccepted = null;
    bearingHistory = [];
  }

  return { isDirectionOutlier, accept, reset };
}
