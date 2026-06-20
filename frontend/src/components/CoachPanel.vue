<template>
  <div class="panel">
    <h2>🧠 AI Coach</h2>
    <div class="form-grid">
      <div class="form-group"><label for="coach-athlete-id">ID Atleta</label><input id="coach-athlete-id" type="number" v-model.number="athleteId" min="1" /></div>
      <div class="form-group">
        <button class="btn btn-primary" @click="loadCoach" :disabled="loading">{{ loading ? '🔄 Analisi in corso...' : '📊 Carica Coach Completo' }}</button>
      </div>
    </div>

    <div v-if="loading && !coachData" class="skeleton-container">
      <div class="skeleton skeleton-card" style="height: 100px; margin-bottom: 15px;"></div>
      <div class="skeleton skeleton-text" style="width: 80%;"></div>
      <div class="skeleton skeleton-text" style="width: 60%;"></div>
      <div class="skeleton skeleton-text" style="width: 70%;"></div>
    </div>

    <div v-if="coachData" class="stats" style="margin-top:15px">
      <div class="stat-card"><div class="stat-value">{{ scoreValue('Performance') }}</div><div class="stat-label">Performance</div></div>
      <div class="stat-card"><div class="stat-value">{{ scoreValue('Endurance') }}</div><div class="stat-label">Endurance</div></div>
      <div class="stat-card"><div class="stat-value">{{ scoreValue('Efficiency') }}</div><div class="stat-label">Efficiency</div></div>
    </div>

    <div v-if="coachData" class="panel" style="margin-top:15px">
      <h3>💡 Consigli di Allenamento</h3>
      <div class="result-box">{{ coachData.training_advice }}</div>
      <h3>📈 Analisi Storica</h3>
      <div class="result-box">{{ coachData.historical_analysis ?? '' }}</div>
      <h3>🧘 Consigli di Recupero</h3>
      <div class="result-box">{{ coachData.recovery_advice }}</div>
    </div>

    <div v-if="!loading && !coachData" class="empty-state">
      <div class="empty-icon">🧠</div>
      <div class="empty-title">Nessun dato coach</div>
      <div class="empty-desc">Inserisci un ID atleta e carica l'analisi AI completa.</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGet } from '../utils/api'

const athleteId = ref(null)
const loading = ref(false)
const coachData = ref(null)

async function loadAthleteId() {
  const data = await apiGet('/api/v1/athletes')
  athleteId.value = data.athletes?.[0]?.id ?? null
}

function scoreValue(label) {
  return coachData.value?.training_scores?.find((score) => score.label === label)?.value ?? 0
}

async function loadCoach() {
  if (!athleteId.value) return
  loading.value = true
  try {
    coachData.value = await apiGet('/api/v1/coach/full', { athlete_id: athleteId.value || 0 })
  } catch (e) {
    console.error('coach', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAthleteId().then(loadCoach).catch(console.error)
})
</script>
