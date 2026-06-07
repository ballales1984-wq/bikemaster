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
              <input type="checkbox" :checked="ev.completed" @change="toggleComplete(ev)" />
            </span>
            <span class="event-info">
              <strong class="event-title">{{ ev.title }}</strong>
              <span class="event-meta">
                <span class="badge" :class="'badge-' + ev.event_type">{{ eventLabel(ev.event_type) }}</span>
                <span v-if="ev.duration_minutes">{{ ev.duration_minutes }} min</span>
              </span>
              <span v-if="ev.description" class="event-desc">{{ ev.description }}</span>
            </span>
            <span class="event-actions">
              <button class="btn btn-secondary btn-xs" @click="openEdit(ev)">Modifica</button>
              <button class="btn btn-danger btn-xs" @click="deleteEvent(ev.id)">Elimina</button>
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
          <label>Titolo *</label>
          <input v-model="form.title" required maxlength="200" />
        </div>
        <div class="form-group">
          <label>Tipo</label>
          <select v-model="form.event_type">
            <option value="training">Allenamento</option>
            <option value="race">Gara</option>
            <option value="recovery">Recupero</option>
            <option value="goal_deadline">Scadenza Obiettivo</option>
            <option value="test">Test</option>
            <option value="other">Altro</option>
          </select>
        </div>
        <div class="form-group">
          <label>Data</label>
          <input type="date" v-model="form.date" required />
        </div>
        <div class="form-group">
          <label>Durata (min)</label>
          <input type="number" v-model.number="form.duration_minutes" min="0" />
        </div>
        <div class="form-group full-width">
          <label>Descrizione</label>
          <textarea v-model="form.description" maxlength="1000" rows="3"></textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">Salva</button>
          <button type="button" class="btn btn-secondary" @click="showForm = false">Annulla</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { apiGet, apiPost, apiDelete, apiPut } from '../utils/api.js'

const athleteId = ref(1)
const athletes = ref([])
const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth())
const events = ref([])
const showForm = ref(false)
const editingEvent = ref(null)
const form = ref({ title: '', event_type: 'training', date: '', duration_minutes: 0, description: '', completed: false })
const athleteGoals = ref('')

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
  form.value = { title: '', event_type: 'training', date, duration_minutes: 0, description: '', completed: false }
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
  form.value = { title: obj.title, event_type: obj.event_type, date: dateStr, duration_minutes: obj.duration, description: obj.hint, completed: false }
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
    alert('Errore: ' + (e.message || e))
  }
}

async function deleteEvent(id) {
  if (!confirm('Eliminare questo evento?')) return
  try {
    await apiDelete(`/api/v1/calendar/events/${id}`)
    loadEvents()
  } catch (e) {
    alert('Errore: ' + (e.message || e))
  }
}

async function toggleComplete(ev) {
  try {
    await apiPost(`/api/v1/calendar/events/${ev.id}/complete`, {})
    loadEvents()
  } catch (e) {
    alert('Errore: ' + (e.message || e))
  }
}

onMounted(() => {
  loadAthletes()
  loadEvents()
  loadGoals()
})

watch(athleteId, () => {
  loadEvents()
  loadGoals()
})
</script>
