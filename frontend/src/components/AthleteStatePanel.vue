<template>
  <div class="athlete-state-panel" aria-label="Athlete State">
    <div class="panel-header">
      <h3>Stato Atleta</h3>
      <button
        class="refresh-btn"
        :disabled="loading"
        :aria-label="loading ? 'Updating' : 'Refresh state'"
        @click="refresh"
      >
        {{ loading ? "..." : "🔄" }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-else-if="!hasState" class="empty">
      <p>Nessuno stato disponibile. Effettua una uscita per calcolare il tuo stato.</p>
      <button class="action-btn" :disabled="loading" @click="refresh">
        Calcola stato
      </button>
    </div>

    <div v-else class="state-grid">
      <div class="metric-card" :class="riskClass">
        <div class="metric-value">{{ state.readiness }}%</div>
        <div class="metric-label">Readiness</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{{ state.fatigue_score.toFixed(1) }}</div>
        <div class="metric-label">Fatigue</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{{ state.ctl.toFixed(1) }}</div>
        <div class="metric-label">CTL (Fitness)</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{{ state.atl.toFixed(1) }}</div>
        <div class="metric-label">ATL (Fatigue)</div>
      </div>

      <div class="metric-card" :class="tsbClass">
        <div class="metric-value">{{ state.tsb.toFixed(1) }}</div>
        <div class="metric-label">TSB (Form)</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{{ state.acwr.toFixed(2) }}</div>
        <div class="metric-label">ACWR</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{{ state.recovery_hours_needed.toFixed(1) }}h</div>
        <div class="metric-label">Recovery</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{{ state.weekly_tss.toFixed(0) }}</div>
        <div class="metric-label">Weekly TSS</div>
      </div>
    </div>

    <div v-if="hasState" class="state-footer">
      <div class="risk-badge" :class="riskClass">{{ state.risk_level.toUpperCase() }}</div>
      <p class="recommendation">{{ state.recommendation }}</p>
      <div class="trends">
        <span class="trend">7d: {{ state.trend_7d }}</span>
        <span class="trend">30d: {{ state.trend_30d }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAthleteStateStore } from "../stores/athleteState";

const store = useAthleteStateStore();

const riskClass = {
  get() {
    return `risk-${store.riskLevel}`;
  },
};

const tsbClass = {
  get() {
    if (store.state && store.state.tsb > 15) return "tsb-fresh";
    if (store.state && store.state.tsb < -20) return "tsb-fatigued";
    return "";
  },
};

function refresh() {
  store.fetchState();
}
</script>

<style scoped>
.athlete-state-panel {
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin: 20px 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.refresh-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-primary);
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition);
}

.refresh-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  color: #ff6b6b;
  padding: 12px;
  border-radius: var(--radius-sm);
  background: rgba(255, 107, 107, 0.1);
}

.empty {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary);
}

.empty p {
  margin-bottom: 16px;
}

.action-btn {
  background: var(--accent-gradient);
  color: var(--bg-primary);
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}

.action-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-2px);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.state-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.metric-card {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  text-align: center;
  transition: var(--transition);
}

.metric-card:hover {
  border-color: var(--border-light);
  transform: translateY(-2px);
}

.metric-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  font-family: "Outfit", sans-serif;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.risk-ok {
  border-color: #4ade80;
}

.risk-warning {
  border-color: #facc15;
}

.risk-high {
  border-color: #fb923c;
}

.risk-block {
  border-color: #ef4444;
  animation: pulse 2s infinite;
}

.tsb-fresh {
  border-color: #4ade80;
}

.tsb-fatigued {
  border-color: #ef4444;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.state-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.risk-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.risk-badge.risk-ok {
  background: rgba(74, 222, 128, 0.15);
  color: #4ade80;
}

.risk-badge.risk-warning {
  background: rgba(250, 204, 21, 0.15);
  color: #facc15;
}

.risk-badge.risk-high {
  background: rgba(251, 146, 60, 0.15);
  color: #fb923c;
}

.risk-badge.risk-block {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.recommendation {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin: 8px 0;
}

.trends {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.trend {
  font-size: 0.8rem;
  color: var(--text-secondary);
  padding: 2px 8px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
}
</style>
