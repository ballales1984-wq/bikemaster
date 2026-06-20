<template>
  <section>
<div class="panel" role="region" aria-label="Your cycling rides">
       <h2 id="rides-heading">📋 Your Rides</h2>
       <div class="add-ride-form">
         <h3>➕ Add New Ride</h3>
         <form @submit.prevent="handleAdd" class="ride-form">
           <div class="form-row">
             <input v-model="form.date" type="date" required class="form-input" />
             <input v-model="form.distance_km" type="number" step="0.01" placeholder="Distance (km)" required class="form-input" />
           </div>
           <div class="form-row">
             <input v-model="form.duration_minutes" type="number" placeholder="Duration (min)" required class="form-input" />
             <input v-model="form.avg_speed_kmh" type="number" step="0.01" placeholder="Avg speed (km/h)" class="form-input" />
           </div>
           <div class="form-row">
             <input v-model="form.elevation_gain_m" type="number" placeholder="Elevation (m)" class="form-input" />
             <input v-model="form.calories" type="number" placeholder="Calories" class="form-input" />
           </div>
           <button type="submit" class="btn btn-primary" :disabled="adding" :aria-busy="adding">{{ adding ? 'Adding...' : 'Add Ride' }}</button>
         </form>
         <p v-if="addError" class="error-text">{{ addError }}</p>
       </div>
       <p v-if="loading" class="loading-text" role="status" aria-live="polite">Loading...</p>
       <div v-else-if="rides.length === 0" class="empty-state">
         <div class="empty-icon">🏍️</div>
         <div class="empty-title">No rides recorded</div>
         <div class="empty-desc">Add your first ride to start tracking your performance.</div>
       </div>
       <div v-else class="rides-list" aria-live="polite" aria-label="Rides list">
         <div class="ride-item" v-for="ride in rides" :key="ride.id">
           <div>
             <div class="ride-date">{{ ride.date }}</div>
             <div class="ride-stats">{{ ride.distance_km }}km • {{ ride.duration_minutes }}min • {{ ride.avg_speed_kmh }} km/h</div>
           </div>
           <button class="btn btn-danger btn-sm" @click="askDelete(ride.id)" :aria-label="`Delete ride on ${ride.date}`">Delete</button>
         </div>
       </div>
     </div>

     <ConfirmModal
       v-model="showDeleteModal"
       title="Delete Ride"
       :message="`Are you sure you want to delete the ride on ${deleteTargetDate}?`"
       confirm-label="Delete"
       cancel-label="Cancel"
       @confirm="handleDelete"
     />
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGet, apiDelete, apiPost } from '../utils/api'
import ConfirmModal from './ConfirmModal.vue'

const loading = ref(true)
const adding = ref(false)
const addError = ref('')
const rides = ref([])
const form = ref({ date: '', distance_km: '', duration_minutes: '', avg_speed_kmh: '', elevation_gain_m: '', calories: '' })
const showDeleteModal = ref(false)
const deleteTargetId = ref(null)
const deleteTargetDate = ref('')

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

function askDelete(id) {
  deleteTargetId.value = id
  const ride = rides.value.find(r => r.id === id)
  deleteTargetDate.value = ride ? ride.date : ''
  showDeleteModal.value = true
}

async function handleDelete() {
  if (!deleteTargetId.value) return
  try {
    await apiDelete(`/api/v1/rides/${deleteTargetId.value}`)
    rides.value = rides.value.filter(r => r.id !== deleteTargetId.value)
  } catch (e) {
    console.error('delete failed', e)
  } finally {
    deleteTargetId.value = null
    deleteTargetDate.value = ''
  }
}

onMounted(() => {
  load()
})
</script>
