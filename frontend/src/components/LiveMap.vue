<template>
  <div class="live-map-wrapper">
    <div ref="mapEl" class="live-map"></div>
  </div>
</template>

<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import { ref, onMounted, onBeforeUnmount } from 'vue'
import L from 'leaflet'

const mapEl = ref<HTMLElement | null>(null)
const map = ref<L.Map | null>(null)
const polyline = ref<L.Polyline | null>(null)
const currentMarker = ref<L.CircleMarker | null>(null)

const points = ref<Array<[number, number]>>([])

function addPoint(lat: number, lon: number) {
  points.value.push([lat, lon])
  if (!map.value) return

  if (!polyline.value) {
    polyline.value = L.polyline(points.value, {
      color: '#4ecca3',
      weight: 5,
      opacity: 0.9,
    }).addTo(map.value)
  } else {
    polyline.value.setLatLngs(points.value)
  }

  if (!currentMarker.value) {
    currentMarker.value = L.circleMarker([lat, lon], {
      radius: 8,
      color: '#4ecca3',
      fillColor: '#4ecca3',
      fillOpacity: 1,
      weight: 2,
    }).addTo(map.value)
  } else {
    currentMarker.value.setLatLng([lat, lon])
  }

  map.value.setView([lat, lon], 16)
}

onMounted(() => {
  if (!mapEl.value) return
  map.value = L.map(mapEl.value, { preferCanvas: true }).setView([45.4642, 9.19], 16)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map.value)

  if (points.value.length > 0) {
    const last = points.value[points.value.length - 1]
    polyline.value = L.polyline(points.value, {
      color: '#4ecca3',
      weight: 5,
      opacity: 0.9,
    }).addTo(map.value)
    currentMarker.value = L.circleMarker(last, {
      radius: 8,
      color: '#4ecca3',
      fillColor: '#4ecca3',
      fillOpacity: 1,
      weight: 2,
    }).addTo(map.value)
    map.value.setView(last, 16)
  }
})

onBeforeUnmount(() => {
  if (map.value) {
    map.value.remove()
    map.value = null
  }
})

defineExpose({
  addPoint,
  clear() {
    points.value = []
    polyline.value = null
    currentMarker.value = null
  },
})
</script>

<style scoped>
.live-map-wrapper {
  width: 100%;
  height: 400px;
  min-height: 400px;
}
.live-map {
  height: 100%;
  width: 100%;
  border-radius: var(--radius-sm);
}
</style>
