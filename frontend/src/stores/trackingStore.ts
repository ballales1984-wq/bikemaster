/**
 * Store del tracking GPS in tempo reale.
 *
 * Registers cycling metrics (distance, speed, elevation,
 * FC, cadenza, potenza), traccia punti GPS e genera GPX.
 */
import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";
import type { GpsPoint } from "../types/index";

const STORAGE_KEY = "bikemaster_tracking_draft";

export const useTrackingStore = defineStore("tracking", () => {
  const isTracking = ref(false);
  const isPaused = ref(false);
  const distance = ref(0);
  const currentSpeed = ref(0);
  const avgSpeed = ref(0);
  const elapsedTime = ref(0);
  const elevation = ref(0);
  const points = ref(0);
  const heartRate = ref<number | null>(null);
  const cadence = ref<number | null>(null);
  const power = ref<number | null>(null);
  const gpxPath = ref<string | null>(null);
  const gpxBlob = ref<Blob | null>(null);
  const routePoints = ref<GpsPoint[]>([]);
  const lastPoint = ref<GpsPoint | null>(null);
  const rideId = ref<number | null>(null);

  function start() {
    isTracking.value = true;
    isPaused.value = false;
    resetMetrics();
  }

  function pause() {
    isPaused.value = true;
  }

  function resume() {
    isPaused.value = false;
  }

  function stop() {
    isTracking.value = false;
    isPaused.value = false;
  }

  function updateMetrics(payload: {
    distance?: number;
    currentSpeed?: number;
    avgSpeed?: number;
    elapsedTime?: number;
    elevation?: number;
    points?: number;
    heartRate?: number | null;
    cadence?: number | null;
    power?: number | null;
  }) {
    if (payload.distance !== undefined) distance.value = payload.distance;
    if (payload.currentSpeed !== undefined)
      currentSpeed.value = payload.currentSpeed;
    if (payload.avgSpeed !== undefined) avgSpeed.value = payload.avgSpeed;
    if (payload.elapsedTime !== undefined)
      elapsedTime.value = payload.elapsedTime;
    if (payload.elevation !== undefined) elevation.value = payload.elevation;
    if (payload.points !== undefined) points.value = payload.points;
    if (payload.heartRate !== undefined) heartRate.value = payload.heartRate;
    if (payload.cadence !== undefined) cadence.value = payload.cadence;
    if (payload.power !== undefined) power.value = payload.power;
  }

  function addPoint(point: GpsPoint) {
    routePoints.value.push(point);
    lastPoint.value = point;
    points.value = routePoints.value.length;
    persistState();
  }

  function setGpxPath(path: string | null = null) {
    gpxPath.value = path;
  }

  function setGpxBlob(blob: Blob | null = null) {
    gpxBlob.value = blob;
  }

  function setRideId(id: number | null = null) {
    rideId.value = id;
  }

  function resetMetrics() {
    distance.value = 0;
    currentSpeed.value = 0;
    avgSpeed.value = 0;
    elapsedTime.value = 0;
    elevation.value = 0;
    points.value = 0;
    heartRate.value = null;
    cadence.value = null;
    power.value = null;
    routePoints.value = [];
    lastPoint.value = null;
    gpxPath.value = null;
    gpxBlob.value = null;
    rideId.value = null;
    clearPersistedState();
  }

  function toGpx(name = "BikeMaster ride") {
    const safeName =
      name.replace(/[&<>]/g, "").replace(/\s+/g, " ").trim() ||
      "BikeMaster ride";
    const route = routePoints.value
      .map((point) => {
        const eleStr =
          point.altitude !== null && point.altitude !== undefined
            ? `\n        <ele>${point.altitude}</ele>`
            : "";
        const extensions = buildGpxExtensions(point);
        return `      <trkpt lat="${point.lat}" lon="${point.lon}">${eleStr}
        <time>${point.timestamp || new Date().toISOString()}</time>
        ${extensions}
      </trkpt>`;
      })
      .join("\n");

    return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BikeMaster-Web" xmlns="http://www.topografix.com/GPX/1/1"
      xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">
  <trk>
    <name>${safeName}</name>
    <trkseg>
${route}
    </trkseg>
  </trk>
</gpx>
`;
  }

  function buildGpxExtensions(point: GpsPoint): string {
    const parts: string[] = [];
    if (point.heartRate !== null && point.heartRate !== undefined) {
      parts.push(`<gpxtpx:hr>${point.heartRate}</gpxtpx:hr>`);
    }
    if (point.cadence !== null && point.cadence !== undefined) {
      parts.push(`<gpxtpx:cad>${point.cadence}</gpxtpx:cad>`);
    }
    if (point.power !== null && point.power !== undefined) {
      parts.push(`<gpxtpx:power>${point.power}</gpxtpx:power>`);
    }
    if (parts.length === 0) return "";
    return `\n        <gpxtpx:TrackPointExtension>\n          ${parts.join("\n          ")}\n        </gpxtpx:TrackPointExtension>`;
  }

  function persistState() {
    if (typeof window === "undefined") return;
    try {
      const state = {
        isTracking: isTracking.value,
        isPaused: isPaused.value,
        distance: distance.value,
        currentSpeed: currentSpeed.value,
        avgSpeed: avgSpeed.value,
        elapsedTime: elapsedTime.value,
        elevation: elevation.value,
        points: points.value,
        heartRate: heartRate.value,
        cadence: cadence.value,
        power: power.value,
        routePoints: routePoints.value,
        lastPoint: lastPoint.value,
        rideId: rideId.value,
        timestamp: Date.now(),
      };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // sessionStorage may be full or unavailable
    }
  }

  function restoreState(): boolean {
    if (typeof window === "undefined") return false;
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      const state = JSON.parse(raw);
      if (!state || !state.routePoints || state.routePoints.length === 0) {
        clearPersistedState();
        return false;
      }
      isTracking.value = state.isTracking ?? false;
      isPaused.value = state.isPaused ?? false;
      distance.value = state.distance ?? 0;
      currentSpeed.value = state.currentSpeed ?? 0;
      avgSpeed.value = state.avgSpeed ?? 0;
      elapsedTime.value = state.elapsedTime ?? 0;
      elevation.value = state.elevation ?? 0;
      points.value = state.points ?? 0;
      heartRate.value = state.heartRate ?? null;
      cadence.value = state.cadence ?? null;
      power.value = state.power ?? null;
      routePoints.value = state.routePoints ?? [];
      lastPoint.value = state.lastPoint ?? null;
      rideId.value = state.rideId ?? null;
      return true;
    } catch {
      return false;
    }
  }

  function clearPersistedState() {
    if (typeof window === "undefined") return;
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }

  const formattedTime = computed(() => {
    const totalSeconds = Math.floor(elapsedTime.value);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  });

  const formattedDistance = computed(() => {
    return (distance.value / 1000).toFixed(2);
  });

  return {
    isTracking,
    isPaused,
    distance,
    currentSpeed,
    avgSpeed,
    elapsedTime,
    elevation,
    points,
    heartRate,
    cadence,
    power,
    gpxPath,
    gpxBlob,
    routePoints,
    lastPoint,
    rideId,
    start,
    pause,
    resume,
    stop,
    updateMetrics,
    addPoint,
    setGpxPath,
    setGpxBlob,
    setRideId,
    resetMetrics,
    toGpx,
    buildGpxExtensions,
    persistState,
    restoreState,
    clearPersistedState,
    formattedTime,
    formattedDistance,
  };
});
