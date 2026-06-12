<template>
  <section class="panel">
    <div class="map-header">
      <div>
        <h2>Mappe Percorsi</h2>
        <p class="map-subtitle">
          I segmenti GPS vengono colorati in base alla pendenza, alle condizioni meteo della zona o alla combinazione delle due informazioni.
        </p>
      </div>
      <button class="btn btn-primary" :disabled="loading" @click="loadRides">
        {{ loading ? 'Aggiornamento...' : 'Aggiorna mappa' }}
      </button>
    </div>

    <div class="map-toolbar">
      <label class="control">
        <span>Percorso</span>
        <select v-model="selectedRideId" class="form-input">
          <option :value="null">Tutti i percorsi</option>
          <option v-for="ride in ridesWithGps" :key="ride.id" :value="ride.id">
            {{ ride.date }} · {{ formatDistance(ride.distanceM) }}
          </option>
        </select>
      </label>

      <label class="control">
        <span>Colorazione</span>
        <select v-model="colorMode" class="form-input">
          <option value="combined">Pendenza + meteo</option>
          <option value="slope">Solo pendenza</option>
          <option value="weather">Solo meteo</option>
        </select>
      </label>

      <label class="checkbox-control">
        <input v-model="weatherEnabled" type="checkbox" />
        <span>Includi meteo</span>
      </label>
    </div>

    <div v-if="loading && !enrichedRides.length" class="loading-text">
      <span class="spinner"></span> Caricamento percorsi...
    </div>

    <div v-else-if="!ridesWithGps.length" class="empty-state">
      <div class="empty-icon">Map</div>
      <div class="empty-title">Nessun percorso GPS disponibile</div>
      <div class="empty-desc">Importa GPX/FIT o aggiungi una ride con punti GPS per visualizzare la mappa colorata.</div>
    </div>

    <template v-else>
      <div class="map-kpis">
        <div class="kpi">
          <strong>{{ visibleRides.length }}</strong>
          <span>{{ visibleRides.length === 1 ? 'percorso' : 'percorsi' }}</span>
        </div>
        <div class="kpi">
          <strong>{{ totalGpsPoints }}</strong>
          <span>punti GPS</span>
        </div>
        <div class="kpi">
          <strong>{{ averageRisk }}</strong>
          <span>rischio medio</span>
        </div>
        <div class="kpi">
          <strong>{{ worstRide }}</strong>
          <span>tratto più critico</span>
        </div>
      </div>

      <div id="route-map" ref="mapContainer" class="route-map"></div>

      <div class="legend-grid">
        <div class="legend-card">
          <h4>Rischio combinato</h4>
          <div v-for="level in riskLevels" :key="level.label" class="legend-row">
            <span class="legend-swatch" :style="{ background: level.color }"></span>
            <span>{{ level.label }} · {{ level.range }}</span>
          </div>
        </div>

        <div class="legend-card">
          <h4>Pendenze</h4>
          <div v-for="item in gradeLegend" :key="item.label" class="legend-row">
            <span class="legend-swatch" :style="{ background: item.color }"></span>
            <span>{{ item.label }}</span>
          </div>
        </div>

        <div v-if="weatherEnabled" class="legend-card">
          <h4>Meteo</h4>
          <div v-for="item in weatherLegend" :key="item.label" class="legend-row">
            <span class="legend-swatch" :style="{ background: item.color }"></span>
            <span>{{ item.label }}</span>
          </div>
          <p v-if="weatherUnavailableCount" class="legend-note">
            {{ weatherUnavailableCount }} {{ weatherUnavailableCount === 1 ? 'percorso' : 'percorsi' }} senza meteo: rischio meteo impostato a 50/100.
          </p>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import { apiGet } from '../utils/api.js'

const mapContainer = ref(null)
const loading = ref(false)
const enrichedRides = ref([])
const selectedRideId = ref(null)
const colorMode = ref('combined')
const weatherEnabled = ref(true)

let map = null
let layerGroup = null

const riskLevels = [
  { label: 'Facile', range: '0-24', color: '#27ae60' },
  { label: 'Moderato', range: '25-49', color: '#f1c40f' },
  { label: 'Difficile', range: '50-74', color: '#e67e22' },
  { label: 'Critico', range: '75-100', color: '#e74c3c' },
]

const gradeLegend = [
  { label: 'Piano o falsopiano: < 3%', color: '#27ae60' },
  { label: 'Media: 3-6%', color: '#f1c40f' },
  { label: 'Dura: 6-10%', color: '#e67e22' },
  { label: 'Molto dura: > 10%', color: '#e74c3c' },
]

const weatherLegend = [
  { label: 'Buono: score ≥ 8', color: '#27ae60' },
  { label: 'Accettabile: score 5-7', color: '#f1c40f' },
  { label: 'Critico: score < 5', color: '#e74c3c' },
]

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

function applyRideRisk(ride) {
  const weatherScore = Number.isFinite(ride.weatherScore) ? ride.weatherScore : 5
  ride.segments = ride.segments.map(segment => {
    const gradeRisk = gradeRiskPercent(segment.grade)
    const weatherRisk = weatherRiskPercent(weatherScore)
    let risk = 0

    if (colorMode.value === 'slope') {
      risk = gradeRisk
    } else if (colorMode.value === 'weather') {
      risk = weatherEnabled.value ? weatherRisk : 0
    } else {
      risk = Math.round((gradeRisk + weatherRisk) / 2)
    }

    return {
      ...segment,
      risk,
      color: riskColor(risk),
      gradeRisk,
      weatherRisk,
    }
  })

  const risks = ride.segments.map(segment => segment.risk)
  ride.overallRisk = risks.length ? Math.round(risks.reduce((sum, value) => sum + value, 0) / risks.length) : 0
  ride.maxRisk = risks.length ? Math.max(...risks) : 0
  return ride
}

function renderMap() {
  if (!mapContainer.value) return

  if (!map) {
    map = L.map(mapContainer.value, { preferCanvas: true }).setView([45.4642, 9.19], 13)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map)
    layerGroup = L.layerGroup().addTo(map)
  }

  layerGroup.clearLayers()
  const bounds = L.latLngBounds()

  visibleRides.value.forEach(ride => {
    const rideLayer = L.layerGroup()

    ride.segments.forEach(segment => {
      const polyline = L.polyline([segment.start, segment.end], {
        color: segment.color,
        weight: selectedRideId.value ? 6 : 4,
        opacity: selectedRideId.value ? 0.95 : 0.68,
        lineCap: 'round',
        lineJoin: 'round',
      })
      polyline.addTo(rideLayer)
      bounds.extend(segment.start)
      bounds.extend(segment.end)
    })

    if (ride.center) {
      const centerMarker = L.circleMarker(ride.center, {
        radius: 6,
        color: riskColor(ride.overallRisk),
        fillColor: riskColor(ride.overallRisk),
        fillOpacity: 0.9,
        weight: 2,
      })
      centerMarker.bindPopup(ridePopup(ride))
      centerMarker.addTo(rideLayer)
    }

    rideLayer.addTo(layerGroup)
  })

  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.03))
  }
  map.invalidateSize()
}

function segmentPopup(ride, segment) {
  const gradeText = segment.grade >= 0 ? `+${segment.grade.toFixed(1)}%` : `${segment.grade.toFixed(1)}%`
  const weatherText = weatherEnabled.value
    ? `Meteo: ${escapeHtml(segment.weatherRisk)}/100 · score ${escapeHtml(ride.weatherScore)}/10`
    : 'Meteo: disattivato'
  return `
    <strong>${escapeHtml(ride.date)}</strong><br>
    Pendenza: ${escapeHtml(gradeText)}<br>
    Rischio pendenza: ${escapeHtml(segment.gradeRisk)}/100<br>
    ${weatherText}<br>
    Rischio segmento: ${escapeHtml(segment.risk)}/100
  `
}

function ridePopup(ride) {
  const weatherLabel = ride.weatherUnavailable ? 'non disponibile' : `${ride.weatherScore}/10`
  const weatherDescription = ride.weather?.description || ''
  const weatherText = weatherEnabled.value
    ? `Meteo: ${escapeHtml(weatherLabel)} · ${escapeHtml(weatherDescription)}`
    : 'Meteo: disattivato'
  return `
    <strong>Ride ${escapeHtml(ride.date)}</strong><br>
    Distanza: ${escapeHtml(formatDistance(ride.distanceM))}<br>
    Dislivello positivo: ${escapeHtml(`${Math.round(ride.elevationGain)} m`)}<br>
    Rischio medio: ${escapeHtml(ride.overallRisk)}/100<br>
    ${weatherText}
  `
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]))
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

function gradeRiskPercent(grade) {
  const absGrade = Math.abs(grade)
  if (absGrade < 3) return 15
  if (absGrade < 6) return 35
  if (absGrade < 10) return 65
  return 90
}

function weatherRiskPercent(score) {
  if (!Number.isFinite(score)) return 50
  if (score >= 8) return 10
  if (score >= 5) return 45
  return 85
}

function riskColor(risk) {
  if (risk < 25) return '#27ae60'
  if (risk < 50) return '#f1c40f'
  if (risk < 75) return '#e67e22'
  return '#e74c3c'
}

function formatDistance(meters = 0) {
  return `${(meters / 1000).toFixed(2)} km`
}

onMounted(() => {
  loadRides()
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
    layerGroup = null
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
