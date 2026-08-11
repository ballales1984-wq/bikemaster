/**
 * ActivitySegmentation composable.
 *
 * Detects the start and end of physical activities from raw GPS points
 * using speed thresholds and minimum duration/distance rules.
 *
 * States:
 * - idle: no activity detected yet
 * - candidate: possible activity (speed > threshold) but not yet confirmed
 * - active: confirmed activity in progress
 * - paused: activity interrupted (stationary too long)
 *
 * Transition rules:
 * - idle → candidate: speed > 3 km/h for 30 seconds
 * - candidate → active: distance > 0.2 km
 * - active → paused: speed < 0.5 km/h for 120 seconds
 * - paused → active: speed > 3 km/h again
 * - candidate → idle: speed drops below threshold before confirmation
 */

import { ref, computed } from "vue";
import type { GpsPoint } from "../types/index";
import { haversineDistanceMeters } from "../utils/geo";

export type SegmentState = "idle" | "candidate" | "active" | "paused";

export interface ActivitySegment {
  id: string;
  state: SegmentState;
  startTime: number;
  endTime: number | null;
  points: GpsPoint[];
  distanceM: number;
  avgSpeedKmh: number;
  elevationGainM: number;
  autoDetected: boolean;
  candidateStartTime: number | null;
  pausedSince: number | null;
}

export interface SegmentationConfig {
  speedActiveThresholdKmh: number;
  speedPausedThresholdKmh: number;
  candidateMinDurationMs: number;
  activeMinDistanceM: number;
  autoPauseTimeoutMs: number;
  autoPauseMinDistanceM: number;
}

export const DEFAULT_SEGMENTATION_CONFIG: SegmentationConfig = {
  speedActiveThresholdKmh: 3,
  speedPausedThresholdKmh: 0.5,
  candidateMinDurationMs: 30000,
  activeMinDistanceM: 200,
  autoPauseTimeoutMs: 120000,
  autoPauseMinDistanceM: 20,
};

export function useActivitySegmentation(
  config: Partial<SegmentationConfig> = {},
) {
  const cfg: SegmentationConfig = { ...DEFAULT_SEGMENTATION_CONFIG, ...config };

  const segments = ref<ActivitySegment[]>([]);
  const currentSegment = ref<ActivitySegment | null>(null);
  const state = ref<SegmentState>("idle");
  const lastPoint = ref<GpsPoint | null>(null);
  const lastSpeedKmh = ref(0);

  let currentDistanceM = 0;
  let currentElevationGainM = 0;

  function generateId(): string {
    return `seg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  }

  function createSegment(): ActivitySegment {
    return {
      id: generateId(),
      state: "candidate",
      startTime: Date.now(),
      endTime: null,
      points: [],
      distanceM: 0,
      avgSpeedKmh: 0,
      elevationGainM: 0,
      autoDetected: true,
      candidateStartTime: Date.now(),
      pausedSince: null,
    };
  }

  function computeSpeedKmh(distanceM: number, elapsedMs: number): number {
    if (elapsedMs <= 0) return 0;
    const hours = elapsedMs / 3600000;
    return distanceM / 1000 / hours;
  }

  function processPoint(point: GpsPoint): ActivitySegment | null {
    const now = Date.now();

    if (lastPoint.value) {
      const delta = haversineDistanceMeters(
        lastPoint.value.lat,
        lastPoint.value.lon,
        point.lat,
        point.lon,
      );
      currentDistanceM += delta;

      if (
        lastPoint.value.altitude !== null &&
        lastPoint.value.altitude !== undefined &&
        point.altitude !== null &&
        point.altitude !== undefined
      ) {
        currentElevationGainM += Math.max(
          0,
          point.altitude - lastPoint.value.altitude,
        );
      }
    }

    const elapsedSinceLast =
      lastPoint.value && lastPoint.value.timestampNumber
        ? point.timestampNumber
          ? point.timestampNumber - lastPoint.value.timestampNumber
          : 0
        : 0;

    const speedKmh =
      elapsedSinceLast > 0
        ? (lastPoint.value
            ? haversineDistanceMeters(
                lastPoint.value.lat,
                lastPoint.value.lon,
                point.lat,
                point.lon,
              )
            : 0) /
          1000 /
          (elapsedSinceLast / 3600000)
        : 0;

    lastSpeedKmh.value = speedKmh;
    const pt = { ...point, timestampNumber: point.timestampNumber ?? now };
    lastPoint.value = pt;

    switch (state.value) {
      case "idle":
        if (speedKmh >= cfg.speedActiveThresholdKmh) {
          currentSegment.value = createSegment();
          currentSegment.value.points.push(pt);
          currentSegment.value.distanceM = currentDistanceM;
          state.value = "candidate";
        }
        break;

      case "candidate":
        if (!currentSegment.value) break;
        currentSegment.value.points.push(pt);
        currentSegment.value.distanceM = currentDistanceM;
        currentSegment.value.elevationGainM = currentElevationGainM;

        if (
          speedKmh < cfg.speedActiveThresholdKmh &&
          now - (currentSegment.value.candidateStartTime ?? now) >
            cfg.candidateMinDurationMs
        ) {
          if (currentDistanceM < cfg.activeMinDistanceM) {
            segments.value.push(currentSegment.value);
            resetCurrentSegment();
            state.value = "idle";
          }
        } else if (currentDistanceM >= cfg.activeMinDistanceM) {
          currentSegment.value.state = "active";
          currentSegment.value.candidateStartTime = null;
          state.value = "active";
        }
        break;

      case "active":
        if (!currentSegment.value) break;
        currentSegment.value.points.push(pt);
        currentSegment.value.distanceM = currentDistanceM;
        currentSegment.value.elevationGainM = currentElevationGainM;
        currentSegment.value.avgSpeedKmh = computeSpeedKmh(
          currentDistanceM,
          now - currentSegment.value.startTime,
        );

        if (speedKmh < cfg.speedPausedThresholdKmh) {
          if (!currentSegment.value.pausedSince) {
            currentSegment.value.pausedSince = now;
          } else if (
            now - currentSegment.value.pausedSince > cfg.autoPauseTimeoutMs &&
            currentDistanceM -
              (currentSegment.value.pausedSince ? 0 : currentDistanceM) <
              cfg.autoPauseMinDistanceM
          ) {
            currentSegment.value.state = "paused";
            currentSegment.value.endTime = now;
            state.value = "paused";
          }
        } else {
          currentSegment.value.pausedSince = null;
        }
        break;

      case "paused":
        if (!currentSegment.value) break;
        if (speedKmh >= cfg.speedActiveThresholdKmh) {
          const newSeg = createSegment();
          newSeg.state = "active";
          newSeg.points.push(pt);
          newSeg.distanceM = currentDistanceM;
          newSeg.elevationGainM = currentElevationGainM;
          newSeg.avgSpeedKmh = computeSpeedKmh(
            currentDistanceM,
            now - newSeg.startTime,
          );
          currentSegment.value = newSeg;
          state.value = "active";
        }
        break;
    }

    return currentSegment.value;
  }

  function closeCurrentSegment(): ActivitySegment | null {
    if (!currentSegment.value || currentSegment.value.state === "idle") {
      return null;
    }
    const seg = currentSegment.value;
    seg.endTime = Date.now();
    if (seg.state === "candidate") {
      seg.state = "active";
    }
    if (seg.points.length > 0) {
      seg.avgSpeedKmh =
        seg.distanceM / 1000 / ((seg.endTime - seg.startTime) / 3600000);
    }
    segments.value.push(seg);
    resetCurrentSegment();
    state.value = "idle";
    return seg;
  }

  function resetCurrentSegment() {
    currentSegment.value = null;
    currentDistanceM = 0;
    currentElevationGainM = 0;
    lastPoint.value = null;
  }

  function getTodaySegments(): ActivitySegment[] {
    const today = new Date().toISOString().slice(0, 10);
    return segments.value.filter((seg) => {
      const segDate = new Date(seg.startTime).toISOString().slice(0, 10);
      return segDate === today;
    });
  }

  function getActiveSegments(): ActivitySegment[] {
    return segments.value.filter(
      (seg) => seg.state === "active" || seg.state === "candidate",
    );
  }

  function clearAll() {
    segments.value = [];
    resetCurrentSegment();
    state.value = "idle";
  }

  const totalTodayDistanceKm = computed(() => {
    return getTodaySegments().reduce(
      (sum, seg) => sum + seg.distanceM / 1000,
      0,
    );
  });

  const totalTodayActiveMinutes = computed(() => {
    return getTodaySegments().reduce((sum, seg) => {
      const end = seg.endTime ?? Date.now();
      return sum + (end - seg.startTime) / 60000;
    }, 0);
  });

  return {
    segments,
    currentSegment,
    state,
    lastSpeedKmh,
    processPoint,
    closeCurrentSegment,
    getTodaySegments,
    getActiveSegments,
    clearAll,
    totalTodayDistanceKm,
    totalTodayActiveMinutes,
  };
}
