<template>
  <div class="panel">
    <h2>🏃 Profilo Atleta</h2>
    <form id="athlete-form" class="form-grid" novalidate>
      <div class="form-group"><label for="athlete-name">Nome</label><input id="athlete-name" type="text" v-model="form.name" required /></div>
      <div class="form-group"><label for="athlete-age">Età</label><input id="athlete-age" type="number" v-model.number="form.age" min="10" max="100" /></div>
      <div class="form-group"><label for="athlete-weight">Peso (kg)</label><input id="athlete-weight" type="number" v-model.number="form.weight_kg" min="20" max="300" step="0.1" /></div>
      <div class="form-group"><label for="athlete-height">Altezza (cm)</label><input id="athlete-height" type="number" v-model.number="form.height_cm" min="100" max="250" /></div>
      <div class="form-group"><label for="athlete-fat">Massa Grassa (%)</label><input id="athlete-fat" type="number" v-model.number="form.fat_percentage" min="3" max="60" step="0.1" /></div>
      <div class="form-group"><label for="athlete-years">Anni attività</label><input id="athlete-years" type="number" v-model.number="form.years_active" min="0" max="80" /></div>
      <div class="form-group"><label for="athlete-weekly">Sessioni/settimana</label><input id="athlete-weekly" type="number" v-model.number="form.weekly_sessions" min="0" max="14" /></div>
      <div class="form-group"><label for="athlete-monthly">Ore/mese</label><input id="athlete-monthly" type="number" v-model.number="form.monthly_hours" min="0" step="0.5" /></div>
      <div class="form-group"><label for="athlete-annual">Ore/anno</label><input id="athlete-annual" type="number" v-model.number="form.annual_hours" min="0" step="0.5" /></div>
      <div class="form-group">
        <label for="athlete-level">Livello</label>
        <select id="athlete-level" v-model="form.experience_level">
          <option>Beginner</option><option>Amateur</option><option>Intermediate</option><option>Advanced</option><option>Elite</option>
        </select>
      </div>
    </form>
    <div class="form-actions">
      <button class="btn btn-primary" @click="save">Salva Atleta</button>
      <button class="btn btn-secondary" @click="getScores">📊 Punteggi</button>
    </div>
    <div v-if="result" class="result-box">{{ result }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { apiGet, apiPost } from '../utils/api.js'

const emit = defineEmits(['toast'])
const form = ref({ name: '', age: 30, weight_kg: 70, height_cm: 175, fat_percentage: 15, years_active: 1, weekly_sessions: 3, monthly_hours: 0, annual_hours: 0, experience_level: 'Beginner' })
const result = ref('')
const athleteId = ref(null)

async function save() {
  try {
    const data = await apiPost('/api/v1/athletes', form.value)
    athleteId.value = data.id
    result.value = 'Profilo atleta salvato (ID: ' + data.id + ')'
  } catch (e) {
    result.value = 'Errore: ' + (e.message || e)
  }
}

async function getScores() {
  try {
    const id = athleteId.value
    if (!id) {
      result.value = 'Salva prima il profilo atleta'
      return
    }
    const data = await apiGet('/api/v1/scores/athlete/' + id)
    result.value = JSON.stringify(data, null, 2)
  } catch (e) {
    result.value = 'Errore: ' + (e.message || e)
  }
}
</script>
