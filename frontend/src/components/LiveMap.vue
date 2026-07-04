<template>
  <div class="live-map-wrapper">
    <div ref="mapEl" class="live-map"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import { useTrackingStore } from '../stores/trackingStore'

const mapEl = ref<HTMLElement | null>(null)
const map = ref<L.Map | null>(null)
const polyline = ref<L.Polyline | null>(null)

const tracking = useTrackingStore()
const points = ref<L.LatLng[]>([])

watch(
  () => tracking.routePoints.length,
  () => {
    const pts = tracking.routePoints
    const point = pts[pts.length - 1]
    if (point && map.value) {
      addPoint(point.lat, point.lon)
    }
  }
)

onMounted(() => {
  if (!mapEl.value) return
  map.value = L.map(mapEl.value, { preferCanvas: true }).setView([45.4642, 9.19], 16)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap',
    maxZoom: 19,
  }).addTo(map.value)
})

onBeforeUnmount(() => {
  if (map.value) {
    map.value.remove()
    map.value = null
  }
})

defineExpose({
  addPoint(lat: number, lon: number) {
    points.value.push(L.latLng(lat, lon))
    if (!polyline.value && map.value) {
      polyline.value = L.polyline(points.value, {
        color: '#4ecca3',
        weight: 5,
        opacity: 0.9,
      }).addTo(map.value)
    }
    map.value?.setView([lat, lon], 16)
  },
  clear() {
    points.value = []
    polyline.value = null
  },
})
</script>

<style scoped>
.live-map-wrapper {
  width: 100%;
  height: 100%;
}
.live-map {
  height: 100%;
  width: 100%;
  border-radius: var(--radius-sm);
}
</style>