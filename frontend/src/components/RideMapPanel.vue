<template>
  <section class="panel">
    <div class="map-header">
      <div>
        <h2>Route Maps</h2>
        <p class="map-subtitle">
          GPS segments are colored by gradient, weather conditions, or combined risk.
        </p>
      </div>
      <button class="btn btn-primary" :disabled="loading" @click="loadRides">
        {{ loading ? 'Updating...' : 'Update map' }}
      </button>
    </div>

    <div class="map-toolbar">
      <label class="control">
        <span>Map</span>
        <select v-model="mapStyle" class="form-input">
          <option v-for="(cfg, key) in MAP_STYLES" :key="key" :value="key">
            {{ cfg.label }}
          </option>
        </select>
      </label>

      <label class="control">
        <span>Route</span>
        <select v-model="selectedRideId" class="form-input">
          <option :value="null">All routes</option>
          <option v-for="ride in ridesWithGps" :key="ride.id" :value="ride.id">
            {{ ride.date }} · {{ formatDistance(ride.distanceM) }}
          </option>
        </select>
      </label>

      <label class="control">
        <span>Coloring</span>
        <select v-model="colorMode" class="form-input">
          <option value="combined">Grade + weather</option>
          <option value="slope">Grade only</option>
          <option value="weather">Weather only</option>
          <option value="speed">Speed</option>
        </select>
      </label>

      <label class="checkbox-control">
        <input v-model="weatherEnabled" type="checkbox" />
        <span>Include weather</span>
      </label>
    </div>

<div v-if="loading && !enrichedRides.length" class="loading-text">
       <span class="spinner"></span> Loading routes...
     </div>

     <div id="route-map" ref="mapContainer" class="route-map">
       <div v-if="!ridesWithGps.length" class="demo-map-overlay">
         <div class="demo-map-content">
           <span class="demo-icon">🗺️</span>
           <p>Milan-Monza demo route</p>
           <p class="demo-hint">Import GPX/FIT or add a ride with GPS points to view your routes</p>
         </div>
       </div>
     </div>

<div v-if="ridesWithGps.length" class="map-kpis">
       <div class="kpi">
         <strong>{{ visibleRides.length }}</strong>
         <span>{{ visibleRides.length === 1 ? 'route' : 'routes' }}</span>
       </div>
       <div class="kpi">
         <strong>{{ totalGpsPoints }}</strong>
         <span>GPS points</span>
       </div>
       <div class="kpi">
         <strong>{{ averageRisk }}</strong>
         <span>average risk</span>
       </div>
       <div class="kpi">
         <strong>{{ worstRide }}</strong>
         <span>worst segment</span>
       </div>
     </div>

<div class="legend-grid">
       <div class="legend-card">
         <h4>Combined Risk</h4>
         <div v-for="level in riskLevels" :key="level.label" class="legend-row">
           <span class="legend-swatch" :style="{ background: level.color }"></span>
           <span>{{ level.label }} · {{ level.range }}</span>
         </div>
       </div>

       <div class="legend-card">
         <h4>Gradients</h4>
         <div v-for="item in gradeLegend" :key="item.label" class="legend-row">
           <span class="legend-swatch" :style="{ background: item.color }"></span>
           <span>{{ item.label }}</span>
         </div>
       </div>

       <div v-if="weatherEnabled" class="legend-card">
         <h4>Weather</h4>
         <div v-for="item in weatherLegend" :key="item.label" class="legend-row">
           <span class="legend-swatch" :style="{ background: item.color }"></span>
           <span>{{ item.label }}</span>
         </div>
         <p v-if="weatherUnavailableCount" class="legend-note">
           {{ weatherUnavailableCount }} {{ weatherUnavailableCount === 1 ? 'route' : 'routes' }} without weather: weather risk set to 50/100.
         </p>
       </div>

       <div v-if="colorMode === 'speed'" class="legend-card">
         <h4>Speed</h4>
         <div v-for="item in speedLegend" :key="item.label" class="legend-row">
           <span class="legend-swatch" :style="{ background: item.color }"></span>
           <span>{{ item.label }}</span>
         </div>
       </div>
     </div>
   </section>
   </template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import { apiGet } from '../utils/api'
import {
   buildRidePolylines,
   escapeHtml,
   formatDistance,
   gradeRiskPercent,
   riskColor,
   speedRiskPercent,
   weatherRiskPercent,
 } from '../utils/routeMap'

  const mapContainer = ref(null)
  const loading = ref(false)
  const enrichedRides = ref([])
  const selectedRideId = ref(null)
  const colorMode = ref('combined')
  const weatherEnabled = ref(true)
  const mapStyle = ref(localStorage.getItem('mapStyle') || 'standard')

  const MAP_STYLES = {
    standard: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
      label: 'Standard (OSM)',
    },
    cyclosm: {
      url: 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | &copy; <a href="https://cyclosm.org">CyclOSM</a>',
      maxZoom: 20,
      label: 'CyclOSM (Cycling)',
    },
    opencyclemap: {
      url: 'https://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | &copy; <a href="http://www.opencyclemap.org">OpenCycleMap</a>',
      maxZoom: 19,
      label: 'OpenCycleMap',
    },
    topo: {
      url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
      maxZoom: 17,
      label: 'Topographic',
    },
  }

 // Demo route: Milan to Monza (approximate coordinates along SS36)
 const demoRoutePoints = [
   { lat: 45.4642, lon: 9.1900, altitude: 120 },
   { lat: 45.4800, lon: 9.2200, altitude: 135 },
   { lat: 45.4900, lon: 9.2500, altitude: 155 },
   { lat: 45.5000, lon: 9.2800, altitude: 175 },
   { lat: 45.5600, lon: 9.2700, altitude: 190 },
   { lat: 45.5800, lon: 9.2400, altitude: 185 },
   { lat: 45.5900, lon: 9.2000, altitude: 190 },
   { lat: 45.6000, lon: 9.1800, altitude: 195 },
   { lat: 45.6100, lon: 9.1600, altitude: 190 },
   { lat: 45.6200, lon: 9.1400, altitude: 200 },
   { lat: 45.6300, lon: 9.1200, altitude: 210 },
 ]

  let map = null
  let layerGroup = null
  let tileLayer = null

  function createTileLayer(styleKey) {
    const cfg = MAP_STYLES[styleKey] || MAP_STYLES.standard
    return L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom: cfg.maxZoom,
    })
  }

  function switchTileLayer(styleKey) {
    if (!map) return
    if (tileLayer) {
      map.removeLayer(tileLayer)
    }
    tileLayer = createTileLayer(styleKey)
    tileLayer.addTo(map)
  }

  function renderMap() {
    if (!mapContainer.value) return

    if (!map) {
      map = L.map(mapContainer.value, { preferCanvas: true }).setView([45.4642, 9.19], 11)
      tileLayer = createTileLayer(mapStyle.value)
      tileLayer.addTo(map)
      layerGroup = L.layerGroup().addTo(map)
    } else {
      switchTileLayer(mapStyle.value)
    }

    layerGroup.clearLayers()
    const bounds = L.latLngBounds()

    const ridesToRender = visibleRides.value.length > 0 ? visibleRides.value : [demoRide.value]

    ridesToRender.forEach(ride => {
      const rideLayer = L.layerGroup()
      const points = ride.gps_points || []

      let segments = ride.segments
      if (ride.isDemo) {
        segments = buildDemoSegments(points)
      }

      buildRidePolylines({ ...ride, segments }).forEach(polylineData => {
        const polyline = L.polyline(polylineData.points, {
          color: polylineData.color,
          weight: 5,
          opacity: 0.8,
          dashArray: ride.isDemo ? '10,5' : null,
          lineCap: 'round',
          lineJoin: 'round',
        })
        polyline.addTo(rideLayer)
        polylineData.points.forEach(point => {
          bounds.extend(point)
        })
      })

      if (ride.center) {
        const centerMarker = L.circleMarker(ride.center, {
          radius: 6,
          color: ride.isDemo ? '#3498db' : riskColor(ride.overallRisk),
          fillColor: ride.isDemo ? '#3498db' : riskColor(ride.overallRisk),
          fillOpacity: 0.9,
          weight: 2,
        })
        centerMarker.bindPopup(ride.isDemo ? 'Milan-Monza demo route' : ridePopup(ride))
        centerMarker.addTo(rideLayer)
      }

      rideLayer.addTo(layerGroup)
    })

    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.1))
    }
    map.invalidateSize()
  }

  const ridesWithGps = computed(() => enrichedRides.value.filter(ride => ride.gps_points.length > 1))

  const visibleRides = computed(() => {
    if (selectedRideId.value) {
      const selected = ridesWithGps.value.find(ride => ride.id === selectedRideId.value)
      if (selected) return [selected]
    }
    return ridesWithGps.value
  })

  const totalGpsPoints = computed(() => visibleRides.value.reduce((sum, ride) => sum + ride.gps_points.length, 0))

const averageRisk = computed(() => {
  const risks = visibleRides.value.flatMap(ride => ride.segments.map(segment => segment.risk))
  if (!risks.length) return '—'
  return `${Math.round(risks.reduce((sum, value) => sum + value, 0) / risks.length)}/100`
})

const worstRide = computed(() => {
  const risks = visibleRides.value.flatMap(ride => ride.segments.map(segment => segment.risk))
  if (!risks.length) return '—'
  return `${Math.max(...risks)}/100`
})

const weatherUnavailableCount = computed(() => enrichedRides.value.filter(ride => ride.weatherUnavailable).length)

const demoRide = computed(() => ({
  id: 'demo',
  isDemo: true,
  date: '2026-06-19',
  gps_points: demoRoutePoints,
  segments: [],
  center: getCenter(demoRoutePoints),
  distanceM: demoRoutePoints.length * 5000,
  overallRisk: 50,
}))

watch(mapStyle, () => {
  localStorage.setItem('mapStyle', mapStyle.value)
  renderMap()
})

watch(colorMode, () => {
  enrichedRides.value = enrichedRides.value.map(ride => applyRideRisk(ride))
  renderMap()
})

watch(weatherEnabled, () => {
  loadRides()
})

watch(selectedRideId, () => {
  renderMap()
})

async function loadRides() {
  loading.value = true
  try {
    const data = await apiGet('/api/v1/rides', { page: 1, page_size: 100, sort: 'date' })
    const rides = data.rides || []
    const enriched = rides.map(enrichRide)

    await Promise.allSettled(
      enriched
        .filter(ride => weatherEnabled.value && ride.gps_points.length > 1)
        .map(ride => loadWeather(ride))
    )

    enriched.forEach(applyRideRisk)
    enrichedRides.value = enriched
    if (selectedRideId.value && !enriched.some(ride => ride.id === selectedRideId.value)) {
      selectedRideId.value = null
    }
    await nextTick()
    renderMap()
  } catch (error) {
    console.error('ride map load failed', error)
    enrichedRides.value = []
  } finally {
    loading.value = false
  }
}

async function loadWeather(ride) {
  try {
    ride.weather = await apiGet('/api/v1/weather', {
      lat: Number(ride.center.lat.toFixed(5)),
      lon: Number(ride.center.lon.toFixed(5)),
      date: ride.date,
    })
    ride.weatherScore = Number.isFinite(ride.weather?.score) ? ride.weather.score : 5
    ride.weatherUnavailable = false
  } catch (error) {
    ride.weather = null
    ride.weatherScore = 5
    ride.weatherUnavailable = true
    ride.weatherError = error.message
  }
}

function enrichRide(ride) {
  const gps_points = downsamplePoints(normalizePoints(ride.gps_points))
  const center = getCenter(gps_points)
  const segments = buildSegments(gps_points)
  const distanceM = segments.reduce((sum, segment) => sum + segment.distance_m, 0)
  const elevationGain = segments.reduce((sum, segment) => sum + Math.max(0, segment.elevation_delta_m), 0)

  return {
    ...ride,
    gps_points,
    center,
    segments,
    distanceM,
    elevationGain,
    weather: null,
    weatherScore: 5,
    weatherUnavailable: false,
    weatherError: '',
    overallRisk: 0,
    maxRisk: 0,
  }
}

function normalizePoints(points = []) {
  return points
    .map(point => ({
      lat: Number(point.lat),
      lon: Number(point.lon),
      altitude: point.altitude ?? point.elevation ?? point.elevation_m ?? null,
      timestamp: point.timestamp ?? null,
      speed: point.speed ?? null,
    }))
    .filter(point => Number.isFinite(point.lat) && Number.isFinite(point.lon))
}

function downsamplePoints(points, stride = 3) {
  if (points.length <= 200) return points
  return points.filter((_, index) => index % stride === 0 || index === points.length - 1)
}

function buildSegments(points) {
  const segments = []
  if (points.length < 2) return segments

  let previous = points[0]
  for (let index = 1; index < points.length; index += 1) {
    const current = points[index]
    const distance_m = haversineDistanceM(previous.lat, previous.lon, current.lat, current.lon)
    const altitudeA = Number(previous.altitude)
    const altitudeB = Number(current.altitude)
    const elevation_delta_m = Number.isFinite(altitudeA) && Number.isFinite(altitudeB) ? altitudeB - altitudeA : 0
    const grade = distance_m > 0 ? (elevation_delta_m / distance_m) * 100 : 0

    segments.push({
      start: [previous.lat, previous.lon],
      end: [current.lat, current.lon],
      distance_m,
      elevation_delta_m,
      grade,
      risk: 0,
      color: '#4ecca3',
    })
    previous = current
  }
  return segments
}

function buildDemoSegments(points) {
  const segments = buildSegments(points)
  return segments.map(segment => {
    const gradeRisk = gradeRiskPercent(segment.grade)
    const risk = Math.round(gradeRisk * 0.7) // Demo risk
    return {
      ...segment,
      risk,
      color: riskColor(risk),
    }
  })
}

function applyRideRisk(ride) {
  const weatherScore = Number.isFinite(ride.weatherScore) ? ride.weatherScore : 5
  ride.segments = ride.segments.map(segment => {
    const gradeRisk = gradeRiskPercent(segment.grade)
    const weatherRisk = weatherRiskPercent(weatherScore)
    const speedRisk = speedRiskPercent(segment.speed)
    let risk = 0

    if (colorMode.value === 'slope') {
      risk = gradeRisk
    } else if (colorMode.value === 'weather') {
      risk = weatherEnabled.value ? weatherRisk : 0
    } else if (colorMode.value === 'speed') {
      risk = speedRisk
    } else {
      risk = Math.round((gradeRisk + weatherRisk) / 2)
    }

    return {
      ...segment,
      risk,
      color: riskColor(risk),
      gradeRisk,
      weatherRisk,
      speedRisk,
    }
  })

  const risks = ride.segments.map(segment => segment.risk)
  ride.overallRisk = risks.length ? Math.round(risks.reduce((sum, value) => sum + value, 0) / risks.length) : 0
  ride.maxRisk = risks.length ? Math.max(...risks) : 0
  return ride
}

function segmentPopup(ride, segment) {
   const gradeText = segment.grade >= 0 ? `+${segment.grade.toFixed(1)}%` : `${segment.grade.toFixed(1)}%`
   const weatherText = weatherEnabled.value
     ? `Weather: ${escapeHtml(segment.weatherRisk)}/100 · score ${escapeHtml(ride.weatherScore)}/10`
     : 'Weather: disabled'
   return `
     <strong>${escapeHtml(ride.date)}</strong><br>
     Grade: ${escapeHtml(gradeText)}<br>
     Grade risk: ${escapeHtml(segment.gradeRisk)}/100<br>
     ${weatherText}<br>
     Segment risk: ${escapeHtml(segment.risk)}/100
   `
 }

function ridePopup(ride) {
   const weatherLabel = ride.weatherUnavailable ? 'unavailable' : `${ride.weatherScore}/10`
   const weatherDescription = ride.weather?.description || ''
   const weatherText = weatherEnabled.value
     ? `Weather: ${escapeHtml(weatherLabel)} · ${escapeHtml(weatherDescription)}`
     : 'Weather: disabled'
   return `
     <strong>Ride ${escapeHtml(ride.date)}</strong><br>
     Distance: ${escapeHtml(formatDistance(ride.distanceM))}<br>
     Elevation gain: ${escapeHtml(`${Math.round(ride.elevationGain)} m`)}<br>
     Average risk: ${escapeHtml(ride.overallRisk)}/100<br>
     ${weatherText}
   `
 }

function getCenter(points) {
  if (!points.length) return null
  const lat = points.reduce((sum, point) => sum + point.lat, 0) / points.length
  const lon = points.reduce((sum, point) => sum + point.lon, 0) / points.length
  return { lat, lon }
}

function haversineDistanceM(lat1, lon1, lat2, lon2) {
  const radius = 6371000
  const toRad = value => value * Math.PI / 180
  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) ** 2
  return 2 * radius * Math.asin(Math.sqrt(a))
}

onMounted(() => {
  loadRides()
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
    layerGroup = null
    tileLayer = null
  }
})
</script>

<style scoped>
.map-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.map-subtitle {
  margin: 6px 0 0;
  color: var(--text-secondary);
  max-width: 760px;
}

.map-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(180px, 220px) auto;
  gap: 12px;
  align-items: end;
  margin-bottom: 14px;
}

.control {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.checkbox-control {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
}

.checkbox-control input {
  width: 16px;
  height: 16px;
}

.map-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.kpi {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
}

.kpi strong {
  display: block;
  color: var(--accent);
  font-size: 1.35rem;
}

.kpi span {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.route-map {
  height: 560px;
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--bg-secondary);
  position: relative;
}

.demo-map-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1e21 0%, #252a2f 100%);
  z-index: 10;
}

.demo-map-content {
  text-align: center;
  color: var(--text-secondary);
}

.demo-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 12px;
}

.demo-hint {
  font-size: 0.9rem;
  margin-top: 8px;
  color: var(--text-secondary);
}

.legend-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.legend-card {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
}

.legend-card h4 {
  margin: 0 0 10px;
  font-size: 0.95rem;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 7px 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.legend-swatch {
  width: 18px;
  height: 10px;
  border-radius: 999px;
  flex: 0 0 18px;
}

.legend-note {
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

@media (max-width: 900px) {
  .map-header,
  .map-toolbar {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .map-kpis,
  .legend-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .route-map {
    height: 460px;
  }
}

@media (max-width: 560px) {
  .map-kpis,
  .legend-grid {
    grid-template-columns: 1fr;
  }

  .route-map {
    height: 380px;
  }
}
</style>
