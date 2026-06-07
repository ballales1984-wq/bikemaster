<template>
  <section v-if="ride">
    <div class="panel">
      <h2>🚴 Dettaglio Ride {{ ride.date }}</h2>
      <div class="ride-stats-detail">
        <span>📏 {{ ride.distance_km }} km</span>
        <span>⏱️ {{ ride.duration_minutes }} min</span>
        <span>⚡ {{ ride.avg_speed_kmh }} km/h</span>
        <span>🔥 {{ ride.calories }} kcal</span>
        <span>😰 {{ ride.fatigue_score }}/10</span>
      </div>
      <img v-if="mapUrl" :src="mapUrl" alt="Route map" class="route-map" />
      <div class="chart-row">
        <img v-if="speedChart" :src="speedChart" alt="Speed chart" />
        <img v-if="elevationChart" :src="elevationChart" alt="Elevation chart" />
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { apiGet } from "../utils/api.js"

const props = defineProps({ rideId: Number })
const ride = ref(null)
const mapUrl = ref("")
const speedChart = ref("")
const elevationChart = ref("")

async function load() {
  const data = await apiGet(`/api/v1/rides/${props.rideId}`)
  ride.value = data
  mapUrl.value = `/static/ride_${props.rideId}_map.html`
  speedChart.value = `/api/v1/charts/speed/${props.rideId}`
  elevationChart.value = `/api/v1/charts/elevation/${props.rideId}`
}

onMounted(() => {
  load()
})
</script>
