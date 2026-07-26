<!-- Pannello BikeMaster 2.0: interfaccia del motore fisico/simulazione BM2. Permette domande ("energia consumata"),
     simulazioni "what if" e validazione potenza su una ride reale (per ID) contro il power-meter.
     Props: none. Events: none (uses useBm2 composable). UI: question/parameters form, results cards with formula/reliability,
     sezione "Analisi su ride reale" con scenari what-if e metriche di validazione (MAE, RMSE, R², bias). -->
<script setup lang="ts">
import { reactive, ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBm2 } from "../composables/useBm2";
import { useI18n } from "../composables/useI18n";
import { apiGet } from "../utils/api";
import type { Bm2Insight, Bm2ModelResult } from "../types/bm2";

const { t } = useI18n();

const {
  answer,
  rideSimulation,
  validation,
  loading,
  error,
  ask,
  simulate,
  simulateRide,
  validate,
} = useBm2();

const route = useRoute();
const router = useRouter();

const form = reactive({
  question: "Quanta energia consumo in questo giro?",
  weight: 75,
  bikeWeight: 8,
  slope: 4,
  gpsPoints: 3,
});

// Analisi avanzata su una ride reale del prodotto (per ride_id).
const rideForm = reactive({
  rideId: null as number | null,
  athleteWeightDelta: 0,
  bikeWeightDelta: 0,
  slopeDelta: 0,
  cdaOverride: null as number | null,
  bikeWeight: 8,
  cda: 0.4,
  crr: 0.005,
});

const rides = ref<Array<{ id: number; date: string; title: string; distance_km: number }>>([]);
const ridePickerOpen = ref(false);

async function loadRides() {
  try {
    const data = await apiGet<{ rides: Array<{ id: number; date: string; title: string; distance_km: number }> }>("/api/v1/rides?page_size=100");
    rides.value = data.rides || [];
  } catch {
    rides.value = [];
  }
}

function selectRide(rideId: number) {
  rideForm.rideId = rideId;
  ridePickerOpen.value = false;
}

onMounted(() => {
  loadRides();
  const qRideId = route.query.rideId;
  if (qRideId !== undefined) {
    rideForm.rideId = Number(qRideId);
  }
});

function buildOverride() {
  const override: Record<string, number> = {};
  if (rideForm.athleteWeightDelta)
    override.athlete_weight_delta_kg = rideForm.athleteWeightDelta;
  if (rideForm.bikeWeightDelta)
    override.bike_weight_delta_kg = rideForm.bikeWeightDelta;
  if (rideForm.slopeDelta) override.slope_delta_percent = rideForm.slopeDelta;
  if (rideForm.cdaOverride != null) override.cda_override = rideForm.cdaOverride;
  return override;
}

function onSimulateRide() {
  if (!rideForm.rideId) return;
  simulateRide({
    ride_id: rideForm.rideId,
    athlete: { weight: form.weight },
    bike: { weight: rideForm.bikeWeight },
    override: buildOverride(),
  });
}

function onValidate() {
  if (!rideForm.rideId) return;
  validate({
    ride_id: rideForm.rideId,
    bike: {
      weight: form.weight,
      bike_weight: rideForm.bikeWeight,
      cda: rideForm.cda,
      crr: rideForm.crr,
    },
  });
}

function comparisonList(): [string, number][] {
  return rideSimulation.value
    ? Object.entries(rideSimulation.value.comparison.deltas)
    : [];
}

function buildPayload() {
  const pts = [];
  for (let i = 0; i < form.gpsPoints; i++) {
    const frac = i / Math.max(1, form.gpsPoints - 1);
    pts.push({
      lat: 45.0 + frac * 0.005,
      lon: 9.0 + frac * 0.005,
      altitude: 200 + frac * 160,
      timestamp: `2026-07-10T08:${String(i * 10).padStart(2, "0")}:00Z`,
    });
  }
  return {
    question: form.question,
    athlete: { weight: form.weight, age: 34, experience_level: "Intermediate", max_hr: 190 },
    bike: { weight: form.bikeWeight },
    world: { surface: "asphalt", avg_slope: form.slope },
    gps_points: pts,
    sensors: [
      { heart_rate: 140, power: 180 },
      { heart_rate: 165, power: 240 },
    ],
  };
}

const isSimulation = ref(false);

function onSubmit() {
  const payload = buildPayload();
  if (isSimulation.value || /se\s|what if|simula|ipotizz/i.test(form.question)) {
    simulate(payload);
  } else {
    ask(payload);
  }
}

const severityClass: Record<Bm2Insight["severity"], string> = {
  info: "bm2-info",
  note: "bm2-note",
  warning: "bm2-warning",
  critical: "bm2-critical",
};

function resultList(): [string, Bm2ModelResult][] {
  return answer.value ? Object.entries(answer.value.results) : [];
}
</script>

<template>
  <section class="bm2-panel">
    <h2>BikeMaster 2.0 — Analisi</h2>
    <form class="bm2-form" @submit.prevent="onSubmit">
        <label>Domanda<input id="bm2-question" v-model="form.question" type="text" placeholder="Es. Quanta energia consumo?" /></label>
      <div class="bm2-row">
        <label>Peso atleta (kg)<input id="bm2-weight" v-model.number="form.weight" type="number" /></label>
        <label>Peso bici (kg)<input id="bm2-bike-weight" v-model.number="form.bikeWeight" type="number" /></label>
        <label>Pendenza (%)<input id="bm2-slope" v-model.number="form.slope" type="number" /></label>
        <label>Punti GPS<input id="bm2-gps-points" v-model.number="form.gpsPoints" type="number" min="2" /></label>
      </div>
      <label class="bm2-check">
        <input id="bm2-simulation" v-model="isSimulation" type="checkbox" /> Modalità simulazione ("what if")
      </label>
      <button type="submit" :disabled="loading">
        {{ loading ? "Analisi…" : "Analizza" }}
      </button>
      <p v-if="error" class="bm2-error">{{ error }}</p>
    </form>

    <div v-if="answer" class="bm2-results">
      <article v-for="[name, r] in resultList()" :key="name" class="bm2-card">
        <header>
          <strong>{{ name }}</strong>
          <span class="bm2-value">{{ r.value.toFixed(1) }} {{ r.unit }}</span>
        </header>
        <dl>
          <dt>Risultato</dt><dd>{{ r.value.toFixed(2) }} {{ r.unit }}</dd>
          <dt>Formula</dt><dd>{{ r.formula }}</dd>
          <dt>Dati usati</dt><dd>{{ r.data_used.join(", ") }}</dd>
          <dt>Precisione</dt><dd>±{{ r.precision.toFixed(2) }} {{ r.unit }}</dd>
          <dt>Reliability</dt><dd>{{ Math.round(r.confidence * 100) }}%</dd>
          <dt>Fonte</dt><dd>{{ r.source }}</dd>
        </dl>
      </article>

      <aside v-if="answer.insights.length" class="bm2-insights">
        <h3>Concetti</h3>
        <ul>
          <li v-for="(ins, i) in answer.insights" :key="i" :class="severityClass[ins.severity]">
            <strong>{{ ins.concept }}</strong> — {{ ins.detail }}
          </li>
        </ul>
      </aside>

      <aside v-if="answer.simulation" class="bm2-sim">
        <h3>Simulazione ("what if")</h3>
        <ul>
          <li v-for="(delta, model) in answer.simulation.deltas" :key="model">
            {{ model }}: {{ delta >= 0 ? "+" : "" }}{{ delta.toFixed(1) }}
          </li>
        </ul>
      </aside>
    </div>

    <hr class="bm2-divider" />

<section class="bm2-realride">
       <h3>Analisi su ride reale</h3>
       <p class="bm2-hint">
         Applica il motore fisico BM2 a una tua uscita salvata per uno
         scenario "what if" o per validare la potenza stimata contro il power-meter.
       </p>
       <div class="bm2-row">
         <label>{{ t("bm2.ridePickerLabel") }}
           <div class="ride-picker">
             <button
               type="button"
               class="picker-trigger"
               @click="ridePickerOpen = !ridePickerOpen"
             >
               {{ rideForm.rideId
                 ? (rides.find(r => r.id === rideForm.rideId)?.date || `Ride #${rideForm.rideId}`)
                 : "Seleziona una ride..." }}
             </button>
             <div v-if="ridePickerOpen" class="picker-dropdown">
               <div
                 v-for="ride in rides"
                 :key="ride.id"
                 class="picker-option"
                 :class="{ active: rideForm.rideId === ride.id }"
                 @click="selectRide(ride.id)"
               >
                 <span class="picker-date">{{ ride.date }}</span>
                 <span class="picker-title">{{ ride.title || `Ride #${ride.id}` }}</span>
                 <span class="picker-dist">{{ ride.distance_km?.toFixed(1) }} km</span>
               </div>
               <div v-if="rides.length === 0" class="picker-empty">
                 Nessuna ride disponibile
               </div>
             </div>
           </div>
         </label>
       </div>

       <fieldset class="bm2-fieldset">
         <legend>Scenario "what if"</legend>
         <div class="bm2-row">
           <label>Δ peso atleta (kg)<input id="bm2-athlete-weight-delta" v-model.number="rideForm.athleteWeightDelta" type="number" step="0.5" /></label>
           <label>Δ peso bici (kg)<input id="bm2-bike-weight-delta" v-model.number="rideForm.bikeWeightDelta" type="number" step="0.5" /></label>
           <label>Δ pendenza (%)<input id="bm2-slope-delta" v-model.number="rideForm.slopeDelta" type="number" step="0.5" /></label>
           <label>CdA override<input id="bm2-cda-override" v-model.number="rideForm.cdaOverride" type="number" step="0.01" placeholder="es. 0.30" /></label>
         </div>
         <button type="button" :disabled="loading || !rideForm.rideId" @click="onSimulateRide">
           {{ loading ? "Calcolo…" : "Simula sulla ride" }}
         </button>
       </fieldset>

       <fieldset class="bm2-fieldset">
         <legend>Validazione potenza (power-meter)</legend>
         <div class="bm2-row">
           <label>Peso bici (kg)<input id="bm2-real-bike-weight" v-model.number="rideForm.bikeWeight" type="number" step="0.1" /></label>
           <label>CdA<input id="bm2-real-cda" v-model.number="rideForm.cda" type="number" step="0.01" /></label>
           <label>Crr<input id="bm2-real-crr" v-model.number="rideForm.crr" type="number" step="0.001" /></label>
         </div>
         <button type="button" :disabled="loading || !rideForm.rideId" @click="onValidate">
           {{ loading ? "Calcolo…" : "Valida potenza" }}
         </button>
       </fieldset>

       <div v-if="rideSimulation" class="bm2-results">
         <h4>Scenario ride #{{ rideSimulation.ride_id }}</h4>
         <ul class="bm2-deltas">
           <li v-for="[model, delta] in comparisonList()" :key="model">
             {{ model }}:
             <span :class="delta >= 0 ? 'bm2-up' : 'bm2-down'">
               {{ delta >= 0 ? "+" : "" }}{{ delta.toFixed(2) }}
             </span>
           </li>
         </ul>
         <pre class="bm2-summary">{{ rideSimulation.summary }}</pre>
       </div>

       <div v-if="validation" class="bm2-results">
         <h4>Validazione ride #{{ validation.ride_id }}</h4>
         <dl class="bm2-valgrid">
           <dt>Punti</dt><dd>{{ validation.validation.n_points }}</dd>
           <dt>MAE</dt><dd>{{ validation.validation.mae_w.toFixed(1) }} W</dd>
           <dt>RMSE</dt><dd>{{ validation.validation.rmse_w.toFixed(1) }} W</dd>
           <dt>Bias</dt><dd>{{ validation.validation.bias_w.toFixed(1) }} W</dd>
           <dt>Potenza media misurata</dt><dd>{{ validation.validation.mean_measured_w.toFixed(1) }} W</dd>
           <dt>Potenza media stimata</dt><dd>{{ validation.validation.mean_estimated_w.toFixed(1) }} W</dd>
           <dt>R²</dt><dd>{{ validation.validation.r2.toFixed(3) }}</dd>
         </dl>
       </div>
     </section>
  </section>
</template>

<style scoped>
.bm2-panel { padding: 1rem; max-width: 920px; margin: 0 auto; }
.bm2-form { display: flex; flex-direction: column; gap: 0.75rem; }
.bm2-row { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.bm2-row label { flex: 1; min-width: 120px; display: flex; flex-direction: column; }
.bm2-card { border: 1px solid #2a3b34; border-radius: 8px; padding: 0.75rem; margin-top: 0.75rem; }
.bm2-card header { display: flex; justify-content: space-between; }
.bm2-value { font-weight: 700; }
.bm2-card dl { display: grid; grid-template-columns: 110px 1fr; gap: 2px 8px; margin: 0.5rem 0 0; font-size: 0.85rem; }
.bm2-card dt { color: #8aa; }
.bm2-error { color: #ff6b6b; }
.bm2-insights, .bm2-sim { margin-top: 1rem; }
.bm2-warning { color: #ffb454; }
.bm2-critical { color: #ff6b6b; }
.bm2-info { color: #4ecca3; }
.bm2-note { color: #9ad; }
.bm2-divider { border: none; border-top: 1px solid #2a3b34; margin: 1.5rem 0; }
.bm2-realride { margin-top: 0.5rem; }
.bm2-hint { color: #8aa; font-size: 0.85rem; margin: 0.25rem 0 0.75rem; }
.bm2-fieldset { border: 1px solid #2a3b34; border-radius: 8px; padding: 0.75rem; margin-top: 0.75rem; }
.bm2-fieldset legend { padding: 0 0.4rem; color: #9ad; font-size: 0.85rem; }
.bm2-fieldset button { margin-top: 0.75rem; }
.bm2-deltas { list-style: none; padding: 0; margin: 0.5rem 0; }
.bm2-up { color: #4ecca3; font-weight: 700; }
.bm2-down { color: #ff6b6b; font-weight: 700; }
.bm2-summary { background: #101c18; padding: 0.6rem; border-radius: 6px; font-size: 0.8rem; white-space: pre-wrap; overflow-x: auto; }
.bm2-valgrid { display: grid; grid-template-columns: 190px 1fr; gap: 2px 8px; font-size: 0.85rem; margin: 0.5rem 0 0; }
.bm2-valgrid dt { color: #8aa; }
 .ride-picker { position: relative; }
 .picker-trigger {
   background: var(--bg-tertiary);
   border: 1px solid var(--border);
   color: var(--text-primary);
   padding: 6px 10px;
   border-radius: var(--radius-sm);
   cursor: pointer;
   font-size: 0.85rem;
   width: 100%;
   text-align: left;
 }
 .picker-trigger:hover { border-color: var(--accent); }
 .picker-dropdown {
   position: absolute;
   top: 100%;
   left: 0;
   right: 0;
   max-height: 200px;
   overflow-y: auto;
   background: var(--bg-secondary);
   border: 1px solid var(--border);
   border-radius: var(--radius-sm);
   z-index: 10;
   margin-top: 2px;
 }
 .picker-option {
   display: flex;
   gap: 8px;
   padding: 6px 10px;
   cursor: pointer;
   font-size: 0.82rem;
   align-items: center;
 }
 .picker-option:hover { background: var(--bg-tertiary); }
 .picker-option.active { background: var(--accent-gradient); color: #000; }
 .picker-date { flex: 0 0 90px; color: var(--text-muted); }
 .picker-title { flex: 1; }
 .picker-dist { flex: 0 0 60px; text-align: right; color: var(--text-muted); }
 .picker-empty { padding: 8px 10px; color: var(--text-muted); font-size: 0.82rem; }
 </style>

