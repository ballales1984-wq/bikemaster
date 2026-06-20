<template>
  <div class="panel dashboard-panel">
    <h2>📊 Athlete Dashboard</h2>
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="dashboard-grid">
      <div class="dashboard-card">
        <h3>👤 Profile</h3>
        <p v-if="dashboard.athlete">
          Name: {{ dashboard.athlete.name }}<br />
          Email: {{ dashboard.athlete.email || 'Not specified' }}<br />
          Level: {{ dashboard.athlete.experience_level }}
        </p>
        <p v-else>Profile not configured</p>
      </div>
      <div class="dashboard-card">
        <h3>🚴 Stats</h3>
        <p v-if="dashboard.summary">
          Total rides: {{ dashboard.summary.total_rides }}<br />
          Total km: {{ dashboard.summary.total_km || 0 }}<br />
          Total hours: {{ dashboard.summary.total_hours || 0 }}<br />
          Calories: {{ dashboard.summary.total_calories || 0 }}
        </p>
      </div>
      <div class="dashboard-card">
        <h3>🏅 Scores</h3>
        <p v-if="dashboard.scores">
          Performance: {{ dashboard.scores.performance }}/10<br />
          Endurance: {{ dashboard.scores.endurance }}/10<br />
          Recovery: {{ dashboard.scores.recovery }}/10<br />
          Efficiency: {{ dashboard.scores.efficiency }}/10
        </p>
      </div>
      <div class="dashboard-card">
        <h3>📈 Fitness (7 days)</h3>
        <p v-if="dashboard.fitness">
          ATL: {{ dashboard.fitness.atl || 0 }}<br />
          CTL: {{ dashboard.fitness.ctl || 0 }}<br />
          TSB: {{ dashboard.fitness.tsb || 0 }}<br />
          Status: {{ dashboard.fitness.status || 'N/A' }}
        </p>
      </div>
      <div class="dashboard-card">
        <h3>🔥 Last 7 days</h3>
        <p v-if="dashboard.trends?.weekly_progress">
          <span v-for="(km, i) in dashboard.trends.weekly_progress" :key="i" class="progress-dot" :title="km + 'km'"></span>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGet } from '../utils/api'

const emit = defineEmits(['toast'])
const dashboard = ref({})
const loading = ref(true)
const error = ref('')

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const data = await apiGet('/api/v1/dashboard')
    dashboard.value = data
  } catch (e) {
    error.value = 'Error: ' + (e.message || e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDashboard().catch(e => {
    error.value = 'Error: ' + (e.message || e)
  })
})
</script>

<style scoped>
.dashboard-panel {
  padding: 1rem;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.dashboard-card {
  background: var(--card-bg, #f8f9fa);
  border-radius: 8px;
  padding: 1rem;
  border: 1px solid var(--border-color, #ddd);
}
.dashboard-card h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: var(--primary, #007bff);
}
.progress-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--primary, #007bff);
  margin: 2px;
}
.loading {
  text-align: center;
  padding: 2rem;
}
.error {
  color: #dc3545;
  padding: 1rem;
}
</style>