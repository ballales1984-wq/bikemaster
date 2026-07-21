<!-- Admin BM2 Panel: backend-of-the-backend inspector for the BM2 scientific engine. Admin only. -->
<template>
  <div v-if="auth.isAdmin" class="admin-bm2">
    <h2>{{ t("admin.bm2.title") }}</h2>

    <div class="bm2-tabs">
      <button v-for="tab in tabs" :key="tab.key" :class="['bm2-tab', { active: activeTab === tab.key }]" @click="activeTab = tab.key">
        {{ t(tab.label) }}
      </button>
    </div>

    <!-- Catalog -->
    <section v-if="activeTab === 'catalog'" class="bm2-section">
      <h3>{{ t("admin.bm2.catalog") }}</h3>
      <div v-if="loadingCatalog" class="bm2-loading">{{ t("common.loading") }}</div>
      <div v-else class="bm2-catalog">
        <div v-for="model in catalog" :key="model.name" class="bm2-model-card">
          <header>
            <strong>{{ model.name }}</strong>
            <span class="bm2-unit">{{ model.unit }}</span>
          </header>
          <p class="bm2-desc">{{ model.description }}</p>
          <code class="bm2-formula">{{ model.formula }}</code>
          <div class="bm2-meta">
            <span>Inputs: {{ getModelInputs(model.name).join(", ") || "—" }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Live Test -->
    <section v-if="activeTab === 'test'" class="bm2-section">
      <h3>{{ t("admin.bm2.testEngine") }}</h3>
      <form class="bm2-form" @submit.prevent="runTest">
        <label class="bm2-full">
          Question
          <input id="abm2-question" v-model="testForm.question" type="text" />
        </label>
        <div class="bm2-row">
          <label>Weight (kg)<input id="abm2-weight" v-model.number="testForm.weight" type="number" /></label>
          <label>Age<input id="abm2-age" v-model.number="testForm.age" type="number" /></label>
          <label>FTP (W)<input id="abm2-ftp" v-model.number="testForm.ftp" type="number" /></label>
          <label>Experience
            <select id="abm2-exp" v-model="testForm.experience">
              <option>Beginner</option><option>Intermediate</option><option>Advanced</option><option>Elite</option>
            </select>
          </label>
        </div>
        <div class="bm2-row">
          <label>Bike weight (kg)<input id="abm2-bike" v-model.number="testForm.bikeWeight" type="number" /></label>
          <label>Crr<input id="abm2-crr" v-model.number="testForm.crr" type="number" step="0.001" /></label>
          <label>CdA<input id="abm2-cda" v-model.number="testForm.cda" type="number" step="0.01" /></label>
          <label>Surface
            <select id="abm2-surface" v-model="testForm.surface">
              <option>asphalt</option><option>gravel</option><option>mtb</option>
            </select>
          </label>
        </div>
        <div class="bm2-row">
          <label>Slope (%)<input id="abm2-slope" v-model.number="testForm.slope" type="number" /></label>
          <label>Wind (m/s)<input id="abm2-wind" v-model.number="testForm.wind" type="number" /></label>
          <label>Temp (°C)<input id="abm2-temp" v-model.number="testForm.temp" type="number" /></label>
        </div>
        <button type="submit" :disabled="testLoading">{{ testLoading ? t("common.loading") : t("admin.bm2.runTest") }}</button>
      </form>

      <div v-if="testResult" class="bm2-results">
        <div v-if="testResult.error" class="bm2-error">{{ testResult.error }}</div>
        <div v-else>
          <div class="bm2-models-used">
            <strong>{{ t("admin.bm2.modelsUsed") }}:</strong> {{ ((testResult.models_used as string[]) || []).join(", ") || "none" }}
          </div>
          <article v-for="[name, r] in resultList(testResult.results as Record<string, Bm2ModelResult>)" :key="name" class="bm2-card">
            <header>
              <strong>{{ name }}</strong>
              <span class="bm2-value">{{ (r as Bm2ModelResult).value.toFixed(1) }} {{ (r as Bm2ModelResult).unit }}</span>
            </header>
            <dl>
              <dt>Formula</dt><dd>{{ (r as Bm2ModelResult).formula }}</dd>
              <dt>Data used</dt><dd>{{ (r as Bm2ModelResult).data_used.join(", ") }}</dd>
              <dt>Precision</dt><dd>±{{ (r as Bm2ModelResult).precision.toFixed(2) }} {{ (r as Bm2ModelResult).unit }}</dd>
              <dt>Confidence</dt><dd>{{ Math.round((r as Bm2ModelResult).confidence * 100) }}%</dd>
              <dt>Source</dt><dd>{{ (r as Bm2ModelResult).source }}</dd>
              <template v-if="(r as Bm2ModelResult).details && Object.keys((r as Bm2ModelResult).details!).length">
                <dt>Details</dt>
                <dd v-for="(val, key) in (r as Bm2ModelResult).details" :key="key">{{ key }}: {{ formatDetail(val) }}</dd>
              </template>
            </dl>
          </article>
        </div>
      </div>
    </section>

    <!-- Simulation -->
    <section v-if="activeTab === 'simulation'" class="bm2-section">
      <h3>{{ t("admin.bm2.simulation") }}</h3>
      <form class="bm2-form" @submit.prevent="runSimulation">
        <label>Ride ID<input id="abm2-ride-id" v-model.number="simForm.rideId" type="number" min="1" /></label>
        <div class="bm2-row">
          <label>Δ athlete weight (kg)<input id="abm2-awd" v-model.number="simForm.athleteWeightDelta" type="number" step="0.5" /></label>
          <label>Δ bike weight (kg)<input id="abm2-bwd" v-model.number="simForm.bikeWeightDelta" type="number" step="0.5" /></label>
          <label>Δ slope (%)<input id="abm2-sd" v-model.number="simForm.slopeDelta" type="number" step="0.5" /></label>
          <label>CdA override<input id="abm2-cda" v-model.number="simForm.cdaOverride" type="number" step="0.01" /></label>
        </div>
        <button type="submit" :disabled="simLoading">{{ simLoading ? t("common.loading") : t("admin.bm2.runSimulation") }}</button>
      </form>
      <div v-if="simResult" class="bm2-results">
        <div v-if="simResult.error" class="bm2-error">{{ simResult.error }}</div>
        <div v-else>
          <h4>Ride #{{ simResult.ride_id }}</h4>
          <div class="bm2-comparison">
            <div v-for="[model, delta] in Object.entries(simResult.comparison.deltas)" :key="model" class="bm2-delta-row">
              <span>{{ model }}:</span>
              <span :class="delta >= 0 ? 'bm2-up' : 'bm2-down'">
                {{ delta >= 0 ? '+' : '' }}{{ delta.toFixed(2) }}
              </span>
            </div>
          </div>
          <pre class="bm2-summary">{{ simResult.summary }}</pre>
        </div>
      </div>
    </section>

    <!-- Constants -->
    <section v-if="activeTab === 'constants'" class="bm2-section">
      <h3>{{ t("admin.bm2.constants") }}</h3>
      <div class="bm2-constants">
        <div class="bm2-const-block">
          <h4>Physics</h4>
          <ul>
            <li><strong>G</strong> = 9.81 m/s²</li>
            <li><strong>RHO</strong> = 1.225 kg/m³</li>
          </ul>
        </div>
        <div class="bm2-const-block">
          <h4>Source Confidence</h4>
          <ul>
            <li v-for="(conf, src) in sourceConfidence" :key="src"><strong>{{ src }}</strong>: {{ conf }}</li>
          </ul>
        </div>
        <div class="bm2-const-block">
          <h4>Range Rules (DataQuality)</h4>
          <ul>
            <li v-for="(range, unit) in rangeRules" :key="unit"><strong>{{ unit }}</strong>: [{{ range[0] }}, {{ range[1] }}]</li>
          </ul>
        </div>
        <div class="bm2-const-block">
          <h4>Routing</h4>
          <ul>
            <li><strong>Threshold</strong>: {{ routeThreshold }}</li>
            <li><strong>Ambiguous keywords</strong>: {{ ambiguousKeywords.join(", ") }}</li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useI18n } from "../composables/useI18n";
import { apiGet, apiPost } from "../utils/api";
import type { Bm2ModelResult } from "../types/bm2";

const { t } = useI18n();
const auth = useAuthStore();

const tabs = [
  { key: "catalog", label: "admin.bm2.catalog" },
  { key: "test", label: "admin.bm2.testEngine" },
  { key: "simulation", label: "admin.bm2.simulation" },
  { key: "constants", label: "admin.bm2.constants" },
];
const activeTab = ref("catalog");

// --- Catalog ---
const catalog = ref<Array<{ name: string; formula: string; unit: string; description: string }>>([]);
const loadingCatalog = ref(false);
const modelInputs: Record<string, string[]> = {
  MovementModel: ["gps_points", "distanza", "durata", "speed"],
  EnergyModel: ["total_mass", "speed", "slope", "duration", "crr", "cda"],
  PerformanceModel: ["ftp", "intensity", "duration"],
  FatigueModel: ["fatica", "storico_attivita", "sonno_ore", "hrv"],
  RouteDifficultyModel: ["distanza", "dislivello", "pendenza", "experience_level"],
  RecoveryModel: ["fatica", "sonno_ore", "hrv", "storico_attivita"],
  NutritionModel: ["intensity", "duration", "massa_corpo"],
  PowerModel: ["speed", "slope", "massa_totale", "crr", "cda", "efficienza"],
  TrainingLoadModel: ["storico_attivita", "intensity", "duration"],
};

function getModelInputs(name: string): string[] {
  return modelInputs[name] || [];
}

async function loadCatalog() {
  loadingCatalog.value = true;
  try {
    const data = await apiGet<{ models: Array<{ name: string; formula: string; unit: string; description: string }> }>("/api/v1/bm2/models");
    catalog.value = data.models || [];
  } catch (e) {
    console.error("Failed to load BM2 catalog", e);
  } finally {
    loadingCatalog.value = false;
  }
}

// --- Test ---
const testLoading = ref(false);
const testResult = ref<Record<string, unknown> | null>(null);
const testForm = reactive({
  question: "Quanta energia consumo?",
  weight: 75,
  age: 34,
  ftp: 250,
  experience: "Intermediate",
  bikeWeight: 8,
  crr: 0.005,
  cda: 0.4,
  surface: "asphalt",
  slope: 4,
  wind: 0,
  temp: 20,
});

function buildTestPayload() {
  const pts = [];
  for (let i = 0; i < 3; i++) {
    const frac = i / 2;
    pts.push({
      lat: 45.0 + frac * 0.005,
      lon: 9.0 + frac * 0.005,
      altitude: 200 + frac * 160,
      timestamp: `2026-07-10T08:${String(i * 10).padStart(2, "0")}:00Z`,
    });
  }
  return {
    question: testForm.question,
    athlete: { weight: testForm.weight, age: testForm.age, ftp: testForm.ftp, experience_level: testForm.experience, max_hr: 190 },
    bike: { weight: testForm.bikeWeight, crr: testForm.crr, cda: testForm.cda, drivetrain_efficiency: 0.97 },
    world: { surface: testForm.surface, avg_slope: testForm.slope, wind_speed: testForm.wind, temperature: testForm.temp },
    gps_points: pts,
    sensors: [{ heart_rate: 140, power: 180 }, { heart_rate: 165, power: 240 }],
  };
}

async function runTest() {
  testLoading.value = true;
  testResult.value = null;
  try {
    const data = await apiPost("/api/v1/bm2/ask", buildTestPayload());
    testResult.value = data as Record<string, unknown>;
  } catch (e) {
    testResult.value = { error: e instanceof Error ? e.message : "Test failed" };
  } finally {
    testLoading.value = false;
  }
}

function resultList(results: Record<string, Bm2ModelResult> | undefined): [string, Bm2ModelResult][] {
  if (!results) return [];
  return Object.entries(results);
}

function formatDetail(val: unknown): string {
  if (typeof val === "number") return val.toFixed(2);
  return String(val);
}

// --- Simulation ---
const simLoading = ref(false);
const simResult = ref<{ ride_id: number | null; comparison: { deltas: Record<string, number> }; summary: string; error?: string } | null>(null);
const simForm = reactive({
  rideId: null as number | null,
  athleteWeightDelta: 0,
  bikeWeightDelta: 0,
  slopeDelta: 0,
  cdaOverride: null as number | null,
});

async function runSimulation() {
  if (!simForm.rideId) return;
  simLoading.value = true;
  simResult.value = null;
  try {
    const data = await apiPost("/api/v1/bm2/simulate-ride", {
      ride_id: simForm.rideId,
      override: {
        athlete_weight_delta_kg: simForm.athleteWeightDelta || undefined,
        bike_weight_delta_kg: simForm.bikeWeightDelta || undefined,
        slope_delta_percent: simForm.slopeDelta || undefined,
        cda_override: simForm.cdaOverride ?? undefined,
      },
      athlete: { weight: testForm.weight, age: testForm.age, ftp: testForm.ftp, experience_level: testForm.experience },
      bike: { weight: testForm.bikeWeight, crr: testForm.crr, cda: testForm.cda, drivetrain_efficiency: 0.97 },
      world: { surface: testForm.surface, avg_slope: testForm.slope, wind_speed: testForm.wind, temperature: testForm.temp },
    });
    simResult.value = data as { ride_id: number | null; comparison: { deltas: Record<string, number> }; summary: string };
  } catch (e) {
    simResult.value = { ride_id: null, comparison: { deltas: {} }, summary: "", error: e instanceof Error ? e.message : "Simulation failed" };
  } finally {
    simLoading.value = false;
  }
}

// --- Constants ---
const sourceConfidence: Record<string, number> = {
  power_meter: 0.95,
  hr_band: 0.8,
  hr_sensor: 0.85,
  gps: 0.85,
  "gps/dem": 0.75,
  baro: 0.8,
  manual: 0.8,
  scale: 0.9,
  dem: 0.7,
  estimate: 0.5,
};
const rangeRules: Record<string, [number, number]> = {
  kg: [20, 250],
  bpm: [20, 230],
  W: [0, 1500],
  "m/s": [0, 40],
  "%": [-40, 40],
  "°C": [-30, 50],
  "W/kg": [0, 30],
  Nm: [0, 100],
  mmHg: [300, 800],
  "g/L": [0.5, 2.0],
};
const routeThreshold = 0.5;
const ambiguousKeywords = [
  "everything", "complete", "general", "summary", "overview",
  "recap", "full analysis", "tell me everything", "explain everything",
];

onMounted(() => {
  loadCatalog();
});
</script>

<style scoped>
.admin-bm2 { display: flex; flex-direction: column; gap: 20px; }
.bm2-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.bm2-tab {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition);
}
.bm2-tab:hover { border-color: var(--accent); color: var(--text-primary); }
.bm2-tab.active { background: var(--accent-gradient); color: #000; font-weight: 600; }
.bm2-section { display: flex; flex-direction: column; gap: 12px; }
.bm2-loading { color: var(--text-muted); }
.bm2-catalog { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.bm2-model-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bm2-model-card header { display: flex; justify-content: space-between; align-items: center; }
.bm2-unit { font-size: 0.75rem; color: var(--accent); background: rgba(0,255,204,0.08); padding: 2px 8px; border-radius: 4px; }
.bm2-desc { font-size: 0.85rem; color: var(--text-secondary); margin: 0; }
.bm2-formula { font-size: 0.8rem; color: #8ad; background: var(--bg-tertiary); padding: 8px; border-radius: var(--radius-sm); display: block; white-space: pre-wrap; }
.bm2-meta { font-size: 0.75rem; color: var(--text-muted); }
.bm2-form { display: flex; flex-direction: column; gap: 0.75rem; }
.bm2-form label { display: flex; flex-direction: column; font-size: 0.85rem; color: var(--text-secondary); gap: 4px; }
.bm2-form input, .bm2-form select {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}
.bm2-full { flex: 1; }
.bm2-row { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.bm2-row label { flex: 1; min-width: 120px; }
.bm2-form button[type="submit"] {
  align-self: flex-start;
  background: var(--accent-gradient);
  color: #000;
  border: none;
  padding: 8px 18px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 600;
}
.bm2-form button[type="submit"]:disabled { opacity: 0.5; cursor: not-allowed; }
.bm2-results { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; }
.bm2-models-used { font-size: 0.9rem; color: var(--text-secondary); }
.bm2-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bm2-card header { display: flex; justify-content: space-between; }
.bm2-value { font-weight: 700; color: var(--accent); }
.bm2-card dl { display: grid; grid-template-columns: 110px 1fr; gap: 2px 8px; margin: 0; font-size: 0.82rem; }
.bm2-card dt { color: #8aa; }
.bm2-card dd { color: var(--text-secondary); }
.bm2-error { color: var(--error); font-size: 0.9rem; }
.bm2-comparison { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; }
.bm2-delta-row { display: flex; justify-content: space-between; padding: 6px 10px; background: var(--bg-tertiary); border-radius: var(--radius-sm); font-size: 0.85rem; }
.bm2-up { color: #4ecca3; font-weight: 700; }
.bm2-down { color: #ff6b6b; font-weight: 700; }
.bm2-summary { background: var(--bg-tertiary); padding: 10px; border-radius: var(--radius-sm); font-size: 0.8rem; white-space: pre-wrap; }
.bm2-constants { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.bm2-const-block {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
}
.bm2-const-block h4 { margin: 0 0 8px; font-size: 0.9rem; color: var(--accent); }
.bm2-const-block ul { margin: 0; padding-left: 18px; font-size: 0.82rem; color: var(--text-secondary); }
.bm2-const-block li { margin-bottom: 4px; }
</style>
