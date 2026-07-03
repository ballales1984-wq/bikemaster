<template>
  <div class="dashboard-panel">
    <!-- Header -->
    <div class="dash-header">
      <h2>📊 Dashboard</h2>
      <button class="btn btn-sm btn-secondary" @click="load" :disabled="loading">
        <span :class="{ spinner: loading }">{{ loading ? '' : '🔄' }}</span>
        {{ loading ? 'Aggiornamento...' : 'Aggiorna' }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading && !dashboard.summary" class="skeleton-grid">
      <div class="skeleton skeleton-card" v-for="i in 4" :key="i"></div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon">⚠️</div>
      <p>{{ error }}</p>
      <button class="btn btn-sm" @click="load">Riprova</button>
    </div>

    <template v-else>
      <!-- Score Rings -->
      <div class="score-row" v-if="dashboard.scores">
        <div class="score-ring" v-for="score in scoreCards" :key="score.label">
          <svg viewBox="0 0 80 80" class="ring-svg">
            <circle cx="40" cy="40" r="32" class="ring-bg"/>
            <circle
              cx="40" cy="40" r="32"
              class="ring-fill"
              :style="{ strokeDashoffset: ringOffset(score.value), stroke: score.color }"
              stroke-dasharray="201"
            />
          </svg>
          <div class="ring-label">
            <div class="ring-value" :style="{ color: score.color }">{{ score.value }}</div>
            <div class="ring-name">{{ score.label }}</div>
          </div>
        </div>
      </div>

      <!-- Main Grid -->
      <div class="dash-grid">
        <!-- Profile Card -->
        <div class="dash-card profile-card" v-if="dashboard.athlete">
          <div class="card-icon">👤</div>
          <div class="card-body">
            <div class="card-title">{{ dashboard.athlete.name || 'Atleta' }}</div>
            <div class="card-sub">{{ dashboard.athlete.experience_level || 'Livello N/D' }}</div>
            <div class="athlete-chips">
              <span class="chip" v-if="dashboard.athlete.weight_kg">{{ dashboard.athlete.weight_kg }} kg</span>
              <span class="chip" v-if="dashboard.athlete.ftp_watts">FTP {{ dashboard.athlete.ftp_watts }}W</span>
              <span class="chip" v-if="dashboard.athlete.age">{{ dashboard.athlete.age }} anni</span>
            </div>
          </div>
        </div>

        <!-- Stats Card -->
        <div class="dash-card stats-card" v-if="dashboard.summary">
          <div class="card-icon">🚴</div>
          <div class="card-body">
            <div class="card-title">Statistiche Globali</div>
            <div class="mini-stats">
              <div class="mini-stat">
                <span class="mini-val">{{ dashboard.summary.total_rides ?? 0 }}</span>
                <span class="mini-lbl">Uscite</span>
              </div>
              <div class="mini-stat">
                <span class="mini-val">{{ fmt(dashboard.summary.total_km) }}</span>
                <span class="mini-lbl">km totali</span>
              </div>
              <div class="mini-stat">
                <span class="mini-val">{{ fmt(dashboard.summary.total_hours, 1) }}h</span>
                <span class="mini-lbl">ore in sella</span>
              </div>
              <div class="mini-stat">
                <span class="mini-val">{{ fmt(dashboard.summary.total_calories, 0) }}</span>
                <span class="mini-lbl">kcal</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Fitness State -->
        <div class="dash-card fitness-card" v-if="dashboard.fitness">
          <div class="card-icon">📈</div>
          <div class="card-body">
            <div class="card-title">Fitness State</div>
            <div class="fitness-bars">
              <div class="fitness-bar-row">
                <span class="bar-label">ATL</span>
                <div class="bar-track"><div class="bar-fill atl" :style="{ width: barPct(dashboard.fitness.atl) + '%' }"></div></div>
                <span class="bar-val">{{ fmt(dashboard.fitness.atl) }}</span>
              </div>
              <div class="fitness-bar-row">
                <span class="bar-label">CTL</span>
                <div class="bar-track"><div class="bar-fill ctl" :style="{ width: barPct(dashboard.fitness.ctl) + '%' }"></div></div>
                <span class="bar-val">{{ fmt(dashboard.fitness.ctl) }}</span>
              </div>
              <div class="fitness-bar-row">
                <span class="bar-label">TSB</span>
                <div class="bar-track">
                  <div class="bar-fill tsb" :style="tsbStyle"></div>
                </div>
                <span class="bar-val" :class="{ positive: (dashboard.fitness.tsb ?? 0) >= 0, negative: (dashboard.fitness.tsb ?? 0) < 0 }">
                  {{ dashboard.fitness.tsb >= 0 ? '+' : '' }}{{ fmt(dashboard.fitness.tsb) }}
                </span>
              </div>
            </div>
            <div class="fitness-status" :class="statusClass">{{ dashboard.fitness.status || 'N/D' }}</div>
          </div>
        </div>

        <!-- Trends -->
        <div class="dash-card trends-card" v-if="dashboard.trends?.weekly_progress?.length">
          <div class="card-icon">📅</div>
          <div class="card-body">
            <div class="card-title">Ultimi 7 giorni</div>
            <div class="mini-chart">
              <div
                v-for="(km, i) in dashboard.trends.weekly_progress"
                :key="i"
                class="chart-bar"
                :style="{ height: chartBarH(km) + '%', background: km > 0 ? 'var(--accent)' : 'var(--border)' }"
                :title="km + ' km'"
              ></div>
            </div>
            <div class="chart-labels">
              <span v-for="d in dayLabels" :key="d" class="day-label">{{ d }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Rides -->
      <div class="dash-section" v-if="dashboard.recent_rides?.length">
        <h3>🕐 Uscite Recenti</h3>
        <div class="recent-rides">
          <div class="recent-ride" v-for="ride in dashboard.recent_rides" :key="ride.id">
            <div class="recent-ride-date">{{ formatDate(ride.date) }}</div>
            <div class="recent-ride-stats">
              <span>🛣️ {{ fmt(ride.distance_km) }} km</span>
              <span>⏱️ {{ ride.duration_minutes }} min</span>
              <span>⚡ {{ fmt(ride.avg_speed_kmh) }} km/h</span>
              <span v-if="ride.elevation_gain_m">⛰️ {{ fmt(ride.elevation_gain_m, 0) }}m</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!dashboard.summary && !loading" class="empty-state">
        <div class="empty-icon">📊</div>
        <div class="empty-title">Nessun dato disponibile</div>
        <div class="empty-desc">Importa le tue prime uscite per vedere la dashboard.</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiGet } from '../utils/api'

const dashboard = ref({})
const loading = ref(true)
const error = ref('')

const dayLabels = ['L', 'M', 'M', 'G', 'V', 'S', 'D']

const scoreCards = computed(() => {
  const s = dashboard.value.scores
  if (!s) return []
  return [
    { label: 'Performance', value: fmt(s.performance), color: '#00ffcc' },
    { label: 'Endurance', value: fmt(s.endurance), color: '#0088ff' },
    { label: 'Efficiency', value: fmt(s.efficiency), color: '#ff6b35' },
    { label: 'Recovery', value: fmt(s.recovery), color: '#a855f7' },
  ].filter(c => c.value !== '0.0' && c.value !== '—')
})

function fmt(v, dec = 1) {
  if (v == null || isNaN(Number(v))) return '0'
  return Number(v).toFixed(dec)
}

function ringOffset(val) {
  const pct = Math.min(Math.max(Number(val) / 10, 0), 1)
  return 201 - pct * 201
}

function barPct(val, max = 100) {
  return Math.min(Math.max((Number(val) / max) * 100, 0), 100)
}

const tsbStyle = computed(() => {
  const tsb = dashboard.value.fitness?.tsb ?? 0
  const pct = Math.min(Math.abs(tsb) / 50 * 50, 50)
  if (tsb >= 0) {
    return { width: pct + '%', marginLeft: '50%', background: 'var(--success)' }
  } else {
    return { width: pct + '%', marginLeft: (50 - pct) + '%', background: 'var(--error)' }
  }
})

const statusClass = computed(() => {
  const s = (dashboard.value.fitness?.status || '').toLowerCase()
  if (s.includes('fresh') || s.includes('form')) return 'status-good'
  if (s.includes('train') || s.includes('load')) return 'status-warn'
  if (s.includes('overtrain') || s.includes('fatigue')) return 'status-bad'
  return ''
})

function chartBarH(km) {
  const all = dashboard.value.trends?.weekly_progress ?? []
  const max = Math.max(...all, 1)
  return Math.max((km / max) * 100, 4)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString('it-IT', { day: '2-digit', month: 'short' })
  } catch { return dateStr }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await apiGet('/api/v1/dashboard')
    dashboard.value = data
  } catch (e) {
    error.value = 'Errore caricamento: ' + (e.message || e)
  } finally {
    loading.value = false
  }
}

onMounted(() => load().catch(e => { error.value = e.message }))
</script>

<style scoped>
.dashboard-panel {
  padding: 4px 0;
}

.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.dash-header h2 {
  color: var(--accent);
  font-size: 1.4rem;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

/* Skeleton */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.skeleton-grid .skeleton-card {
  height: 140px;
}

/* Score rings */
.score-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 28px;
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}

.score-ring {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
}

.ring-svg {
  width: 80px;
  height: 80px;
  transform: rotate(-90deg);
  animation: ringAppear 0.6s ease both;
}

.ring-svg:nth-child(1) { animation-delay: 0.05s; }
.ring-svg:nth-child(2) { animation-delay: 0.15s; }
.ring-svg:nth-child(3) { animation-delay: 0.25s; }
.ring-svg:nth-child(4) { animation-delay: 0.35s; }

.ring-bg {
  fill: none;
  stroke: var(--border);
  stroke-width: 6;
}

.ring-fill {
  fill: none;
  stroke-width: 6;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1);
}

.ring-label {
  text-align: center;
}

.ring-value {
  font-size: 1.1rem;
  font-weight: 700;
  font-family: 'Outfit', sans-serif;
}

.ring-name {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Main grid */
.dash-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.dash-card {
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  display: flex;
  gap: 14px;
  transition: var(--transition);
  position: relative;
  overflow: hidden;
}

.dash-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--accent-gradient);
  opacity: 0;
  transition: var(--transition);
}

.dash-card:hover { 
  box-shadow: var(--shadow-lg);
  border-color: var(--border-light);
}
.dash-card:hover::after { opacity: 1; }

.card-icon {
  font-size: 1.8rem;
  line-height: 1;
  flex-shrink: 0;
}

.card-body { flex: 1; min-width: 0; }

.card-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
  font-size: 0.95rem;
}

.card-sub {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-bottom: 8px;
}

/* Athlete chips */
.athlete-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.chip {
  background: rgba(0,255,204,0.1);
  border: 1px solid rgba(0,255,204,0.2);
  color: var(--accent);
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 500;
}

/* Mini stats */
.mini-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.mini-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mini-val {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'Outfit', sans-serif;
}

.mini-lbl {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Fitness bars */
.fitness-bars { display: flex; flex-direction: column; gap: 8px; }

.fitness-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  width: 28px;
  font-weight: 600;
  text-transform: uppercase;
}

.bar-track {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s ease;
}

.bar-fill.atl { background: linear-gradient(90deg, #ff6b35, #ff3366); }
.bar-fill.ctl { background: linear-gradient(90deg, #0088ff, #00ffcc); }
.bar-fill.tsb { position: absolute; top: 0; transition: all 0.8s ease; height: 100%; border-radius: 3px; }

.bar-val {
  font-size: 0.75rem;
  font-weight: 600;
  width: 36px;
  text-align: right;
  color: var(--text-secondary);
}
.bar-val.positive { color: var(--success); }
.bar-val.negative { color: var(--error); }

.fitness-status {
  margin-top: 10px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: inline-block;
  background: var(--bg-tertiary);
  color: var(--text-muted);
}
.status-good { background: rgba(0,255,204,0.15); color: var(--success); }
.status-warn { background: rgba(255,184,0,0.15); color: var(--warning); }
.status-bad  { background: rgba(255,51,102,0.15); color: var(--error); }

/* Mini chart */
.mini-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 50px;
  margin-top: 8px;
}

.chart-bar {
  flex: 1;
  border-radius: 3px 3px 0 0;
  min-height: 4px;
  transition: height 0.5s ease;
}

.chart-labels {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.day-label {
  flex: 1;
  font-size: 0.6rem;
  color: var(--text-muted);
  text-align: center;
}

/* Recent rides */
.dash-section h3 {
  color: var(--text-primary);
  font-size: 1rem;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.recent-rides {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recent-ride {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  transition: var(--transition);
}

.recent-ride:hover {
  border-color: var(--accent);
  transform: translateX(4px);
}

.recent-ride-date {
  font-weight: 600;
  color: var(--accent);
  font-size: 0.9rem;
  white-space: nowrap;
}

.recent-ride-stats {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.recent-ride-stats span {
  font-size: 0.85rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

@keyframes ringAppear {
  from { opacity: 0; transform: rotate(-90deg) scale(0.5); }
  to { opacity: 1; transform: rotate(-90deg) scale(1); }
}

@media (max-width: 768px) {
  .dash-grid {
    grid-template-columns: 1fr;
  }

  .score-row {
    justify-content: space-around;
  }

  .ring-svg { width: 70px; height: 70px; }

  .recent-ride {
    flex-direction: column;
    align-items: flex-start;
  }

  .recent-ride-stats { gap: 8px; }
}
</style>