<template>
  <section>
    <div class="panel">
      <h2>📅 Calendar & Goals</h2>

      <div class="calendar-controls">
        <div class="calendar-nav">
          <button
            class="btn btn-secondary btn-sm"
            @click="prevMonth"
          >
            ◀
          </button>
          <span class="month-label">{{ monthLabel }}</span>
          <button
            class="btn btn-secondary btn-sm"
            @click="nextMonth"
          >
            ▶
          </button>
          <button
            class="btn btn-secondary btn-sm"
            @click="goToday"
          >
            Today
          </button>
        </div>
        <div class="athlete-select">
          <label>Athlete:</label>
          <select
            v-model.number="athleteId"
            @change="loadEvents"
          >
            <option :value="0">
              General
            </option>
            <option
              v-for="a in athletes"
              :key="a.id"
              :value="a.id"
            >
              {{ a.name }}
            </option>
          </select>
        </div>
      </div>

      <div class="calendar-legend">
        <span class="legend-item legend-training">Training</span>
        <span class="legend-item legend-race">Race</span>
        <span class="legend-item legend-recovery">Recovery</span>
        <span class="legend-item legend-goal">Goal</span>
        <span class="legend-item legend-test">Test</span>
        <span class="legend-item legend-other">Other</span>
      </div>

      <div class="calendar-grid">
        <div
          v-for="d in weekDays"
          :key="d"
          class="cal-header"
        >
          {{ d }}
        </div>
        <div
          v-for="(day, idx) in calendarDays"
          :key="idx"
          class="cal-cell"
          :class="{
            'other-month': !day.currentMonth,
            'today': isToday(day),
            'has-events': day.events.length > 0,
          }"
        >
          <span
          class="day-num"
          @click="openAddForDate(day.date)"
        >
          {{ day.day }}</span>
          <div class="day-events">
            <span
              v-for="ev in day.events.slice(0, 3)"
              :key="ev.id"
              class="event-dot"
              :class="'dot-' + ev.event_type"
            >
              {{ ev.title }}
            </span>
            <span
              v-if="day.events.length > 3"
              class="more-events"
            >+{{ day.events.length - 3 }}</span>
          </div>
        </div>
      </div>

      <div
        v-if="fitnessData.length"
        class="panel fitness-chart-panel"
      >
        <h2>📈 Fitness ATL / CTL / TSB</h2>
        <canvas
          ref="fitnessCanvas"
          height="200"
        />
      </div>
    </div>

    <div class="panel">
      <h2>🎯 Linked Goals</h2>
      <div class="objectives-box">
        <div
          v-for="obj in recommendedObjectives"
          :key="obj.label"
          class="obj-card"
        >
          <div class="obj-icon">
            {{ obj.icon }}
          </div>
          <div class="obj-text">
            <strong>{{ obj.label }}</strong>
            <small>{{ obj.hint }}</small>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="showForm"
      class="panel form-overlay"
    >
      <h3>{{ editingEvent ? 'Edit Event' : 'New Event' }}</h3>
      <form
        class="form-grid"
        @submit.prevent="saveEvent"
      >
        <div class="form-group">
          <label for="event-title">Title *</label>
          <input
            id="event-title"
            v-model="form.title"
            required
            maxlength="200"
          >
        </div>
        <div class="form-actions">
          <button
            type="submit"
            class="btn btn-primary"
          >
            Save
          </button>
          <button
            type="button"
            class="btn btn-secondary"
            @click="showForm = false"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
    <ConfirmModal
      v-model="showDeleteModal"
      title="Delete Event"
      :message="`Delete event '${deleteTargetTitle}'?`"
      confirm-label="Delete"
      cancel-label="Cancel"
      @confirm="handleDelete"
    />
  </section>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { apiGet, apiPost, apiDelete, apiPut } from '../utils/api'
import ConfirmModal from './ConfirmModal.vue'
import Chart from 'chart.js/auto'

const athleteId = ref(null)
const athletes = ref([])
const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth())
const events = ref([])
const fitnessData = ref([])
const fitnessCanvas = ref(null)
let fitnessChart = null
const showForm = ref(false)
const showDeleteModal = ref(false)
const deleteTargetId = ref(null)
const deleteTargetTitle = ref('')
const editingEvent = ref(null)
const form = ref({ title: '', event_type: 'training', date: '', duration_minutes: 0, description: '', completed: false })
const athleteGoals = ref('')
const calendarError = ref('')

const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

 const monthLabel = computed(() => {
   const months = ['January','February','March','April','May','June','July','August','September','October','November','December']
   return `${months[currentMonth.value]} ${currentYear.value}`
 })

const calendarDays = computed(() => {
  const firstDay = new Date(currentYear.value, currentMonth.value, 1)
  let startWeekDay = firstDay.getDay() - 1
  if (startWeekDay < 0) startWeekDay = 6
  const daysInMonth = new Date(currentYear.value, currentMonth.value + 1, 0).getDate()
  const prevMonthDays = new Date(currentYear.value, currentMonth.value, 0).getDate()
  const result = []
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${(today.getMonth()+1).toString().padStart(2,'0')}-${today.getDate().toString().padStart(2,'0')}`
  for (let i = 0; i < startWeekDay; i++) {
    const d = prevMonthDays - startWeekDay + 1 + i
    const m = currentMonth.value === 0 ? 12 : currentMonth.value
    const y = currentMonth.value === 0 ? currentYear.value - 1 : currentYear.value
    result.push({ day: d, date: `${y}-${m.toString().padStart(2,'0')}-${d.toString().padStart(2,'0')}`, currentMonth: false, events: [] })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${currentYear.value}-${(currentMonth.value+1).toString().padStart(2,'0')}-${d.toString().padStart(2,'0')}`
    const dayEvents = events.value.filter(e => e.date === dateStr)
    result.push({ day: d, date: dateStr, currentMonth: true, events: dayEvents, isToday: dateStr === todayStr })
  }
  const remaining = 42 - result.length
  for (let i = 1; i <= remaining; i++) {
    const m = currentMonth.value === 11 ? 1 : currentMonth.value + 2
    const y = currentMonth.value === 11 ? currentYear.value + 1 : currentYear.value
    result.push({ day: i, date: `${y}-${m.toString().padStart(2,'0')}-${i.toString().padStart(2,'0')}`, currentMonth: false, events: [] })
  }
  return result
})

const selectedDate = computed(() => {
  const today = new Date()
  const y = today.getFullYear(), m = today.getMonth(), d = today.getDate()
  if (currentMonth.value === m && currentYear.value === y) {
    return today.toLocaleDateString('en-US')
  }
  return `${d}/${m+1}/${y}`
})

const selectedDateEvents = computed(() => {
  const today = new Date()
  const y = today.getFullYear(), m = today.getMonth(), d = today.getDate()
  if (currentMonth.value === m && currentYear.value === y) {
    const todayStr = `${y}-${(m+1).toString().padStart(2,'0')}-${d.toString().padStart(2,'0')}`
    return events.value.filter(e => e.date === todayStr).sort((a, b) => a.id - b.id)
  }
  return []
})

const recommendedObjectives = computed(() => [
   { label: 'Interval Training', icon: '⚡', hint: 'HIIT session', event_type: 'training', duration: 45, title: 'Interval Training' },
   { label: 'Long Ride', icon: '🏔️', hint: 'Easy ride', event_type: 'training', duration: 120, title: 'Long Ride' },
   { label: 'Active Recovery', icon: '🧘', hint: 'Stretching', event_type: 'recovery', duration: 30, title: 'Active Recovery' },
   { label: 'FTP Test', icon: '🔬', hint: 'Power test', event_type: 'test', duration: 60, title: 'FTP Test' },
   { label: 'Race', icon: '🏁', hint: 'Competition', event_type: 'race', duration: 180, title: 'Race' },
   { label: 'Goal Deadline', icon: '🎯', hint: 'Deadline', event_type: 'goal_deadline', duration: 0, title: 'Goal Deadline' },
 ])

function isToday(day) {
  if (!day.isToday) return false
  const today = new Date()
  return day.date === `${today.getFullYear()}-${(today.getMonth()+1).toString().padStart(2,'0')}-${today.getDate().toString().padStart(2,'0')}`
}

function prevMonth() {
  if (currentMonth.value === 0) { currentMonth.value = 11; currentYear.value-- } else { currentMonth.value-- }
  loadEvents()
}
function nextMonth() {
  if (currentMonth.value === 11) { currentMonth.value = 0; currentYear.value++ } else { currentMonth.value++ }
  loadEvents()
}
function goToday() {
  const today = new Date()
  currentYear.value = today.getFullYear()
  currentMonth.value = today.getMonth()
  loadEvents()
}

function eventLabel(type) {
   const map = { training: 'Training', race: 'Race', recovery: 'Recovery', goal_deadline: 'Goal', test: 'Test', other: 'Other' }
   return map[type] || type
 }

function openAddForDate(date) {
  editingEvent.value = null
  form.value = { title: '', event_type: 'training', date, duration_minutes: 0, description: '', completed: false, lat: null, lon: null }
  showForm.value = true
}

function openEdit(ev) {
  editingEvent.value = ev
  form.value = { ...ev }
  showForm.value = true
}

function quickAddFromObjective(obj) {
  const today = new Date()
  const dateStr = `${today.getFullYear()}-${(today.getMonth()+1).toString().padStart(2,'0')}-${today.getDate().toString().padStart(2,'0')}`
  editingEvent.value = null
  form.value = { title: obj.title, event_type: obj.event_type, date: dateStr, duration_minutes: obj.duration, description: obj.hint, completed: false, lat: null, lon: null }
  showForm.value = true
}

async function loadAthletes() {
  try {
    const data = await apiGet('/api/v1/athletes')
    athletes.value = data.athletes || []
    if (athletes.value.length > 0 && !athleteId.value) {
      athleteId.value = athletes.value[0].id
    }
  } catch (e) {
    athletes.value = []
  }
}

async function loadEvents() {
  if (!athleteId.value) { events.value = []; fitnessData.value = []; return }
  try {
    const [eventsData, fitness] = await Promise.all([
      apiGet('/api/v1/calendar/events', { athlete_id: athleteId.value, year: currentYear.value, month: currentMonth.value + 1 }),
      apiGet('/api/v1/training/load', { athlete_id: athleteId.value, days: 30 }).catch(() => ({ training_loads: [] })),
    ])
    events.value = eventsData.events || []
    fitnessData.value = fitness.training_loads || []
  } catch (e) {
    events.value = []
    fitnessData.value = []
  }
}

function renderFitnessChart() {
  if (!fitnessCanvas.value || !fitnessData.value.length) return
  const labels = fitnessData.value.map(d => {
    const dt = new Date(d.date)
    return `${dt.getDate()}/${dt.getMonth() + 1}`
  })
  const atl = fitnessData.value.map(d => d.atl)
  const ctl = fitnessData.value.map(d => d.ctl)
  const tsb = fitnessData.value.map(d => d.tsb)
  if (fitnessChart) fitnessChart.destroy()
  const ctx = fitnessCanvas.value.getContext('2d')
  fitnessChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'ATL (Fatica)', data: atl, borderColor: '#ff6b35', backgroundColor: 'rgba(255,107,53,0.1)', fill: true, tension: 0.3, pointRadius: 3 },
        { label: 'CTL (Fitness)', data: ctl, borderColor: '#0088ff', backgroundColor: 'rgba(0,136,255,0.1)', fill: true, tension: 0.3, pointRadius: 3 },
        { label: 'TSB (Forma)', data: tsb, borderColor: '#00ffcc', backgroundColor: 'rgba(0,255,204,0.1)', fill: true, tension: 0.3, pointRadius: 3 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#b0b5c1', usePointStyle: true, padding: 16 } },
      },
      scales: {
        x: { ticks: { color: '#6e7687', maxRotation: 0, maxTicksLimit: 10 }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#6e7687' }, grid: { color: 'rgba(255,255,255,0.06)' } },
      },
    },
  })
}

async function loadGoals() {
  if (!athleteId.value) { athleteGoals.value = ''; return }
  try {
    const data = await apiGet('/api/v1/athletes/' + athleteId.value)
    athleteGoals.value = data.goals || ''
  } catch (e) {
    athleteGoals.value = ''
  }
}

async function saveEvent() {
  try {
    const payload = { ...form.value, athlete_id: athleteId.value }
    if (editingEvent.value) {
      await apiPut(`/api/v1/calendar/events/${editingEvent.value.id}`, payload)
    } else {
      await apiPost('/api/v1/calendar/events', payload)
    }
    showForm.value = false
    editingEvent.value = null
    loadEvents()
    loadGoals()
  } catch (e) {
    calendarError.value = e.message || 'Error saving'
  }
}

async function handleDelete() {
  if (!deleteTargetId.value) return
  try {
    await apiDelete(`/api/v1/calendar/events/${deleteTargetId.value}`)
    loadEvents()
  } catch (e) {
calendarError.value = e.message || 'Error deleting'
   } finally {
     deleteTargetId.value = null
     deleteTargetTitle.value = ''
   }
 }

 function askDeleteEvent(id) {
   const ev = events.value.find(e => e.id === id)
   deleteTargetId.value = id
   deleteTargetTitle.value = ev ? ev.title : ''
   showDeleteModal.value = true
 }

 async function toggleComplete(ev) {
   try {
     await apiPost(`/api/v1/calendar/events/${ev.id}/complete`, {})
     loadEvents()
   } catch (e) {
     calendarError.value = e.message || 'Error completing'
   }
  }

  let initialized = false

onMounted(async () => {
  await loadAthletes()
  initialized = true
  await loadEvents()
  await loadGoals()
  renderFitnessChart()
})

watch(athleteId, () => {
  if (!initialized) return
  loadEvents()
  loadGoals()
})

watch(fitnessData, () => {
  renderFitnessChart()
}, { deep: true })

watch([currentYear, currentMonth], () => {
  if (!initialized) return
  loadEvents()
})
</script>

  <style scoped>
.fitness-chart-panel {
  position: relative;
  height: 260px;
}
</style>
