<script setup lang="ts">
import { reactive, ref } from "vue";
import { useBm2 } from "../composables/useBm2";
import type { Bm2Insight, Bm2ModelResult } from "../types/bm2";

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
      <label>
        Domanda
        <input v-model="form.question" type="text" placeholder="Es. Quanta energia consumo?" />
      </label>
      <div class="bm2-row">
        <label>Peso atleta (kg)<input v-model.number="form.weight" type="number" /></label>
        <label>Peso bici (kg)<input v-model.number="form.bikeWeight" type="number" /></label>
        <label>Pendenza (%)<input v-model.number="form.slope" type="number" /></label>
        <label>Punti GPS<input v-model.number="form.gpsPoints" type="number" min="2" /></label>
      </div>
      <label class="bm2-check">
        <input v-model="isSimulation" type="checkbox" /> Modalità simulazione ("what if")
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
          <dt>Affidabilità</dt><dd>{{ Math.round(r.confidence * 100) }}%</dd>
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
        Applica il motore fisico BM2 a una tua uscita salvata (per ID) per uno
        scenario "what if" o per validare la potenza stimata contro il power-meter.
      </p>
      <div class="bm2-row">
        <label>ID ride<input v-model.number="rideForm.rideId" type="number" min="1" /></label>
      </div>

      <fieldset class="bm2-fieldset">
        <legend>Scenario "what if"</legend>
        <div class="bm2-row">
          <label>Δ peso atleta (kg)<input v-model.number="rideForm.athleteWeightDelta" type="number" step="0.5" /></label>
          <label>Δ peso bici (kg)<input v-model.number="rideForm.bikeWeightDelta" type="number" step="0.5" /></label>
          <label>Δ pendenza (%)<input v-model.number="rideForm.slopeDelta" type="number" step="0.5" /></label>
          <label>CdA override<input v-model.number="rideForm.cdaOverride" type="number" step="0.01" placeholder="es. 0.30" /></label>
        </div>
        <button type="button" :disabled="loading || !rideForm.rideId" @click="onSimulateRide">
          {{ loading ? "Calcolo…" : "Simula sulla ride" }}
        </button>
      </fieldset>

      <fieldset class="bm2-fieldset">
        <legend>Validazione potenza (power-meter)</legend>
        <div class="bm2-row">
          <label>Peso bici (kg)<input v-model.number="rideForm.bikeWeight" type="number" step="0.1" /></label>
          <label>CdA<input v-model.number="rideForm.cda" type="number" step="0.01" /></label>
          <label>Crr<input v-model.number="rideForm.crr" type="number" step="0.001" /></label>
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
</style>
