<template>
  <section>
    <div class="panel">
      <h2>📅 Calendario & Obiettivi</h2>

      <div class="calendar-controls">
        <div class="calendar-nav">
          <button class="btn btn-secondary btn-sm" @click="prevMonth">◀</button>
          <span class="month-label">{{ monthLabel }}</span>
          <button class="btn btn-secondary btn-sm" @click="nextMonth">▶</button>
          <button class="btn btn-secondary btn-sm" @click="goToday">Oggi</button>
        </div>
        <div class="athlete-select">
          <label>Atleta:</label>
          <select v-model.number="athleteId" @change="loadEvents">
            <option :value="0">Generale</option>
            <option v-for="a in athletes" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
        </div>
      </div>

      <div class="calendar-legend">
        <span class="legend-item legend-training">Allenamento</span>
        <span class="legend-item legend-race">Gara</span>
        <span class="legend-item legend-recovery">Recupero</span>
        <span class="legend-item legend-goal">Obiettivo</span>
        <span class="legend-item legend-test">Test</span>
        <span class="legend-item legend-other">Altro</span>
      </div>

      <div class="calendar-grid">
        <div class="cal-header" v-for="d in weekDays" :key="d">{{ d }}</div>
        <div v-for="(day, idx) in calendarDays" :key="idx" class="cal-cell" :class="{
          'other-month': !day.currentMonth,
          'today': isToday(day),
          'has-events': day.events.length > 0
        }" @click="openAddForDate(day.date)">
          <span class="day-num">{{ day.day }}</span>
          <div class="day-events">
            <span v-for="ev in day.events.slice(0, 3)" :key="ev.id" class="event-dot" :class="'dot-' + ev.event_type">
              {{ ev.title }}
            </span>
            <span v-if="day.events.length > 3" class="more-events">+{{ day.events.length - 3 }}</span>
          </div>
        </div>
      </div>

      <div v-if="selectedDateEvents.length" class="day-detail">
        <h3>Eventi del {{ selectedDate }} <span class="event-count">({{ selectedDateEvents.length }})</span></h3>
        <ul class="event-list">
          <li v-for="ev in selectedDateEvents" :key="ev.id" class="event-item" :class="{ completed: ev.completed }">
            <span class="event-check">
              <input type="checkbox" :checked="ev.completed" @change="toggleComplete(ev)" :name="'event-complete-' + ev.id" />
            </span>
            <span class="event-info">
              <strong class="event-title">{{ ev.title }}</strong>
              <span class="event-meta">
                <span class="badge" :class="'badge-' + ev.event_type">{{ eventLabel(ev.event_type) }}</span>
                <span v-if="ev.duration_minutes">{{ ev.duration_minutes }} min</span>
                <span v-if="ev.weather_temp !== null && ev.weather_temp !== undefined" class="weather-badge" :class="'weather-score-' + weatherScoreClass(ev)">
                  🌡️ {{ ev.weather_temp }}°C 💨 {{ ev.weather_humidity }}%
                </span>
              </span>
              <span v-if="ev.description" class="event-desc">{{ ev.description }}</span>
            </span>
            <span class="event-actions">
              <button class="btn btn-secondary btn-xs" @click="openEdit(ev)">Modifica</button>
              <button class="btn btn-danger btn-xs" @click="askDeleteEvent(ev.id)">Elimina</button>
            </span>
          </li>
        </ul>
      </div>
    </div>

    <div class="panel">
      <h2>🎯 Collegamento Obiettivi</h2>
      <div class="objectives-box">
        <div class="obj-card" v-for="obj in recommendedObjectives" :key="obj.label" @click="quickAddFromObjective(obj)">
          <div class="obj-icon">{{ obj.icon }}</div>
          <div class="obj-text">
            <strong>{{ obj.label }}</strong>
            <small>{{ obj.hint }}</small>
          </div>
          <div class="obj-action">+ Aggiungi</div>
        </div>
      </div>
      <div v-if="athleteGoals" class="athlete-goals-display">
        <small>Obiettivi atleta registrati:</small>
        <p>{{ athleteGoals }}</p>
      </div>
    </div>

    <div v-if="showForm" class="panel form-overlay">
      <h3>{{ editingEvent ? 'Modifica Evento' : 'Nuovo Evento' }}</h3>
      <form @submit.prevent="saveEvent" class="form-grid">
        <div class="form-group">
          <label for="event-title">Titolo *</label>
          <input id="event-title" v-model="form.title" required maxlength="200" />
        </div>
        <div class="form-group">
          <label for="event-type">Tipo</label>
          <select id="event-type" v-model="form.event_type">
            <option value="training">Allenamento</option>
            <option value="race">Gara</option>
            <option value="recovery">Recupero</option>
            <option value="goal_deadline">Scadenza Obiettivo</option>
            <option value="test">Test</option>
            <option value="other">Altro</option>
          </select>
        </div>
        <div class="form-group">
          <label for="event-date">Data</label>
          <input id="event-date" type="date" v-model="form.date" required />
        </div>
        <div class="form-group">
          <label for="event-duration">Durata (min)</label>
          <input id="event-duration" type="number" v-model.number="form.duration_minutes" min="0" />
        </div>
        <div class="form-group">
          <label for="event-lat">Latitudine</label>
          <input id="event-lat" type="number" v-model.number="form.lat" step="0.0001" placeholder="Opzionale" />
        </div>
        <div class="form-group">
          <label for="event-lon">Longitudine</label>
          <input id="event-lon" type="number" v-model.number="form.lon" step="0.0001" placeholder="Opzionale" />
        </div>
        <div class="form-group full-width">
          <label for="event-description">Descrizione</label>
          <textarea id="event-description" v-model="form.description" maxlength="1000" rows="3"></textarea>
        </div>
        <div v-if="weatherForecast" class="weather-preview">
          <h4>🌤️ Previsione meteo per {{ form.date }}</h4>
          <div class="weather-info">
            <span v-if="weatherForecast.temperature !== null">🌡️ {{ weatherForecast.temperature }}°C</span>
            <span v-if="weatherForecast.humidity !== null">💧 {{ weatherForecast.humidity }}%</span>
            <span v-if="weatherForecast.description">{{ weatherForecast.description }}</span>
            <span class="weather-score" :class="'score-' + weatherScore">Score: {{ weatherScore }}/10</span>
            <p class="weather-advice">{{ weatherForecast.advice }}</p>
          </div>
        </div>
        <div v-if="calendarError" class="error-text">{{ calendarError }}</div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">Salva</button>
          <button type="button" class="btn btn-secondary" @click="showForm = false">Annulla</button>
        </div>
      </form>
    </div>
    <ConfirmModal
      v-model="showDeleteModal"
      title="Elimina Evento"
      :message="`Sei sicuro di voler eliminare l'evento '${deleteTargetTitle}'?`"
      confirm-label="Elimina"
      cancel-label="Annulla"
      @confirm="handleDelete"
    />
  </section>
</template>

<style scoped>
.weather-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75em;
  margin-left: 6px;
}
.weather-score-0 { background: #fee2e2; color: #991b1b; }
.weather-score-1 { background: #fef3c7; color: #92400e; }
.weather-score-2 { background: #dbeafe; color: #1e40af; }
.weather-score-3 { background: #dcfce7; color: #166534; }
.weather-score-4 { background: #dcfce7; color: #166534; }

.weather-preview {
  grid-column: span 2;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  margin-top: 8px;
}
.weather-info {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.weather-score {
  font-weight: 600;
}
.score-8, .score-9, .score-10 { color: #166534; }
.score-5, .score-6, .score-7 { color: #92400e; }
.score-0, .score-1, .score-2, .score-3, .score-4 { color: #991b1b; }
</style>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { apiGet, apiPost, apiDelete, apiPut } from '../utils/api.js'
import ConfirmModal from './ConfirmModal.vue'

const athleteId = ref(1)
const athletes = ref([])
const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth())
const events = ref([])
const showForm = ref(false)
const showDeleteModal = ref(false)
const deleteTargetId = ref(null)
const deleteTargetTitle = ref('')
const editingEvent = ref(null)
const form = ref({ title: '', event_type: 'training', date: '', duration_minutes: 0, description: '', completed: false })
const athleteGoals = ref('')
const calendarError = ref('')

const weekDays = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

const monthLabel = computed(() => {
  const months = ['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre']
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
    return today.toLocaleDateString('it-IT')
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
  { label: 'Allenamento Intervalli', icon: '⚡', hint: 'Sessione HIIT', event_type: 'training', duration: 45, title: 'Allenamento Intervalli' },
  { label: 'Uscita Lunga', icon: '🏔️', hint: 'Fondo lento', event_type: 'training', duration: 120, title: 'Uscita Lunga' },
  { label: 'Recupero Attivo', icon: '🧘', hint: 'Allungamento', event_type: 'recovery', duration: 30, title: 'Recupero Attivo' },
  { label: 'Test FTP', icon: '🔬', hint: 'Misura potenza', event_type: 'test', duration: 60, title: 'Test FTP' },
  { label: 'Gara', icon: '🏁', hint: 'Competizione', event_type: 'race', duration: 180, title: 'Gara' },
  { label: 'Scadenza Obiettivo', icon: '🎯', hint: 'Deadline', event_type: 'goal_deadline', duration: 0, title: 'Scadenza Obiettivo' },
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
  const map = { training: 'Allenamento', race: 'Gara', recovery: 'Recupero', goal_deadline: 'Obiettivo', test: 'Test', other: 'Altro' }
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
    if (athletes.value.length > 0 && athleteId.value <= 0) {
      athleteId.value = athletes.value[0].id
    }
  } catch (e) {
    athletes.value = []
  }
}

async function loadEvents() {
  if (athleteId.value <= 0) { events.value = []; return }
  try {
    const data = await apiGet('/api/v1/calendar/events', { athlete_id: athleteId.value, year: currentYear.value, month: currentMonth.value + 1 })
    events.value = data.events || []
  } catch (e) {
    events.value = []
  }
}

async function loadGoals() {
  if (athleteId.value <= 0) { athleteGoals.value = ''; return }
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
    calendarError = e.message || 'Errore nel salvataggio'
  }
}

async function handleDelete() {
  if (!deleteTargetId.value) return
  try {
    await apiDelete(`/api/v1/calendar/events/${deleteTargetId.value}`)
    loadEvents()
  } catch (e) {
    calendarError = e.message || 'Errore nell\'eliminazione'
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
     calendarError = e.message || 'Errore nel completamento'
   }
}

async function fetchWeatherForecast() {
   if (!form.value.lat || !form.value.lon || !form.value.date) {
     weatherForecast.value = null
     return
   }
   try {
     weatherForecast.value = await apiGet('/api/v1/weather', { lat: form.value.lat, lon: form.value.lon, date: form.value.date })
   } catch (e) {
     weatherForecast.value = null
   }
}

function weatherScoreClass(ev) {
   if (!ev.weather_temp || !ev.weather_humidity) return 5
   const score = Math.round((ev.weather_temp >= 5 && ev.weather_temp <= 30 && ev.weather_humidity < 70) ? 8 : (ev.weather_temp >= 0 && ev.weather_temp <= 35 ? 6 : 3))
   return score
}

const weatherScore = computed(() => {
   if (!weatherForecast.value) return 5
   const s = weatherForecast.value.score || 5
   return s
})

const weatherForecast = ref(null)

onMounted(() => {
   loadAthletes()
   loadEvents()
   loadGoals()
})

watch(athleteId, () => {
   loadEvents()
   loadGoals()
})

watch(form, () => {
   if (form.value.lat && form.value.lon && form.value.date) {
     fetchWeatherForecast()
   }
}, { deep: true })
</script>
