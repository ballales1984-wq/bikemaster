<template>
  <section class="panel">
    <div class="tracking-header">
      <h2>Tracciamento GPS</h2>
      <div v-if="isTracking" class="tracking-status">
        <span class="status-badge" :class="{ paused: isPaused }">
          {{ isPaused ? 'In pausa' : 'In corso' }}
        </span>
      </div>
    </div>

    <div v-if="!isTracking && !gpxPath" class="empty-state">
      <div class="empty-icon">📍</div>
      <div class="empty-title">Pronto per tracciare la tua uscita</div>
      <div class="empty-desc">
        Premi il pulsante qui sotto per iniziare a registrare il tuo percorso in tempo reale.
      </div>
      <button class="btn btn-primary btn-large" @click="startTracking">
        Avvia Tracking
      </button>
    </div>

    <div v-else class="tracking-content">
      <LiveMap ref="liveMapRef" />
      <RideMetricsPanel />
      <ControlsBar :is-paused="isPaused" @pause="pauseTracking" @resume="resumeTracking" @stop="stopTracking" />

      <div v-if="gpxPath" class="tracking-complete">
        <p>Tracciamento completato! File salvato.</p>
        <button class="btn btn-primary" @click="uploadRide">
          Carica su BikeMaster
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useTrackingStore } from '../stores/trackingStore'
import LiveMap from '../components/LiveMap.vue'
import RideMetricsPanel from '../components/RideMetricsPanel.vue'
import ControlsBar from '../components/ControlsBar.vue'
import { apiUpload } from '../utils/api'

const liveMapRef = ref<InstanceType<typeof LiveMap> | null>(null)

const tracking = useTrackingStore()
const {
  isTracking,
  isPaused,
  stop,
  setGpxPath,
} = tracking

async function startTracking() {
  const hasPermission = await checkPermissions()
  if (!hasPermission) {
    alert('Permessi GPS richiesti per il tracciamento')
    return
  }
  if (window.BikeTracking?.startTracking) {
    await window.BikeTracking.startTracking()
  }
  start()
}

async function checkPermissions(): Promise<boolean> {
  if (!window.BikeTracking?.checkPermissions) return true
  return window.BikeTracking.checkPermissions().then((result) => result.granted)
}

async function pauseTracking() {
  if (window.BikeTracking?.pauseTracking) {
    await window.BikeTracking.pauseTracking()
  }
  pause()
}

async function resumeTracking() {
  if (window.BikeTracking?.resumeTracking) {
    await window.BikeTracking.resumeTracking()
  }
  resume()
}

async function stopTracking() {
  if (window.BikeTracking?.stopTracking) {
    const result = await window.BikeTracking.stopTracking()
    setGpxPath(result?.gpxPath || null)
  } else {
    setGpxPath(null)
  }
  stop()
}

async function uploadRide() {
  const gpxPath = tracking.gpxPath
  if (!gpxPath) return
  try {
    await apiUpload('/api/v1/import/gpx', gpxPath)
    alert('Uscita caricata con successo!')
    tracking.resetMetrics()
  } catch (error) {
    console.error('Upload failed:', error)
    alert('Errore durante il caricamento')
  }
}

onMounted(() => {
  tracking.start()
})

onBeforeUnmount(() => {
  tracking.resetMetrics()
})
</script>