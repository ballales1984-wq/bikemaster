<template>
   <section class="panel tracking-panel">
      <div class="tracking-header">
        <h2>{{ t('tracking.title') }}</h2>
        <div v-if="isTracking" class="tracking-status">
          <span class="status-badge" :class="{ paused: isPaused }">
            <span class="pulse-dot"></span>
            {{ isPaused ? t('tracking.paused') : t('tracking.inProgress') }}
          </span>
        </div>
      </div>

      <div v-if="!isTracking && !tracking.gpxPath && !tracking.gpxBlob" class="empty-state premium-empty">
        <div class="empty-icon glass-icon">📍</div>
        <div class="empty-title">{{ t('tracking.ready') }}</div>
        <div class="empty-desc">
          {{ t('tracking.readyDesc') }}
        </div>
        <div class="activity-select modern-select">
          <label for="activity-type">{{ t('tracking.activityType') }}</label>
          <div class="select-wrapper">
            <select id="activity-type" v-model="activityType">
              <option v-for="opt in activityOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>
        <div v-if="!isOnline" class="gps-error-banner" style="margin-bottom:12px">
           {{ t('tracking.offline') }}
        </div>
        <div v-if="gpsError" class="gps-error">{{ gpsError }}</div>
        <button class="btn btn-primary btn-large pulse-btn" @click="startTracking">
          {{ t('tracking.start') }}
        </button>
      </div>

      <div v-else class="tracking-content">
        <transition name="fade">
          <div v-if="gpsWaiting" class="gps-waiting glass-banner">
            <div class="radar-spinner"></div>
            <span>Acquiring GPS signal... Move outdoors for better accuracy.</span>
          </div>
        </transition>
        <transition name="fade">
          <div v-if="gpsError && !gpsWaiting" class="gps-error-banner">{{ gpsError }}</div>
        </transition>
        
        <div class="map-wrapper glass-panel">
          <LiveMap ref="liveMapRef" />
        </div>
        
        <RideMetricsPanel />
        <ControlsBar :is-paused="isPaused" @pause="pauseTracking" @resume="resumeTracking" @stop="stopTracking" />

        <div v-if="tracking.gpxPath || tracking.gpxBlob" class="tracking-complete glass-panel">
          <p>Tracking completed! File ready for upload.</p>
          <button class="btn btn-primary btn-large" :disabled="isUploading" @click="uploadRide">
            {{ isUploading ? 'Uploading...' : 'Upload to BikeMaster' }}
          </button>
        </div>
      </div>
   </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useTrackingStore } from '../stores/trackingStore'
import { useRouter } from 'vue-router'
import { useI18n } from '../composables/useI18n'
import { useBatteryEfficientGps } from '../composables/useBatteryEfficientGps'
import { useGpsOutlierFilter } from '../composables/useGpsOutlierFilter'
import {
  useGpsDirectionFilter,
  bearing as gpsBearing,
  detectTurnFromBearing,
} from '../composables/useGpsDirectionFilter'
import LiveMap from '../components/LiveMap.vue'
import RideMetricsPanel from '../components/RideMetricsPanel.vue'
import ControlsBar from '../components/ControlsBar.vue'
import { apiUpload, apiPost } from '../utils/api'
import type { GpsPoint, NativeGpsSample } from '../types/index'
import { haversineDistanceMeters } from '../utils/geo'

const { t } = useI18n()
const router = useRouter()

const isOnline = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => { isOnline.value = true })
  window.addEventListener('offline', () => { isOnline.value = false })
}

const liveMapRef = ref<InstanceType<typeof LiveMap> | null>(null)
const isUploading = ref(false)
const gpsWaiting = ref(false)
const gpsError = ref('')
const batterySaver = ref(false)

const activityType = ref<'ride' | 'walk' | 'hike' | 'run' | 'indoor' | 'other'>('ride')
const activityOptions = [
  { value: 'ride', label: '🚴 Bici' },
  { value: 'run', label: '🏃 Corsa' },
  { value: 'walk', label: '🚶 Passeggiata' },
  { value: 'hike', label: '🥾 Trekking' },
  { value: 'indoor', label: '🏠 Indoor' },
  { value: 'other', label: '📍 Altro' },
]
const activityTitle: Record<string, string> = {
  ride: 'Tracciamento in bici',
  run: 'Corsa',
  walk: 'Passeggiata',
  hike: 'Trekking',
  indoor: 'Sessione indoor',
  other: 'Tracciamento GPS',
}

let webStartTime = 0
let webPausedAccumulatedMs = 0
let webPausedAt: number | null = null
let webLastPoint: GpsPoint | null = null
let webDistance = 0
let webElevationGain = 0
let webFirstFixTimeout: number | null = null
let webDirectionLastBearing: number | null = null

const gpsOutlierFilter = useGpsOutlierFilter()
const directionFilter = useGpsDirectionFilter()

const tracking = useTrackingStore()
const {
  isTracking,
  isPaused,
} = storeToRefs(tracking)

const gps = useBatteryEfficientGps({
  batterySaver: () => batterySaver.value,
  onWaiting: () => {
    gpsWaiting.value = true
    gpsError.value = ''
  },
  onFirstFix: () => {
    gpsWaiting.value = false
    if (webFirstFixTimeout !== null) {
      clearTimeout(webFirstFixTimeout)
      webFirstFixTimeout = null
    }
  },
  onPosition: handleWebPosition,
  onError: handleWebError,
})

async function startTracking() {
  const hasPermission = await checkPermissions()
  if (!hasPermission) {
    alert('GPS permissions required for tracking')
    return
  }
  if (window.BikeTracking?.startTracking) {
    await window.BikeTracking.startTracking()
    if (window.BikeTracking.onPosition) {
      window.BikeTracking.onPosition(handleNativePosition)
    }
    if (window.BikeTracking.onError) {
      window.BikeTracking.onError((err) => handleWebError(err as unknown as GeolocationPositionError))
    }
  } else {
    startWebTracking()
  }
  tracking.start()
}

function handleNativePosition(sample: NativeGpsSample) {
  processCandidate(
    sample.lat,
    sample.lon,
    sample.altitude ?? null,
    sample.timestamp,
  )
}

async function checkPermissions(): Promise<boolean> {
  if (!window.BikeTracking?.checkPermissions) {
    if (!navigator.geolocation) return false
    try {
      const result = await navigator.permissions.query({ name: 'geolocation' })
      if (result.state === 'granted') return true
      if (result.state === 'prompt') return true
      return false
    } catch {
      return true
    }
  }
  return window.BikeTracking.checkPermissions().then((result) => result.granted)
}

async function pauseTracking() {
  if (window.BikeTracking?.pauseTracking) {
    await window.BikeTracking.pauseTracking()
  } else if (isPaused.value === false) {
    gps.pause()
  }
  tracking.pause()
}

async function resumeTracking() {
  if (window.BikeTracking?.resumeTracking) {
    await window.BikeTracking.resumeTracking()
  } else if (webPausedAt !== null) {
    webPausedAccumulatedMs += Date.now() - webPausedAt
    webPausedAt = null
  }
  tracking.resume()
}

async function stopTracking() {
  let result: { gpxPath?: string | null; gpxBlob?: Blob | null } | void
  if (window.BikeTracking?.stopTracking) {
    result = await window.BikeTracking.stopTracking()
  } else {
    result = stopWebTracking()
  }
  tracking.setGpxPath(result?.gpxPath || null)
  if (result?.gpxBlob) {
    tracking.setGpxBlob(result.gpxBlob)
  }
  tracking.stop()
}

async function uploadRide() {
   try {
      isUploading.value = true

      if (tracking.routePoints.length > 1) {
        try {
          const validPoints = tracking.routePoints.filter(
            (p) => Number.isFinite(p.lat) && Number.isFinite(p.lon),
          )
          const rideData = {
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
            })),
            source: "gps_tracking",
            activity_type: activityType.value,
            title: activityTitle[activityType.value] || "Tracciamento GPS",
          }
          const result = await apiPost("/api/v1/rides", rideData)
          if (result.id) {
            alert("Uscita salvata con successo!")
            resetTrackingState()
            router.push("/rides")
            return
          }
        } catch (directError) {
          console.warn("Salvataggio diretto fallito, provo con GPX...", directError)
        }
      }

      const blob = getUploadBlob()
      if (blob) {
        const file = new File([blob], `ride-${Date.now()}.gpx`, { type: 'application/gpx+xml' })
        const result = await apiUpload('/api/v1/import/gpx', file)
        if (result.error) {
          alert(result.error || 'Upload failed')
          return
        }
        alert('Ride uploaded successfully!')
        resetTrackingState()
        router.push('/rides')
        return
      }
      if (tracking.gpxPath) {
        alert('Unable to upload file from native path. Please use GPX export instead.')
        return
      }
      alert('No ride to upload')
    } catch (error) {
     console.error('Upload failed:', error)
     alert('Error during upload')
    } finally {
      isUploading.value = false
    }
  }

function startWebTracking() {
  webStartTime = Date.now()
  webPausedAccumulatedMs = 0
  webPausedAt = null
  webLastPoint = null
  webDistance = 0
  webElevationGain = 0
  webDirectionLastBearing = null
  gpsOutlierFilter.reset()
  directionFilter.reset()
  gpsError.value = ''
  webFirstFixTimeout = window.setTimeout(() => {
    if (gpsWaiting.value) {
      gpsWaiting.value = false
      gpsError.value = 'No GPS signal. On desktop, try moving near a window or use a GPS device.'
    }
  }, 15000)
  gps.start()
}

function detectGpsTurn(
  lastPoint: GpsPoint | null,
  candidate: GpsPoint,
  lastBearing: number | null,
  distanceFromLast: number,
): boolean {
  if (!lastPoint || distanceFromLast < 3) return false
  const candidateBearing = gpsBearing(lastPoint, candidate)
  return detectTurnFromBearing(lastBearing, candidateBearing)
}

function processCandidate(
  lat: number,
  lon: number,
  altitude: number | null,
  timestampMs: number,
  opts: { haversineDistance: (aLat: number, aLon: number, bLat: number, bLon: number) => number } = {
    haversineDistance: haversineDistanceMeters,
  },
) {
  if (!isTracking.value || isPaused.value) return
  if (!isFinite(lat) || !isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    return
  }

  if (gpsWaiting.value) {
    gpsWaiting.value = false
    gpsError.value = ''
    if (webFirstFixTimeout !== null) {
      clearTimeout(webFirstFixTimeout)
      webFirstFixTimeout = null
    }
  }

  let distanceDelta = 0
  if (webLastPoint && webLastPoint.timestampNumber != null) {
    const samePosition = webLastPoint.lat === lat && webLastPoint.lon === lon
    const elapsedSinceLastMs = timestampMs - webLastPoint.timestampNumber
    if (samePosition && elapsedSinceLastMs < 5000) {
      return
    }
    if (elapsedSinceLastMs > 0) {
      distanceDelta = opts.haversineDistance(
        webLastPoint.lat,
        webLastPoint.lon,
        lat,
        lon,
      )
      if (distanceDelta > 5000) {
        return
      }
      webDistance += distanceDelta
    }
  }

  const candidate: GpsPoint = {
    lat,
    lon,
    altitude,
    timestamp: new Date(timestampMs).toISOString(),
  }

  const speedOutlier = gpsOutlierFilter.isOutlier(candidate)
  const isTurning = detectGpsTurn(webLastPoint, candidate, webDirectionLastBearing, distanceDelta)
  const directionOutlier = directionFilter.isDirectionOutlier(
    candidate,
    distanceDelta,
    isTurning,
  )

  if (speedOutlier || directionOutlier) {
    return
  }

  const acceptedBearing = directionFilter.accept(candidate, distanceDelta, isTurning)
  if (acceptedBearing !== null) {
    webDirectionLastBearing = acceptedBearing
  }

  if (
    webLastPoint?.altitude !== null &&
    webLastPoint?.altitude !== undefined &&
    candidate.altitude !== null &&
    candidate.altitude !== undefined
  ) {
    webElevationGain += Math.max(0, candidate.altitude - webLastPoint.altitude)
  }

  const elapsedSeconds = getWebElapsedSeconds()
  const avgSpeed = elapsedSeconds > 0 ? (webDistance / 1000) / (elapsedSeconds / 3600) : 0
  const elapsedSinceLastMs = webLastPoint?.timestampNumber
    ? timestampMs - webLastPoint.timestampNumber
    : 0
  const currentSpeed = elapsedSinceLastMs > 0 && distanceDelta > 0
    ? (distanceDelta / 1000) / (elapsedSinceLastMs / 3600000)
    : 0

  tracking.addPoint(candidate)
  tracking.updateMetrics({
    distance: webDistance,
    currentSpeed,
    avgSpeed,
    elapsedTime: elapsedSeconds,
    elevation: webElevationGain,
    points: tracking.routePoints.length,
  })
  liveMapRef.value?.addPoint(candidate.lat, candidate.lon)
  webLastPoint = { ...candidate, timestampNumber: timestampMs }
}

function handleWebPosition(position: GeolocationPosition) {
  processCandidate(
    position.coords.latitude,
    position.coords.longitude,
    position.coords.altitude,
    position.timestamp,
  )
}

function handleWebError(error: GeolocationPositionError) {
  gpsWaiting.value = false
  if (webFirstFixTimeout !== null) {
    clearTimeout(webFirstFixTimeout)
    webFirstFixTimeout = null
  }
  if (error.code === 1) {
    gpsError.value = 'GPS permission denied. Please allow location access and try again.'
    alert('GPS permission denied. Please allow location access and try again.')
    void stopTracking()
    return
  }
  if (error.code === 2 || error.code === 3) {
    gpsError.value = 'GPS signal lost. Please move outdoors or check your device.'
    return
  }
  alert(`GPS Error: ${error.message}`)
}

function stopWebTracking() {
  if (webFirstFixTimeout !== null) {
    clearTimeout(webFirstFixTimeout)
    webFirstFixTimeout = null
  }
  gps.stop()
  gpsWaiting.value = false
  const blob = new Blob([tracking.toGpx()], { type: 'application/gpx+xml' })
  tracking.setGpxBlob(blob)
  return { gpxPath: null, gpxBlob: blob }
}

function getUploadBlob() {
  if (tracking.gpxBlob) return tracking.gpxBlob
  if (tracking.routePoints.length > 0) {
    return new Blob([tracking.toGpx()], { type: 'application/gpx+xml' })
  }
  return null
}

function getWebElapsedSeconds() {
  return Math.max(0, (Date.now() - webStartTime - webPausedAccumulatedMs) / 1000)
}

function resetTrackingState() {
  tracking.resetMetrics()
  tracking.setGpxPath(null)
  tracking.setGpxBlob(null)
}

onMounted(() => {
  resetTrackingState()
})

onBeforeUnmount(() => {
  if (webFirstFixTimeout !== null) {
    clearTimeout(webFirstFixTimeout)
    webFirstFixTimeout = null
  }
  gps.stop()
  if (tracking.isTracking && !tracking.gpxBlob) {
    stopWebTracking()
  }
})
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

.status-badge.paused .pulse-dot {
  animation: none;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
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
  transition: border-color 0.2s, box-shadow 0.2s;
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
  content: '';
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
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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
</style>
