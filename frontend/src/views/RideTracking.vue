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
import LiveMap from '../components/LiveMap.vue'
import RideMetricsPanel from '../components/RideMetricsPanel.vue'
import ControlsBar from '../components/ControlsBar.vue'
import { apiUpload } from '../utils/api'
import type { GpsPoint } from '../types/index'
import { BikeTracking, type TrackingStateEvent, type TrackingStoppedEvent } from '../plugins/bikeTracking'

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
const isNativeTracking = ref(false)

let webWatchId: number | null = null
let webStartTime = 0
let webPausedAccumulatedMs = 0
let webPausedAt: number | null = null
let webLastPoint: GpsPoint | null = null
let webDistance = 0
let webElevationGain = 0
let webFirstFixTimeout: number | null = null

let stateListener: { remove: () => void } | null = null
let stoppedListener: { remove: () => void } | null = null
let isHandlingStop = false

const tracking = useTrackingStore()
const {
  isTracking,
  isPaused,
} = storeToRefs(tracking)

async function startTracking() {
  const hasPermission = await checkPermissions()
  if (!hasPermission) {
    alert('GPS permissions required for tracking')
    return
  }
  if (BikeTracking.startTracking) {
    isNativeTracking.value = true
    await BikeTracking.startTracking()
    registerNativeListeners()
  } else {
    isNativeTracking.value = false
    startWebTracking()
  }
  tracking.start()
}

async function registerNativeListeners() {
  if (stateListener) {
    stateListener.remove()
    stateListener = null
  }
  if (stoppedListener) {
    stoppedListener.remove()
    stoppedListener = null
  }

  stateListener = await BikeTracking.addListener('trackingState', (info: TrackingStateEvent) => {
    if (!isTracking.value || isPaused.value) return

    const distance = info.distance
    const currentSpeed = info.currentSpeed
    const avgSpeed = info.avgSpeed
    const elapsedTime = info.elapsedTime
    const elevation = info.elevation
    const points = info.points

    tracking.updateMetrics({
      distance,
      currentSpeed,
      avgSpeed,
      elapsedTime,
      elevation,
      points,
    })

    if (info.lastLatitude != null && info.lastLongitude != null) {
      tracking.addPoint({
        lat: info.lastLatitude,
        lon: info.lastLongitude,
        altitude: info.elevation ?? undefined,
        timestamp: new Date().toISOString(),
      })
      liveMapRef.value?.addPoint(info.lastLatitude, info.lastLongitude)
    }

    if (info.heartRate !== null && info.heartRate !== undefined) {
      tracking.updateMetrics({ heartRate: info.heartRate })
    }
    if (info.cadence !== null && info.cadence !== undefined) {
      tracking.updateMetrics({ cadence: info.cadence })
    }
    if (info.power !== null && info.power !== undefined) {
      tracking.updateMetrics({ power: info.power })
    }
  })

  stoppedListener = await BikeTracking.addListener('trackingStopped', async (info: TrackingStoppedEvent) => {
    if (isHandlingStop) return
    if (info.error) {
      alert('Tracking error: ' + info.error)
      return
    }
    if (info.gpxPath) {
      tracking.setGpxPath(info.gpxPath)
      try {
        const result = await BikeTracking.readGpx({ path: info.gpxPath })
        const binary = atob(result.base64)
        const bytes = new Uint8Array(binary.length)
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i)
        }
        const blob = new Blob([bytes], { type: 'application/gpx+xml' })
        tracking.setGpxBlob(blob)
      } catch {
        console.error('Failed to read native GPX file')
      }
    }
    tracking.stop()
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('BikeMaster', {
        body: 'Tracciamento completato! Carica la tua uscita.',
        icon: '/icon-192.png',
      })
    }
  })
}

async function checkPermissions(): Promise<boolean> {
  if (BikeTracking?.checkPermissions) {
    const result = await BikeTracking.checkPermissions()
    return result.granted
  }
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

async function pauseTracking() {
  if (BikeTracking?.pauseTracking) {
    await BikeTracking.pauseTracking()
  } else if (isPaused.value === false) {
    webPausedAt = Date.now()
  }
  tracking.pause()
}

async function resumeTracking() {
  if (BikeTracking?.resumeTracking) {
    await BikeTracking.resumeTracking()
  } else if (webPausedAt !== null) {
    webPausedAccumulatedMs += Date.now() - webPausedAt
    webPausedAt = null
  }
  tracking.resume()
}

async function stopTracking() {
  try {
    isHandlingStop = true
    if (BikeTracking.stopTracking) {
      const result = await BikeTracking.stopTracking()
      if (result.gpxPath) {
        tracking.setGpxPath(result.gpxPath)
        try {
          const gpx = await BikeTracking.readGpx({ path: result.gpxPath })
          const binary = atob(gpx.base64)
          const bytes = new Uint8Array(binary.length)
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i)
          }
          const blob = new Blob([bytes], { type: 'application/gpx+xml' })
          tracking.setGpxBlob(blob)
          tracking.stop(blob)
        } catch {
          console.error('Failed to read native GPX file')
          tracking.stop()
        }
      } else {
        tracking.stop()
      }
    } else {
      const webBlob = stopWebTracking()
      tracking.stop(webBlob.gpxBlob)
    }
  } catch (error) {
    console.error('Stop tracking failed:', error)
    tracking.stop()
  } finally {
    isHandlingStop = false
  }
}

async function uploadRide() {
   try {
     isUploading.value = true
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
  if (webWatchId !== null) {
    navigator.geolocation.clearWatch(webWatchId)
    webWatchId = null
  }
  webStartTime = Date.now()
  webPausedAccumulatedMs = 0
  webPausedAt = null
  webLastPoint = null
  webDistance = 0
  webElevationGain = 0
  gpsWaiting.value = true
  gpsError.value = ''
  webWatchId = navigator.geolocation.watchPosition(
    handleWebPosition,
    handleWebError,
    {
      enableHighAccuracy: true,
      maximumAge: 1000,
      timeout: 10000,
    }
  )
  webFirstFixTimeout = window.setTimeout(() => {
    if (gpsWaiting.value) {
      gpsWaiting.value = false
      gpsError.value = 'No GPS signal. On desktop, try moving near a window or use a GPS device.'
    }
  }, 15000)
}

function handleWebPosition(position: GeolocationPosition) {
  if (!isTracking.value || isPaused.value) return

  const lat = position.coords.latitude
  const lon = position.coords.longitude
  if (!isFinite(lat) || !isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    return
  }

  const accuracy = position.coords.accuracy
  if (accuracy != null && accuracy > 20) {
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
  if (webWatchId !== null) {
    navigator.geolocation.clearWatch(webWatchId)
    webWatchId = null
  }
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
  if (BikeTracking.getTrackingState) {
    BikeTracking.getTrackingState().then((state) => {
      if (state.isTracking && state.outputPath) {
        gpsWaiting.value = true
        BikeTracking.readGpx({ path: state.outputPath }).then((gpx) => {
          const binary = atob(gpx.base64)
          const bytes = new Uint8Array(binary.length)
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i)
          }
          const blob = new Blob([bytes], { type: 'application/gpx+xml' })
          tracking.setGpxBlob(blob)
          tracking.setGpxPath(state.outputPath)
          gpsWaiting.value = false
        }).catch(() => {
          gpsWaiting.value = false
        })
      }
    }).catch(() => {
      // ignore
    })
  }
})

onBeforeUnmount(() => {
  if (stateListener) {
    stateListener.remove()
    stateListener = null
  }
  if (stoppedListener) {
    stoppedListener.remove()
    stoppedListener = null
  }
  if (webFirstFixTimeout !== null) {
    clearTimeout(webFirstFixTimeout)
    webFirstFixTimeout = null
  }
  if (webWatchId !== null) {
    navigator.geolocation.clearWatch(webWatchId)
    webWatchId = null
  }
  if (!isNativeTracking.value && tracking.isTracking && !tracking.gpxBlob) {
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
