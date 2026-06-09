<template>
  <section>
    <div class="panel">
      <h2>📋 Le tue Ride</h2>
      <div class="add-ride-form">
        <h3>➕ Aggiungi Nuova Ride</h3>
        <form @submit.prevent="handleAdd" class="ride-form">
          <div class="form-row">
            <input v-model="form.date" type="date" required class="form-input" />
            <input v-model="form.distance_km" type="number" step="0.01" placeholder="Distanza (km)" required class="form-input" />
          </div>
          <div class="form-row">
            <input v-model="form.duration_minutes" type="number" placeholder="Durata (min)" required class="form-input" />
            <input v-model="form.avg_speed_kmh" type="number" step="0.01" placeholder="Velocità media (km/h)" class="form-input" />
          </div>
          <div class="form-row">
            <input v-model="form.elevation_gain_m" type="number" placeholder="Elevazione (m)" class="form-input" />
            <input v-model="form.calories" type="number" placeholder="Calorie" class="form-input" />
          </div>
          <button type="submit" class="btn btn-primary" :disabled="adding">{{ adding ? 'Aggiungendo...' : 'Aggiungi Ride' }}</button>
        </form>
        <p v-if="addError" class="error-text">{{ addError }}</p>
      </div>
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
import { apiGet, apiDelete, apiPost } from '../utils/api.js'

const loading = ref(true)
const adding = ref(false)
const addError = ref('')
const rides = ref([])
const form = ref({ date: '', distance_km: '', duration_minutes: '', avg_speed_kmh: '', elevation_gain_m: '', calories: '' })

async function load() {
  loading.value = true
  try {
    const data = await apiGet('/api/v1/rides')
    rides.value = data.rides || []
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  adding.value = true
  addError.value = ''
  try {
    const rideData = {
      date: form.value.date,
      distance_km: Number(form.value.distance_km),
      duration_minutes: Number(form.value.duration_minutes),
      avg_speed_kmh: form.value.avg_speed_kmh ? Number(form.value.avg_speed_kmh) : undefined,
      elevation_gain_m: form.value.elevation_gain_m ? Number(form.value.elevation_gain_m) : undefined,
      calories: form.value.calories ? Number(form.value.calories) : undefined
    }
    await apiPost('/api/v1/rides', rideData)
    form.value = { date: '', distance_km: '', duration_minutes: '', avg_speed_kmh: '', elevation_gain_m: '', calories: '' }
    await load()
  } catch (e) {
    addError.value = e.message
  } finally {
    adding.value = false
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
