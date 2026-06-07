<template>
  <div class="panel">
    <h2>🧠 AI Coach</h2>
    <div class="form-grid">
      <div class="form-group"><label for="coach-athlete-id">ID Atleta (0 = ultimo)</label><input type="number" v-model.number="athleteId" min="0" /></div>
      <div class="form-group">
        <button class="btn btn-primary" @click="loadCoach">📊 Carica Coach Completo</button>
      </div>
    </div>
    <div v-if="loading" class="loading-text">Analisi in corso...</div>

    <div v-if="coachData" class="stats" style="margin-top:15px">
      <div class="stat-card"><div class="stat-value">{{ coachData.scores?.performance ?? 0 }}</div><div class="stat-label">Performance</div></div>
      <div class="stat-card"><div class="stat-value">{{ coachData.scores?.endurance ?? 0 }}</div><div class="stat-label">Endurance</div></div>
      <div class="stat-card"><div class="stat-value">{{ coachData.scores?.fatigue ?? 0 }}</div><div class="stat-label">Fatigue</div></div>
      <div class="stat-card"><div class="stat-value">{{ coachData.scores?.recovery ?? 0 }}</div><div class="stat-label">Recovery</div></div>
    </div>

    <div v-if="coachData" class="panel" style="margin-top:15px">
      <h3>💡 Consigli di Allenamento</h3>
      <div class="result-box">{{ coachData.training_advice }}</div>
      <h3>📈 Analisi Storica</h3>
      <div class="result-box">{{ coachData.historical }}</div>
      <h3>🧘 Consigli di Recupero</h3>
      <div class="result-box">{{ coachData.recovery_advice }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { apiGet } from '../utils/api.js'

const athleteId = ref(0)
const loading = ref(false)
const coachData = ref(null)

async function loadCoach() {
  loading.value = true
  try {
    coachData.value = await apiGet('/api/v1/coach/full', { athlete_id: athleteId.value || 0 })
  } catch (e) {
    console.error('coach', e)
  } finally {
    loading.value = false
  }
}
</script>
