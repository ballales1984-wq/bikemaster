<template>
  <div class="panel">
    <h2>🚴‍♂️ Pianificatore Granfondo</h2>
    
    <div class="form-grid">
      <div class="form-group">
        <label for="gf-start-date">Data Inizio</label>
        <input id="gf-start-date" type="date" v-model="startDate" />
      </div>
      <div class="form-group">
        <label for="gf-weeks">Numero Settimane</label>
        <select id="gf-weeks" v-model.number="weeks">
          <option :value="8">8 settimane</option>
          <option :value="9">9 settimane</option>
          <option :value="10">10 settimane</option>
          <option :value="11">11 settimane</option>
          <option :value="12">12 settimane</option>
        </select>
      </div>
      <div class="form-group">
        <button class="btn btn-primary" @click="generatePlan">📅 Genera Piano</button>
      </div>
    </div>
    
    <div v-if="loading" class="loading-text">Generazione piano...</div>
    
    <div v-if="plan" class="plan-container">
      <div class="plan-header">
        <h3>Piano Allenamento {{ weeks }} settimane</h3>
        <p class="plan-dates">Dal {{ startDate }} al {{ endDate }}</p>
      </div>

      <div class="plan-actions">
        <button class="btn btn-success" @click="savePlan" :disabled="saving">
          {{ saving ? 'Salvataggio...' : '💾 Salva nel Calendario' }}
        </button>
        <span v-if="saveMessage" class="save-message" :class="{ success: saveSuccess, error: !saveSuccess }">
          {{ saveMessage }}
        </span>
      </div>

      <div class="tapering-info">
        <span class="badge badge-info">📊 Tapering: -40% volume 2 settimane prima, -60% ultima settimana</span>
      </div>
      
      <div class="calendar-grid plan-grid">
        <div class="cal-header" v-for="d in weekDays" :key="d">{{ d }}</div>
        <div v-for="(day, idx) in calendarDays" :key="idx" class="cal-cell" :class="{ today: day.isToday }">
          <span class="day-num">{{ day.day }}</span>
          <div class="day-workouts">
            <div v-for="w in day.workouts" :key="w.title" class="workout-item" :class="'type-' + w.workout_type">
              {{ w.title }}
              <span class="workout-meta">{{ w.duration_minutes }}min {{ Math.round(w.target_intensity * 100) }}%</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="workout-legend">
        <span class="legend-item legend-endurance">Base Aerobica</span>
        <span class="legend-item legend-threshold">Thresholds</span>
        <span class="legend-item legend-sweetspot">Sweetspot</span>
        <span class="legend-item legend-recovery">Recupero</span>
        <span class="legend-item legend-race">Gara</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiGet, apiPost } from '../utils/api.js'

const athleteId = ref(null)
const startDate = ref(new Date().toISOString().split('T')[0])
const weeks = ref(8)
const loading = ref(false)
const plan = ref(null)

const weekDays = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

async function loadAthleteId() {
  const data = await apiGet('/api/v1/athletes')
  athleteId.value = data.athletes?.[0]?.id ?? 0
}

const endDate = computed(() => {
  const d = new Date(startDate.value)
  d.setDate(d.getDate() + weeks.value * 7)
  return d.toISOString().split('T')[0]
})

async function generatePlan() {
  if (!athleteId.value) return
  loading.value = true
  try {
    const result = await apiPost('/api/v1/training/granfondo/plan', {
      athlete_id: athleteId.value,
      start_date: startDate.value,
      target_weeks: weeks.value
    })
    plan.value = result.plan
  } catch (e) {
    console.error('plan error', e)
    plan.value = null
  } finally {
    loading.value = false
  }
}

const calendarDays = computed(() => {
  if (!plan.value) return []
  
  const start = new Date(startDate.value)
  const firstDay = start.getDay() || 7
  const totalDays = weeks.value * 7 + 1
  
  const result = []
  const today = new Date().toISOString().split('T')[0]
  
  for (let i = -firstDay + 1; i < totalDays; i++) {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    const dateStr = d.toISOString().split('T')[0]
    const dayWorkouts = plan.value.filter(w => w.date === dateStr)
    
    result.push({
      day: d.getDate(),
      date: dateStr,
      workouts: dayWorkouts,
      isToday: dateStr === today
    })
  }
  
  return result
})

onMounted(() => {
  loadAthleteId().catch(console.error)
})
</script>

<style scoped>
.plan-container {
  margin-top: 20px;
}

.plan-header h3 {
  color: var(--accent);
  margin-bottom: 5px;
}

.plan-dates {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.tapering-info {
  margin: 15px 0;
}

.badge-info {
  background: var(--accent-secondary);
  color: #fff;
}

.plan-grid {
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  margin-top: 15px;
}

.workout-item {
  font-size: 0.65rem;
  padding: 2px 4px;
  border-radius: 3px;
  margin-bottom: 2px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workout-meta {
  display: block;
  font-size: 0.6rem;
  opacity: 0.8;
}

.legend-endurance { background: #3498db; }
.legend-threshold { background: #e74c3c; }
.legend-sweetspot { background: #9b59b6; }
.legend-recovery { background: #2ecc71; }
.legend-race { background: #f39c12; }

.workout-legend {
  display: flex;
  gap: 8px;
  margin-top: 15px;
  flex-wrap: wrap;
}

.workout-legend .legend-item {
  font-size: 0.78rem;
  padding: 3px 8px;
  border-radius: 12px;
  color: #fff;
}

.plan-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}

.save-message {
  font-size: 0.9rem;
}

.save-message.success {
  color: #166534;
}

.save-message.error {
  color: #991b1b;
}

.btn-success {
  background: #22c55e;
  color: #fff;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
}

.btn-success:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>