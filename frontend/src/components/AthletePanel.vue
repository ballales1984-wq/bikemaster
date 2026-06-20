<template>
  <div class="panel">
    <h2>🏃 Athlete Profile</h2>
    <form id="athlete-form" class="form-grid" novalidate>
      <div class="form-group"><label for="athlete-name">Name</label><input id="athlete-name" type="text" v-model="form.name" required /></div>
      <div class="form-group"><label for="athlete-age">Age</label><input id="athlete-age" type="number" v-model.number="form.age" min="10" max="100" /></div>
      <div class="form-group"><label for="athlete-weight">Weight (kg)</label><input id="athlete-weight" type="number" v-model.number="form.weight_kg" min="20" max="300" step="0.1" /></div>
      <div class="form-group"><label for="athlete-height">Height (cm)</label><input id="athlete-height" type="number" v-model.number="form.height_cm" min="100" max="250" /></div>
      <div class="form-group"><label for="athlete-fat">Body Fat (%)</label><input id="athlete-fat" type="number" v-model.number="form.fat_percentage" min="3" max="60" step="0.1" /></div>
      <div class="form-group"><label for="athlete-years">Years Active</label><input id="athlete-years" type="number" v-model.number="form.years_active" min="0" max="80" /></div>
      <div class="form-group"><label for="athlete-weekly">Sessions/week</label><input id="athlete-weekly" type="number" v-model.number="form.weekly_sessions" min="0" max="14" /></div>
      <div class="form-group"><label for="athlete-monthly">Hours/month</label><input id="athlete-monthly" type="number" v-model.number="form.monthly_hours" min="0" step="0.5" /></div>
      <div class="form-group"><label for="athlete-annual">Hours/year</label><input id="athlete-annual" type="number" v-model.number="form.annual_hours" min="0" step="0.5" /></div>
      <div class="form-group">
        <label for="athlete-level">Level</label>
        <select id="athlete-level" v-model="form.experience_level">
          <option>Beginner</option><option>Amateur</option><option>Intermediate</option><option>Advanced</option><option>Elite</option>
        </select>
      </div>
    </form>
    <div class="form-actions">
      <button class="btn btn-primary" @click="save">Save Athlete</button>
      <button class="btn btn-secondary" @click="getScores">📊 Scores</button>
    </div>
    <div v-if="result" class="result-box">{{ result }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGet, apiPost, apiPut } from '../utils/api'

const emit = defineEmits(['toast'])
const form = ref({
  name: '',
  age: 30,
  weight_kg: 70,
  height_cm: 175,
  fat_percentage: 15,
  years_active: 1,
  weekly_sessions: 3,
  monthly_hours: 0,
  annual_hours: 0,
  experience_level: 'Beginner'
})
const result = ref('')
const athleteId = ref(null)

async function loadAthlete() {
  const data = await apiGet('/api/v1/athletes')
  const athlete = data.athletes?.[0]
  if (athlete) {
    athleteId.value = athlete.id
    form.value = { ...form.value, ...athlete }
  }
}

async function save() {
  try {
    const data = athleteId.value
      ? await apiPut('/api/v1/athletes/' + athleteId.value, form.value)
      : await apiPost('/api/v1/athletes', form.value)
athleteId.value = data.id
     result.value = 'Athlete profile saved (ID: ' + data.id + ')'
   } catch (e) {
     result.value = 'Error: ' + (e.message || e)
   }
 }

 async function getScores() {
   try {
     const id = athleteId.value
     if (!id) {
       result.value = 'Save athlete profile first'
       return
     }
     const data = await apiGet('/api/v1/scores/athlete/' + id)
     result.value = JSON.stringify(data, null, 2)
   } catch (e) {
     result.value = 'Error: ' + (e.message || e)
   }
 }

 onMounted(() => {
   loadAthlete().catch(e => {
     result.value = 'Error: ' + (e.message || e)
   })
 })
</script>
