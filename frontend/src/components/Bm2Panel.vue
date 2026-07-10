<script setup lang="ts">
import { reactive, ref } from "vue";
import { useBm2 } from "../composables/useBm2";
import type { Bm2Insight, Bm2ModelResult } from "../types/bm2";

const { answer, loading, error, ask } = useBm2();

const form = reactive({
  question: "Quanta energia consumo in questo giro?",
  weight: 75,
  bikeWeight: 8,
  slope: 4,
  gpsPoints: 3,
});

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
    useBm2().simulate(payload);
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
</style>
