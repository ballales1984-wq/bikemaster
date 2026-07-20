/**
 * Store del tracking GPS in tempo reale.
 *
 * Registers cycling metrics (distance, speed, elevation,
 * FC, cadenza, potenza), traccia punti GPS e genera GPX.
 */
import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type { GpsPoint } from "../types/index";

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
  }

  function setGpxPath(path: string | null = null) {
    gpxPath.value = path;
  }

  function setGpxBlob(blob: Blob | null = null) {
    gpxBlob.value = blob;
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
  }

  function toGpx(name = "BikeMaster ride") {
    const safeName =
      name.replace(/[&<>]/g, "").replace(/\s+/g, " ").trim() ||
      "BikeMaster ride";
    const route = routePoints.value
      .map((point) => {
        const eleStr = point.altitude !== null && point.altitude !== undefined 
          ? `\n        <ele>${point.altitude}</ele>` 
          : "";
        return `      <trkpt lat="${point.lat}" lon="${point.lon}">${eleStr}
        <time>${point.timestamp || new Date().toISOString()}</time>
      </trkpt>`;
      })
      .join("\n");

    return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BikeMaster-Web" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>${safeName}</name>
    <trkseg>
${route}
    </trkseg>
  </trk>
</gpx>
`;
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
    start,
    pause,
    resume,
    stop,
    updateMetrics,
    addPoint,
    setGpxPath,
    setGpxBlob,
    resetMetrics,
    toGpx,
    formattedTime,
    formattedDistance,
  };
});

