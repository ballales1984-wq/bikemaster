<template>
  <section>
    <div class="panel">
      <h2>📋 Le tue Ride</h2>
      <p v-if="loading" class="loading-text">Caricamento...</p>
      <div v-else class="rides-list">
        <div class="ride-item" v-for="ride in rides" :key="ride.id">
          <div>
            <div class="ride-date">{{ ride.date }}</div>
            <div class="ride-stats">{{ ride.distance_km }}km • {{ ride.duration_minutes }}min • {{ ride.avg_speed_kmh }} km/h</div>
          </div>
          <button class="btn btn-danger btn-sm" @click="handleDelete(ride.id)">Elimina</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGet, apiDelete } from '../utils/api.js'

const loading = ref(true)
const rides = ref([])

async function load() {
  loading.value = true
  try {
    const data = await apiGet('/api/v1/rides')
    rides.value = data.rides || []
  } finally {
    loading.value = false
  }
}

async function handleDelete(id) {
  if (!confirm('Eliminare questa ride?')) return
  await apiDelete(`/api/v1/rides/${id}`)
  rides.value = rides.value.filter(r => r.id !== id)
}

onMounted(() => {
  load()
})
</script>
