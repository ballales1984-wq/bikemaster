<template>
   <section class="panel">
     <div class="tracking-header">
       <h2>GPS Tracking</h2>
       <div v-if="isTracking" class="tracking-status">
         <span class="status-badge" :class="{ paused: isPaused }">
           {{ isPaused ? 'Paused' : 'In progress' }}
         </span>
       </div>
     </div>

      <div v-if="!isTracking && !tracking.gpxPath && !tracking.gpxBlob" class="empty-state">
        <div class="empty-icon">📍</div>
        <div class="empty-title">Ready to track your ride</div>
        <div class="empty-desc">
          Press the button below to start recording your route in real-time.
        </div>
        <button class="btn btn-primary btn-large" @click="startTracking">
          Start Tracking
        </button>
      </div>

     <div v-else class="tracking-content">
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
import { useTrackingStore } from '../stores/trackingStore'
import LiveMap from '../components/LiveMap.vue'
import RideMetricsPanel from '../components/RideMetricsPanel.vue'
import ControlsBar from '../components/ControlsBar.vue'
import { apiUpload } from '../utils/api'
import type { GpsPoint } from '../types/index'

const liveMapRef = ref<InstanceType<typeof LiveMap> | null>(null)
const isUploading = ref(false)

let webWatchId: number | null = null
let webStartTime = 0
let webPausedAccumulatedMs = 0
let webPausedAt: number | null = null
let webLastPoint: GpsPoint | null = null
let webDistance = 0
let webElevationGain = 0

const tracking = useTrackingStore()
const {
  isTracking,
  isPaused,
  start,
  stop,
  pause,
  resume,
  addPoint,
  updateMetrics,
  resetMetrics,
  setGpxPath,
  setGpxBlob,
  toGpx,
} = tracking

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
  start()
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
    webPausedAt = Date.now()
  }
  pause()
}

async function resumeTracking() {
  if (window.BikeTracking?.resumeTracking) {
    await window.BikeTracking.resumeTracking()
  } else if (webPausedAt !== null) {
    webPausedAccumulatedMs += Date.now() - webPausedAt
    webPausedAt = null
  }
  resume()
}

async function stopTracking() {
  let result: { gpxPath?: string | null; gpxBlob?: Blob | null } | void
  if (window.BikeTracking?.stopTracking) {
    result = await window.BikeTracking.stopTracking()
  } else {
    result = stopWebTracking()
  }
  setGpxPath(result?.gpxPath || null)
  if (result?.gpxBlob) {
    setGpxBlob(result.gpxBlob)
  }
  stop()
}

async function uploadRide() {
   try {
     isUploading.value = true
     const blob = getUploadBlob()
     if (blob) {
       const file = new File([blob], `ride-${Date.now()}.gpx`, { type: 'application/gpx+xml' })
       await apiUpload('/api/v1/import/gpx', file)
       alert('Ride uploaded successfully!')
       resetTrackingState()
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
  webWatchId = navigator.geolocation.watchPosition(
    handleWebPosition,
    handleWebError,
    {
      enableHighAccuracy: true,
      maximumAge: 1000,
      timeout: 10000,
    }
  )
}

function handleWebPosition(position: GeolocationPosition) {
  if (!isTracking.value || isPaused.value) return

  const point = {
    lat: position.coords.latitude,
    lon: position.coords.longitude,
    altitude: position.coords.altitude,
    timestamp: new Date(position.timestamp).toISOString(),
  }

  const distanceDelta = webLastPoint
    ? haversineDistanceMeters(webLastPoint.lat, webLastPoint.lon, point.lat, point.lon)
    : 0
  webDistance += distanceDelta

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
    ? (distanceDelta / 1000) / (elapsedSinceLastMs / 3600000)
    : 0

  addPoint(point)
  updateMetrics({
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
  alert(`GPS Error: ${error.message}`)
}

function stopWebTracking() {
  if (webWatchId !== null) {
    navigator.geolocation.clearWatch(webWatchId)
    webWatchId = null
  }
  const blob = new Blob([toGpx()], { type: 'application/gpx+xml' })
  setGpxBlob(blob)
  return { gpxPath: null, gpxBlob: blob }
}

function getUploadBlob() {
  if (tracking.gpxBlob) return tracking.gpxBlob
  if (tracking.routePoints.length > 0) {
    return new Blob([toGpx()], { type: 'application/gpx+xml' })
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
  resetMetrics()
  setGpxPath(null)
  setGpxBlob(null)
}

onMounted(() => {
  resetTrackingState()
})

onBeforeUnmount(() => {
  if (webWatchId !== null) {
    navigator.geolocation.clearWatch(webWatchId)
    webWatchId = null
  }
  if (tracking.isTracking && !tracking.gpxBlob) {
    stopWebTracking()
  }
})
</script>
