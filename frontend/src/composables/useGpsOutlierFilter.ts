import type { GpsPoint } from "../types/index";

export interface GpsOutlierFilterOptions {
  maxSpeedMetersPerSecond?: number;
  maxJumpMeters?: number;
  minElapsedMs?: number;
}

export interface GpsSample {
  lat: number;
  lon: number;
  timestamp: number;
}

function haversineMeters(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const radius = 6371000;
  const toRadians = (value: number) => (value * Math.PI) / 180;
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) *
      Math.cos(toRadians(lat2)) *
      Math.sin(dLon / 2) ** 2;
  return 2 * radius * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function toSample(
  point: GpsPoint | GpsSample | null | undefined,
): GpsSample | null {
  if (!point) return null;
  const lat =
    "lat" in point ? point.lat : (point as { lat: number }).lat;
  const lon =
    "lon" in point ? point.lon : (point as { lon: number }).lon;
  const rawTimestamp = (point as { timestamp?: string | number | null })
    .timestamp;
  const timestamp =
    rawTimestamp == null
      ? NaN
      : typeof rawTimestamp === "number"
        ? rawTimestamp
        : new Date(rawTimestamp).getTime();
  if (!isFinite(lat) || !isFinite(lon) || !isFinite(timestamp)) return null;
  return { lat, lon, timestamp };
}

export function useGpsOutlierFilter(options: GpsOutlierFilterOptions = {}) {
  const maxSpeedMetersPerSecond = options.maxSpeedMetersPerSecond ?? 30;
  const maxJumpMeters = options.maxJumpMeters ?? 5000;
  const minElapsedMs = options.minElapsedMs ?? 250;

  let lastAccepted: GpsSample | null = null;

  function reset() {
    lastAccepted = null;
  }

  function isOutlier(
    candidate: GpsPoint | GpsSample,
    reference: GpsSample | null = lastAccepted,
  ): boolean {
    const sample = toSample(candidate);
    if (!sample) return true;
    if (!reference) {
      lastAccepted = sample;
      return false;
    }

    const distance = haversineMeters(
      reference.lat,
      reference.lon,
      sample.lat,
      sample.lon,
    );

    if (distance > maxJumpMeters) return true;

    const elapsedMs = sample.timestamp - reference.timestamp;
    if (elapsedMs < 0) return true;
    if (elapsedMs > minElapsedMs) {
      const speed = distance / (elapsedMs / 1000);
      if (speed > maxSpeedMetersPerSecond) return true;
    }

    lastAccepted = sample;
    return false;
  }

  return { isOutlier, reset };
}
