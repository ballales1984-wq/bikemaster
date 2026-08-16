<!--
  Vista di tracciamento GPS in tempo reale (estesa per monitoraggio continuo H24).
  Integra ContinuousTracking (auto-start/auto-pause/auto-resume) e
  ActivitySegmentation (rilevamento automatico inizio/fine uscita).
  Componenti: LiveMap, RideMetricsPanel, ControlsBar, DailyTimeline, ActivityRings.
  Compositables: useBatteryEfficientGps, useGpsOutlierFilter, useGpsDirectionFilter,
                 useContinuousTracking, useActivitySegmentation.
-->
<template>
  <section class="panel tracking-panel">
    <div class="tracking-header">
      <h2>{{ t("tracking.title") }}</h2>
      <div v-if="isTracking" class="tracking-status">
        <span class="status-badge" :class="{ paused: isPaused }">
          <span class="pulse-dot"></span>
          {{ isPaused ? t("tracking.paused") : t("tracking.inProgress") }}
        </span>
        <label class="voice-coach-toggle">
          <input v-model="voiceCoachEnabled" type="checkbox" />
          <span>Voice Coach</span>
        </label>
      </div>
      <div v-else class="tracking-auto-info">
        <span class="auto-badge" :class="{ active: tracking.autoTracking }">
          {{
            tracking.autoTracking
              ? "Auto-tracking attivo"
              : "Auto-tracking disattivato"
          }}
        </span>
      </div>
    </div>

    <div
      v-if="
        !isTracking &&
        !tracking.gpxPath &&
        !tracking.gpxBlob &&
        !hasActiveSession
      "
      class="empty-state premium-empty"
    >
      <div class="empty-icon glass-icon">📊</div>
      <div class="empty-title">{{ t("tracking.ready") }}</div>
      <div class="empty-desc">
        {{ t("tracking.readyDesc") }}
      </div>

      <ActivityRings
        v-if="tracking.activityRings.length > 0"
        :rings="tracking.activityRings"
      />

      <div v-if="todaySegments.length > 0" class="daily-summary-section">
        <h3>Attivita di oggi</h3>
        <DailyTimeline :segments="todaySegments" @select="onSelectSegment" />
        <div class="daily-stats">
          <div class="stat">
            <span class="stat-value">{{
              tracking.totalTodayDistanceKm.toFixed(1)
            }}</span>
            <span class="stat-label">km</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{
              tracking.totalTodayActiveMinutes
            }}</span>
            <span class="stat-label">min attivi</span>
          </div>
        </div>
      </div>

      <div class="activity-select modern-select">
        <label for="activity-type">{{ t("tracking.activityType") }}</label>
        <div class="select-wrapper">
          <select id="activity-type" v-model="activityType">
            <option
              v-for="opt in activityOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
        </div>
      </div>
      <div
        v-if="!isOnline"
        class="gps-error-banner"
        style="margin-bottom: 12px"
      >
        {{ t("tracking.offline") }}
      </div>
      <div v-if="gpsError" class="gps-error">{{ gpsError }}</div>
      <div class="manual-start-section">
        <button
          class="btn btn-primary btn-large pulse-btn"
          @click="manualStart"
        >
          {{
            tracking.autoTracking
              ? "Inizia uscita manuale"
              : t("tracking.start")
          }}
        </button>
        <label class="auto-toggle">
          <input v-model="tracking.autoTracking" type="checkbox" />
          <span>Tracking automatico</span>
        </label>
      </div>
    </div>

    <div v-else class="tracking-content">
      <transition name="fade">
        <div v-if="gpsWaiting" class="gps-waiting glass-banner">
          <div class="radar-spinner"></div>
          <span
            >Acquisizione segnale GPS... Spostati all'aperto per una maggiore
            accuratezza.</span
          >
        </div>
      </transition>
      <transition name="fade">
        <div v-if="gpsError && !gpsWaiting" class="gps-error-banner">
          {{ gpsError }}
        </div>
      </transition>

      <div class="map-wrapper glass-panel">
        <LiveMap ref="liveMapRef" />
      </div>

      <RideMetricsPanel />
      <ControlsBar
        :is-paused="isPaused"
        @pause="pauseTracking"
        @resume="resumeTracking"
        @stop="stopTracking"
      />

      <div
        v-if="tracking.gpxPath || tracking.gpxBlob"
        class="tracking-complete glass-panel"
      >
        <p>Tracciamento completato! File pronto per il caricamento.</p>
        <div class="tracking-actions">
          <button
            class="btn btn-primary"
            :disabled="isUploading"
            @click="uploadRide"
          >
            {{ isUploading ? t("tracking.uploading") : t("tracking.upload") }}
          </button>
          <button class="btn btn-secondary" @click="showFullRoute">
            {{ t("trackingTools.showRoute") }}
          </button>
          <button class="btn btn-secondary" @click="saveAsItinerary">
            {{ t("trackingTools.saveAsItinerary") }}
          </button>
          <button class="btn btn-secondary" @click="openAetherMap">
            {{ t("trackingTools.openAetherMap") }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch, computed } from "vue";
import { storeToRefs } from "pinia";
import { useTrackingStore, STORAGE_KEY } from "../stores/trackingStore";
import { useRouter } from "vue-router";
import { useI18n } from "../composables/useI18n";
import { useGpsOutlierFilter } from "../composables/useGpsOutlierFilter";
import {
  useGpsDirectionFilter,
  bearing as gpsBearing,
  detectTurnFromBearing,
} from "../composables/useGpsDirectionFilter";
import { useContinuousTracking } from "../composables/useContinuousTracking";
import LiveMap from "../components/LiveMap.vue";
import RideMetricsPanel from "../components/RideMetricsPanel.vue";
import ControlsBar from "../components/ControlsBar.vue";
import DailyTimeline from "../components/DailyTimeline.vue";
import ActivityRings from "../components/ActivityRings.vue";
import { apiUpload, apiPost } from "../utils/api";
import type { GpsPoint } from "../types/index";
import { haversineDistanceMeters } from "../utils/geo";
import { useVoiceCoach } from "../composables/useVoiceCoach";

const { t } = useI18n();
const router = useRouter();

const isOnline = ref(
  typeof navigator !== "undefined" ? navigator.onLine : true,
);

if (typeof window !== "undefined") {
  window.addEventListener("online", () => {
    isOnline.value = true;
  });
  window.addEventListener("offline", () => {
    isOnline.value = false;
  });
}

const liveMapRef = ref<InstanceType<typeof LiveMap> | null>(null);
const isUploading = ref(false);
const gpsWaiting = ref(false);
const gpsError = ref("");
const batterySaver = ref(false);

const activityType = ref<"ride" | "walk" | "hike" | "run" | "indoor" | "other">(
  "ride",
);
const activityOptions = [
  { value: "ride", label: " Bici" },
  { value: "run", label: " Corsa" },
  { value: "walk", label: " Passeggiata" },
  { value: "hike", label: " Trekking" },
  { value: "indoor", label: " Indoor" },
  { value: "other", label: " Altro" },
];
const activityTitle: Record<string, string> = {
  ride: "Tracciamento in bici",
  run: "Corsa",
  walk: "Passeggiata",
  hike: "Trekking",
  indoor: "Sessione indoor",
  other: "Tracciamento GPS",
};

let webStartTime = 0;
let webPausedAccumulatedMs = 0;
let webPausedAt: number | null = null;
let webLastPoint: GpsPoint | null = null;
let webDistance = 0;
let webElevationGain = 0;
let webFirstFixTimeout: number | null = null;
let webDirectionLastBearing: number | null = null;

const gpsOutlierFilter = useGpsOutlierFilter();
const directionFilter = useGpsDirectionFilter();

const tracking = useTrackingStore();
const { isTracking, isPaused } = storeToRefs(tracking);

const voiceCoach = useVoiceCoach();
const voiceCoachEnabled = ref(false);

const continuous = useContinuousTracking({
  onPosition: handleContinuousPosition,
  onError: handleContinuousError,
  onWaiting: () => {
    gpsWaiting.value = true;
    gpsError.value = "";
  },
  onFirstFix: () => {
    gpsWaiting.value = false;
    if (webFirstFixTimeout !== null) {
      clearTimeout(webFirstFixTimeout);
      webFirstFixTimeout = null;
    }
  },
  onActivityChange: (moving) => {
    if (!tracking.autoDetectActivities) return;
    handleActivityChange(moving);
  },
  batterySaver: () => batterySaver.value,
  autoStart: false,
  autoPauseOnHidden: false,
});

const todaySegments = computed(() => tracking.getTodaySegments());
const hasActiveSession = computed(() => tracking.currentSegment !== null);

function getVoiceCoachZone() {
  const p = tracking.power;
  if (p == null) return null;
  if (p > 250) return 4;
  if (p > 180) return 3;
  if (p > 120) return 2;
  return 1;
}

function syncVoiceCoach() {
  if (voiceCoachEnabled.value && isTracking.value) {
    voiceCoach.startVoiceCoachInterval(
      "recovery",
      "default",
      30000,
      getVoiceCoachZone,
    );
  } else {
    voiceCoach.stopVoiceCoachInterval();
  }
}

watch(voiceCoachEnabled, syncVoiceCoach);
watch(isTracking, syncVoiceCoach);

function handleContinuousPosition(point: GpsPoint) {
  if (!isTracking.value) return;
  processCandidate(
    point.lat,
    point.lon,
    point.altitude ?? null,
    point.timestampNumber ?? Date.now(),
  );
}

function handleContinuousError(error: GeolocationPositionError) {
  gpsWaiting.value = false;
  if (webFirstFixTimeout !== null) {
    clearTimeout(webFirstFixTimeout);
    webFirstFixTimeout = null;
  }
  if (error.code === 1) {
    gpsError.value =
      "GPS permission denied. Please allow location access and try again.";
    void stopTracking();
    return;
  }
  if (error.code === 2 || error.code === 3) {
    gpsError.value =
      "GPS signal lost. Please move outdoors or check your device.";
    return;
  }
  gpsError.value = `GPS Error: ${error.message}`;
}

function handleActivityChange(moving: boolean) {
  if (!tracking.autoDetectActivities) return;

  if (moving && !tracking.currentSegment) {
    tracking.startSegment();
  } else if (!moving && tracking.currentSegment) {
    if (tracking.currentSegment.state === "candidate") {
      tracking.closeCurrentSegment();
    }
  }

  if (tracking.currentSegment && moving) {
    tracking.currentSegment.state = "active";
    tracking.currentSegment.pausedSince = null;
  }
}

function startTracking() {
  continuous.start();
  tracking.start();
  webStartTime = Date.now();
  webPausedAccumulatedMs = 0;
  webPausedAt = null;
  webLastPoint = null;
  webDistance = 0;
  webElevationGain = 0;
  webDirectionLastBearing = null;
  gpsOutlierFilter.reset();
  directionFilter.reset();
  gpsError.value = "";
  webFirstFixTimeout = window.setTimeout(() => {
    if (gpsWaiting.value) {
      gpsWaiting.value = false;
      gpsError.value =
        "No GPS signal. On desktop, try moving near a window or use a GPS device.";
    }
  }, 15000);
}

async function manualStart() {
  await startTracking();
}

function pauseTracking() {
  continuous.pause();
  tracking.pause();
  if (webPausedAt === null) {
    webPausedAt = Date.now();
  }
}

function resumeTracking() {
  continuous.resume();
  tracking.resume();
  if (webPausedAt !== null) {
    webPausedAccumulatedMs += Date.now() - webPausedAt;
    webPausedAt = null;
  }
}

function handleVisibilityChange() {
  if (document.hidden) {
    if (isTracking.value && !isPaused.value) {
      pauseTracking();
    }
  } else {
    if (isTracking.value && isPaused.value) {
      resumeTracking();
    }
  }
}

async function stopTracking() {
  continuous.stop();
  let result: { gpxPath?: string | null; gpxBlob?: Blob | null } | void;
  if (tracking.currentSegment) {
    tracking.closeCurrentSegment();
  }
  if (window.BikeTracking?.stopTracking) {
    result = await window.BikeTracking.stopTracking();
  } else {
    result = stopWebTracking();
  }
  tracking.setGpxPath(result?.gpxPath || null);
  if (result?.gpxBlob) {
    tracking.setGpxBlob(result.gpxBlob);
  }
  tracking.stop();
  tracking.updateActivityRings();

  if (tracking.routePoints.length > 1) {
    void saveCurrentRide();
  }
}

async function saveCurrentRide(): Promise<number | null> {
  if (tracking.rideId) return tracking.rideId;
  if (tracking.routePoints.length <= 1) return null;
  try {
    const rideData = buildRidePayload();
    const result = await apiPost("/api/v1/rides", rideData);
    if (result.id) {
      tracking.setRideId(result.id as number);
      window.__toast?.add("Uscita salvata automaticamente!", "success");
      return result.id as number;
    }
  } catch (e) {
    console.warn("Salvataggio automatico fallito", e);
    window.__toast?.add(
      "Impossibile salvare l'uscita automaticamente.",
      "error",
    );
  }
  return null;
}

function buildRidePayload() {
  const validPoints = tracking.routePoints.filter(
    (p) => Number.isFinite(p.lat) && Number.isFinite(p.lon),
  );
  return {
    date: new Date().toISOString().slice(0, 10),
    distance_km: tracking.distance / 1000,
    duration_minutes: tracking.elapsedTime / 60,
    avg_speed_kmh: tracking.avgSpeed > 0 ? tracking.avgSpeed : undefined,
    elevation_gain_m: tracking.elevation > 0 ? tracking.elevation : undefined,
    gps_points: validPoints.map((p) => ({
      lat: p.lat,
      lon: p.lon,
      altitude: p.altitude ?? null,
      timestamp: p.timestamp ?? null,
      speed: p.speed ?? null,
      heart_rate: p.heartRate ?? null,
      cadence: p.cadence ?? null,
      power: p.power ?? null,
    })),
    source: "gps_tracking",
    activity_type: activityType.value,
    title: activityTitle[activityType.value] || "Tracciamento GPS",
  };
}

async function uploadRide() {
  try {
    isUploading.value = true;

    if (!tracking.rideId && tracking.routePoints.length > 1) {
      const savedId = await saveCurrentRide();
      if (savedId) {
        resetTrackingState();
        router.push("/rides");
        return;
      }
    }

    const blob = getUploadBlob();
    if (blob) {
      const file = new File([blob], `ride-${Date.now()}.gpx`, {
        type: "application/gpx+xml",
      });
      const result = await apiUpload("/api/v1/import/gpx", file);
      if (result.error) {
        const errorMsg =
          typeof result.error === "string" ? result.error : "Upload failed";
        window.__toast?.add(errorMsg, "error");
        return;
      }
      window.__toast?.add("Ride uploaded successfully!", "success");
      resetTrackingState();
      router.push("/rides");
      return;
    }
    if (tracking.gpxPath) {
      window.__toast?.add(
        "Unable to upload file from native path. Please use GPX export instead.",
        "error",
      );
      return;
    }
    window.__toast?.add("No ride to upload", "error");
  } catch (error) {
    console.error("Upload failed:", error);
    window.__toast?.add("Error during upload", "error");
  } finally {
    isUploading.value = false;
  }
}

function detectGpsTurn(
  lastPoint: GpsPoint | null,
  candidate: GpsPoint,
  lastBearing: number | null,
  distanceFromLast: number,
): boolean {
  if (!lastPoint || distanceFromLast < 3) return false;
  const candidateBearing = gpsBearing(lastPoint, candidate);
  return detectTurnFromBearing(lastBearing, candidateBearing);
}

function processCandidate(
  lat: number,
  lon: number,
  altitude: number | null,
  timestampMs: number,
  opts: {
    haversineDistance: (
      aLat: number,
      aLon: number,
      bLat: number,
      bLon: number,
    ) => number;
  } = {
    haversineDistance: haversineDistanceMeters,
  },
) {
  if (isPaused.value) return;
  if (
    !isFinite(lat) ||
    !isFinite(lon) ||
    lat < -90 ||
    lat > 90 ||
    lon < -180 ||
    lon > 180
  ) {
    return;
  }

  if (gpsWaiting.value) {
    gpsWaiting.value = false;
    gpsError.value = "";
    if (webFirstFixTimeout !== null) {
      clearTimeout(webFirstFixTimeout);
      webFirstFixTimeout = null;
    }
  }

  let distanceDelta = 0;
  if (webLastPoint && webLastPoint.timestampNumber != null) {
    const samePosition = webLastPoint.lat === lat && webLastPoint.lon === lon;
    const elapsedSinceLastMs = timestampMs - webLastPoint.timestampNumber;
    if (samePosition && elapsedSinceLastMs < 5000) {
      return;
    }
    if (elapsedSinceLastMs > 0) {
      distanceDelta = opts.haversineDistance(
        webLastPoint.lat,
        webLastPoint.lon,
        lat,
        lon,
      );
      if (distanceDelta > 5000) {
        return;
      }
      webDistance += distanceDelta;
    }
  }

  const candidate: GpsPoint = {
    lat,
    lon,
    altitude,
    timestamp: new Date(timestampMs).toISOString(),
    heartRate: null,
    cadence: null,
    power: null,
  };

  const speedOutlier = gpsOutlierFilter.isOutlier(candidate);
  const isTurning = detectGpsTurn(
    webLastPoint,
    candidate,
    webDirectionLastBearing,
    distanceDelta,
  );
  const directionOutlier = directionFilter.isDirectionOutlier(
    candidate,
    distanceDelta,
    isTurning,
  );

  if (speedOutlier || directionOutlier) {
    return;
  }

  const acceptedBearing = directionFilter.accept(
    candidate,
    distanceDelta,
    isTurning,
  );
  if (acceptedBearing !== null) {
    webDirectionLastBearing = acceptedBearing;
  }

  if (
    webLastPoint?.altitude !== null &&
    webLastPoint?.altitude !== undefined &&
    candidate.altitude !== null &&
    candidate.altitude !== undefined
  ) {
    webElevationGain += Math.max(0, candidate.altitude - webLastPoint.altitude);
  }

  const elapsedSeconds = getWebElapsedSeconds();
  const avgSpeed =
    elapsedSeconds > 0 ? webDistance / 1000 / (elapsedSeconds / 3600) : 0;
  const elapsedSinceLastMs = webLastPoint?.timestampNumber
    ? timestampMs - webLastPoint.timestampNumber
    : 0;
  const currentSpeed =
    elapsedSinceLastMs > 0 && distanceDelta > 0
      ? distanceDelta / 1000 / (elapsedSinceLastMs / 3600000)
      : 0;

  tracking.addPoint(candidate);
  tracking.updateMetrics({
    distance: webDistance,
    currentSpeed,
    avgSpeed,
    elapsedTime: elapsedSeconds,
    elevation: webElevationGain,
    points: tracking.routePoints.length,
  });
  tracking.updateSegmentFromPoint(candidate);
  liveMapRef.value?.addPoint(candidate.lat, candidate.lon);
  webLastPoint = { ...candidate, timestampNumber: timestampMs };
}

function stopWebTracking() {
  if (webFirstFixTimeout !== null) {
    clearTimeout(webFirstFixTimeout);
    webFirstFixTimeout = null;
  }
  const blob = new Blob([tracking.toGpx()], { type: "application/gpx+xml" });
  tracking.setGpxBlob(blob);
  return { gpxPath: null, gpxBlob: blob };
}

function getUploadBlob() {
  if (tracking.gpxBlob) return tracking.gpxBlob;
  if (tracking.routePoints.length > 0) {
    return new Blob([tracking.toGpx()], { type: "application/gpx+xml" });
  }
  return null;
}

function getWebElapsedSeconds() {
  return Math.max(
    0,
    (Date.now() - webStartTime - webPausedAccumulatedMs) / 1000,
  );
}

function resetTrackingState() {
  tracking.resetMetrics();
  tracking.setGpxPath(null);
  tracking.setGpxBlob(null);
  tracking.setRideId(null);
  tracking.clearPersistedState();
}

function showFullRoute() {
  const map = liveMapRef.value;
  if (!map) return;
  map.setRoute(tracking.routePoints.map((p) => ({ lat: p.lat, lon: p.lon })));
}

async function saveAsItinerary() {
  const date = new Date().toISOString().slice(0, 10);
  const title = activityTitle[activityType.value] || "Tracciamento GPS";
  const name = `${title} - ${date}`;
  const distKm = tracking.distance / 1000;
  const elevM = tracking.elevation;

  let rideId = tracking.rideId;
  if (!rideId && tracking.routePoints.length > 1) {
    try {
      const rideData = buildRidePayload();
      const result = await apiPost("/api/v1/rides", rideData);
      if (result.id) {
        tracking.setRideId(result.id as number);
        rideId = result.id as number;
      }
    } catch (e) {
      console.warn("Salvataggio ride per itinerario fallito", e);
      window.__toast?.add(
        "Impossibile salvare l'uscita come itinerario.",
        "error",
      );
      return;
    }
  }

  if (!rideId) {
    window.__toast?.add("Registra prima l'uscita.", "error");
    return;
  }

  try {
    const it = await apiPost("/api/v1/itineraries", {
      name,
      start_date: date,
      end_date: date,
      total_km: distKm || undefined,
      total_elevation_m: elevM || undefined,
    });
    if (it.id) {
      await apiPost(`/api/v1/itineraries/${it.id}/stages`, {
        title,
        distance_km: distKm || undefined,
        elevation_gain_m: elevM || undefined,
        ride_id: rideId,
        stage_day: 1,
      });
      window.__toast?.add("Itinerario creato!", "success");
    }
  } catch (e) {
    console.warn("Creazione itinerario fallita", e);
    window.__toast?.add("Impossibile creare l'itinerario.", "error");
  }
}

function openAetherMap() {
  router.push("/aethermap");
}

function onSelectSegment(segId: string) {
  const seg = tracking.segments.find((s) => s.id === segId);
  if (seg && seg.points.length > 0) {
    const map = liveMapRef.value;
    if (map) {
      map.setRoute(seg.points.map((p) => ({ lat: p.lat, lon: p.lon })));
    }
  }
}

onMounted(async () => {
  window.addEventListener("visibilitychange", handleVisibilityChange);
  const restored = tracking.restoreState();
  if (!restored) {
    resetTrackingState();
  } else if (tracking.routePoints.length > 0) {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        const state = JSON.parse(raw);
        if (state.timestamp) {
          webStartTime = state.timestamp;
          webPausedAccumulatedMs = 0;
          webPausedAt = null;
        }
      }
    } catch {
      // ignore
    }
    liveMapRef.value?.setRoute(
      tracking.routePoints.map((p) => ({ lat: p.lat, lon: p.lon })),
    );
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("visibilitychange", handleVisibilityChange);
  if (webFirstFixTimeout !== null) {
    clearTimeout(webFirstFixTimeout);
    webFirstFixTimeout = null;
  }
  continuous.stop();
  if (tracking.currentSegment && tracking.routePoints.length > 0) {
    tracking.closeCurrentSegment();
  }
  tracking.persistState();
});
</script>

<style scoped>
.tracking-panel {
  background: var(--bg);
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.tracking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.status-badge.paused {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
  box-shadow: 0 0 0 rgba(16, 185, 129, 0.4);
  animation: pulse 2s infinite;
}

.voice-coach-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 12px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}

.voice-coach-toggle input {
  accent-color: var(--accent);
}

.status-badge.paused .pulse-dot {
  animation: none;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.tracking-auto-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.auto-badge {
  font-size: 0.8rem;
  padding: 4px 10px;
  border-radius: 12px;
  background: rgba(100, 116, 139, 0.1);
  color: #64748b;
  font-weight: 500;
}

.auto-badge.active {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.premium-empty {
  padding: 40px 20px;
  background: linear-gradient(145deg, var(--bg-secondary), var(--bg));
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: inset 0 2px 10px rgba(255, 255, 255, 0.05);
}

.glass-icon {
  font-size: 4rem;
  margin-bottom: 16px;
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.1));
}

.modern-select {
  margin: 24px auto;
}

.modern-select label {
  font-weight: 500;
  margin-bottom: 8px;
  display: block;
}

.select-wrapper {
  position: relative;
  background: var(--bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.select-wrapper:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.select-wrapper select {
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  font-size: 1rem;
  color: var(--text-primary);
  appearance: none;
  cursor: pointer;
}

.pulse-btn {
  background: linear-gradient(135deg, var(--accent), #2563eb);
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
  transform: translateY(0);
  transition: all 0.2s ease;
  padding: 14px 32px;
  font-size: 1.1rem;
  letter-spacing: 0.5px;
}

.pulse-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
}

.tracking-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.tracking-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: center;
}

.tracking-actions .btn {
  min-width: 140px;
}

.glass-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
}

.map-wrapper {
  padding: 2px;
}

.tracking-content :deep(.map-container) {
  height: 400px;
  min-height: 400px;
  border-radius: calc(var(--radius-lg) - 2px);
}

.glass-banner {
  background: rgba(59, 130, 246, 0.1);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  color: var(--accent);
  font-weight: 500;
}

.radar-spinner {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.2);
  position: relative;
  overflow: hidden;
}

.radar-spinner::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  width: 50%;
  height: 50%;
  background: linear-gradient(45deg, transparent, var(--accent));
  transform-origin: 0% 0%;
  animation: radar 1.5s linear infinite;
}

@keyframes radar {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.tracking-complete {
  padding: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.tracking-complete p {
  font-size: 1.1rem;
  color: var(--text-primary);
  font-weight: 500;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.gps-error-banner {
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: var(--radius-sm);
  color: var(--error);
  font-size: 0.85rem;
  margin-bottom: 12px;
}

.gps-error {
  color: var(--error);
  font-size: 0.85rem;
  margin-top: 8px;
}

.daily-summary-section {
  margin-top: 24px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
}

.daily-summary-section h3 {
  margin: 0 0 16px 0;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.daily-stats {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  justify-content: center;
}

.daily-stats .stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.daily-stats .stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent);
}

.daily-stats .stat-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.manual-start-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}

.auto-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}

.auto-toggle input {
  accent-color: var(--accent);
}

@media (max-width: 768px) {
  .tracking-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .tracking-content :deep(.map-container) {
    height: 300px;
    min-height: 300px;
  }

  .daily-stats {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
