<template>
  <section class="comparison-panel">
    <div class="panel">
      <h2>⚖️ Confronto Uscite</h2>

      <div class="select-row">
        <div class="select-group">
          <label>Uscita A</label>
          <select v-model="rideA" @change="onSelectChange" class="form-select">
            <option :value="null">Seleziona...</option>
            <option v-for="r in rides" :key="r.id" :value="r">
              {{ r.date }} — {{ fmt(r.distance_km) }} km
            </option>
          </select>
        </div>
        <button
          class="swap-btn"
          :disabled="!rideA || !rideB"
          title="Scambia"
          @click="swapRides"
        >
          ⇄
        </button>
        <div class="select-group">
          <label>Uscita B</label>
          <select v-model="rideB" @change="onSelectChange" class="form-select">
            <option :value="null">Seleziona...</option>
            <option v-for="r in rides" :key="r.id" :value="r">
              {{ r.date }} — {{ fmt(r.distance_km) }} km
            </option>
          </select>
        </div>
      </div>

      <div v-if="loading" class="skeleton-container">
        <div class="skeleton skeleton-card"
style="height: 120px"
/>
      </div>

      <div v-else-if="comparison.ready" class="comparison-grid">
        <div
v-for="m in metrics" class="comp-card"
:key="m.key"
>
          <div class="comp-label">
            {{ m.label }}
          </div>
          <div class="comp-values">
            <div
              class="comp-a"
              :class="{ winner: comparison.winners[m.key] === 'A' }"
            >
              <span class="comp-val">{{ m.format(comparison.a[m.key]) }}</span>
              <span
v-if="comparison.deltas[m.key] !== 0" class="comp-delta"
>
                {{ comparison.deltas[m.key] > 0 ? "+" : ""
                }}{{ comparison.deltas[m.key].toFixed(1) }}%
              </span>
            </div>
            <div class="comp-divider">vs</div>
            <div
              class="comp-b"
              :class="{ winner: comparison.winners[m.key] === 'B' }"
            >
              <span class="comp-val">{{ m.format(comparison.b[m.key]) }}</span>
              <span
v-if="comparison.deltas[m.key] !== 0" class="comp-delta"
>
                {{ comparison.deltas[m.key] < 0 ? "+" : ""
                }}{{ Math.abs(comparison.deltas[m.key]).toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>

        <div
v-if="verdict" class="verdict"
>
          <span class="verdict-icon">🏆</span>
          <span>{{ verdict }}</span>
        </div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-icon">⚖️</div>
        <div class="empty-title">Seleziona due uscite per confrontarle</div>
        <div class="empty-desc">
          Scegli dall'elenco le uscite che vuoi analizzare a confronto.
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { apiGet } from "../utils/api";

const rides = ref([]);
const rideA = ref(null);
const rideB = ref(null);
const loading = ref(false);

const metrics = [
  {
    key: "distance_km",
    label: "Distanza (km)",
    format: (v) => (v == null ? "—" : Number(v).toFixed(1)),
  },
  {
    key: "duration_minutes",
    label: "Durata (min)",
    format: (v) => (v == null ? "—" : Math.round(v)),
  },
  {
    key: "avg_speed_kmh",
    label: "Velocità media",
    format: (v) => (v == null ? "—" : Number(v).toFixed(1) + " km/h"),
  },
  {
    key: "elevation_gain_m",
    label: "Dislivello (m)",
    format: (v) => (v == null ? "—" : Math.round(v)),
  },
  {
    key: "calories",
    label: "Calorie",
    format: (v) => (v == null ? "—" : Math.round(v)),
  },
];

function fmt(v, dec = 1) {
  if (v == null || isNaN(Number(v))) return "—";
  return Number(v).toFixed(dec);
}

const comparison = computed(() => {
  if (!rideA.value || !rideB.value) return { ready: false };
  const a = rideA.value;
  const b = rideB.value;
  const deltas = {};
  const winners = {};
  for (const m of metrics) {
    const av = Number(a[m.key]) || 0;
    const bv = Number(b[m.key]) || 0;
    if (av === 0 && bv === 0) {
      deltas[m.key] = 0;
      winners[m.key] = "";
    } else if (av === 0) {
      deltas[m.key] = -100;
      winners[m.key] = "B";
    } else if (bv === 0) {
      deltas[m.key] = 100;
      winners[m.key] = "A";
    } else {
      deltas[m.key] = ((av - bv) / bv) * 100;
      winners[m.key] = av > bv ? "A" : "B";
    }
  }
  return { ready: true, a, b, deltas, winners };
});

const verdict = computed(() => {
  if (!comparison.value.ready) return "";
  const { winners } = comparison.value;
  let scoreA = 0,
    scoreB = 0;
  for (const k in winners) {
    if (winners[k] === "A") scoreA++;
    else if (winners[k] === "B") scoreB++;
  }
  if (scoreA === scoreB) return "Pareggio — uscite equivalenti";
  if (scoreA > scoreB) return `Uscita A Vincente (${scoreA}/${metrics.length})`;
  return `Uscita B Vincente (${scoreB}/${metrics.length})`;
});

function swapRides() {
  const tmp = rideA.value;
  rideA.value = rideB.value;
  rideB.value = tmp;
}

function onSelectChange() {
  // reactive
}

async function load() {
  loading.value = true;
  try {
    const all = [];
    let page = 1;
    const pageSize = 100;
    while (true) {
      const data = await apiGet("/api/v1/rides", { page, page_size: pageSize });
      const batch = data.rides || [];
      all.push(...batch);
      const total = typeof data.total === "number" ? data.total : all.length;
      if (batch.length === 0 || all.length >= total) break;
      page += 1;
    }
    rides.value = all;
  } catch (e) {
    console.error("load rides for comparison", e);
  } finally {
    loading.value = false;
  }
}

onMounted(() => load());
</script>

<style scoped>
.comparison-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.select-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.select-group {
  flex: 1;
  min-width: 200px;
}

.select-group label {
  display: block;
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-weight: 500;
  margin-bottom: 4px;
}

.form-select {
  width: 100%;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 0.9rem;
  font-family: inherit;
}

.swap-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.1rem;
  transition: var(--transition);
  flex-shrink: 0;
}

.swap-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.swap-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin-top: 8px;
}

.comp-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
}

.comp-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.comp-values {
  display: flex;
  align-items: center;
  gap: 12px;
}

.comp-a,
.comp-b {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.comp-val {
  font-size: 1.3rem;
  font-weight: 700;
  font-family: "Outfit", sans-serif;
  color: var(--text-primary);
}

.comp-a.winner .comp-val {
  color: var(--success);
}
.comp-b.winner .comp-val {
  color: var(--success);
}

.comp-delta {
  font-size: 0.72rem;
  color: var(--text-muted);
}

.comp-divider {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.verdict {
  grid-column: 1 / -1;
  text-align: center;
  padding: 14px;
  background: rgba(0, 255, 204, 0.08);
  border: 1px solid rgba(0, 255, 204, 0.2);
  border-radius: var(--radius-sm);
  color: var(--accent);
  font-weight: 600;
  font-size: 1rem;
}

.verdict-icon {
  margin-right: 8px;
}

.skeleton-container {
  margin-top: 15px;
}

.empty-state {
  text-align: center;
  padding: 30px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 8px;
}
.empty-title {
  font-size: 1rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.empty-desc {
  font-size: 0.85rem;
}
</style>
