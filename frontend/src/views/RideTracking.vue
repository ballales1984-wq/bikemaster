<template>
   <section class="panel">
      <div class="tracking-header">
        <h2>{{ t('tracking.title') }}</h2>
        <div v-if="isTracking" class="tracking-status">
          <span class="status-badge" :class="{ paused: isPaused }">
            {{ isPaused ? t('tracking.paused') : t('tracking.inProgress') }}
          </span>
        </div>
      </div>

        <div v-if="!isTracking && !tracking.gpxPath && !tracking.gpxBlob" class="empty-state">
       <div class="empty-icon">📍</div>
       <div class="empty-title">{{ t('tracking.ready') }}</div>
       <div class="empty-desc">
         {{ t('tracking.readyDesc') }}
       </div>
        <div v-if="!isOnline" class="gps-error-banner" style="margin-bottom:12px">
          {{ t('tracking.offline') }}
        </div>
       <div v-if="gpsError" class="gps-error">{{ gpsError }}</div>
       <button class="btn btn-primary btn-large" @click="startTracking">
         {{ t('tracking.start') }}
       </button>
        </div>

      <div v-else class="tracking-content">
        <div v-if="gpsWaiting" class="gps-waiting">
          <span class="gps-spinner"></span>
          Acquiring GPS signal... Move outdoors for better accuracy.
        </div>
        <div v-if="gpsError && !gpsWaiting" class="gps-error-banner">{{ gpsError }}</div>
        <LiveMap ref="liveMapRef" />
        <RideMetricsPanel />
        <ControlsBar :is-paused="isPaused" @pause="pauseTracking" @resume="resumeTracking" @stop="stopTracking" />

        <div v-if="tracking.gpxPath || tracking.gpxBlob" class="tracking-complete">
          <p>Tracking completed! File ready for upload.</p>
          <button class="btn btn-primary" :disabled="isUploading" @click="uploadRide">
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
import LiveMap from '../components/LiveMap.vue'
import RideMetricsPanel from '../components/RideMetricsPanel.vue'
import ControlsBar from '../components/ControlsBar.vue'
import { apiUpload, apiPost } from '../utils/api'
import type { GpsPoint } from '../types/index'

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

let webStartTime = 0
let webPausedAccumulatedMs = 0
let webPausedAt: number | null = null
let webLastPoint: GpsPoint | null = null
let webDistance = 0
let webElevationGain = 0
let webFirstFixTimeout: number | null = null

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
  } else {
    startWebTracking()
  }
  tracking.start()
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
            title: "Tracciamento GPS",
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
  gpsError.value = ''
  webFirstFixTimeout = window.setTimeout(() => {
    if (gpsWaiting.value) {
      gpsWaiting.value = false
      gpsError.value = 'No GPS signal. On desktop, try moving near a window or use a GPS device.'
    }
  }, 15000)
  gps.start()
}

function handleWebPosition(position: GeolocationPosition) {
  if (!isTracking.value || isPaused.value) return

  const lat = position.coords.latitude
  const lon = position.coords.longitude
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

  const point = {
    lat,
    lon,
    altitude: position.coords.altitude,
    timestamp: new Date(position.timestamp).toISOString(),
  }

  if (webLastPoint && webLastPoint.timestampNumber != null) {
    const samePosition = webLastPoint.lat === lat && webLastPoint.lon === lon
    const elapsedSinceLastMs = position.timestamp - webLastPoint.timestampNumber
    if (samePosition && elapsedSinceLastMs < 5000) {
      return
    }
    if (elapsedSinceLastMs > 0) {
      const distanceDelta = haversineDistanceMeters(webLastPoint.lat, webLastPoint.lon, lat, lon)
      if (distanceDelta > 5000) {
        return
      }
      webDistance += distanceDelta
    }
  }

  if (
    webLastPoint?.altitude !== null &&
    webLastPoint?.altitude !== undefined &&
    point.altitude !== null &&
    point.altitude !== undefined
  ) {
    webElevationGain += Math.max(0, point.altitude - webLastPoint.altitude)
  }

  const elapsedSeconds = getWebElapsedSeconds()
  const avgSpeed = elapsedSeconds > 0 ? (webDistance / 1000) / (elapsedSeconds / 3600) : 0
  const elapsedSinceLastMs = webLastPoint?.timestampNumber
    ? position.timestamp - webLastPoint.timestampNumber
    : 0
  const currentSpeed = elapsedSinceLastMs > 0
    ? (webDistance / 1000) / (elapsedSinceLastMs / 3600000)
    : 0

  tracking.addPoint(point)
  tracking.updateMetrics({
    distance: webDistance,
    currentSpeed,
    avgSpeed,
    elapsedTime: elapsedSeconds,
    elevation: webElevationGain,
    points: tracking.routePoints.length,
  })
  liveMapRef.value?.addPoint(point.lat, point.lon)
  webLastPoint = { ...point, timestampNumber: position.timestamp }
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

function haversineDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number) {
  const radius = 6371000
  const toRadians = (value: number) => (value * Math.PI) / 180
  const dLat = toRadians(lat2 - lat1)
  const dLon = toRadians(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(dLon / 2) ** 2
  return 2 * radius * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
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
.tracking-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tracking-content :deep(.map-container) {
  height: 400px;
  min-height: 400px;
}

.gps-waiting {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: var(--radius-sm);
  color: var(--accent);
  font-size: 0.9rem;
  margin-bottom: 16px;
}

.gps-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(59, 130, 246, 0.3);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
