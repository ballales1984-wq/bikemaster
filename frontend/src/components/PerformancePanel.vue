<template>
  <div class="perf-panel">
    <section class="card">
      <h3>FTP &amp; Storico</h3>
      <div class="ftp-current">
        <span class="label">FTP attuale</span>
        <span class="value">{{
          latestFtp != null ? Math.round(latestFtp) + " W" : "—"
        }}</span>
      </div>

      <BaseChart
        :config="ftpChartConfig"
        :height="'240px'"
        empty-label="Nessun dato FTP"
      />

      <form class="ftp-form"
@submit.prevent="onRecord">
        <div class="field">
          <label for="ftp-watts">FTP (W)</label>
          <input
            id="ftp-watts"
            v-model.number="ftpWatts"
            type="number"
            min="1"
            max="2000"
            required
          />
        </div>
        <div class="field">
          <label for="ftp-date">Data</label>
          <input
id="ftp-date" v-model="ftpDate" type="date" />
        </div>
        <div class="field">
          <label for="ftp-source">Fonte</label>
          <select id="ftp-source"
v-model="ftpSource">
            <option value="test">Test</option>
            <option value="ride">Uscita</option>
            <option value="estimate">Stima</option>
          </select>
        </div>
        <button type="submit"
:disabled="saving">
          {{ saving ? "Salvo..." : "Registra FTP" }}
        </button>
      </form>

      <details class="estimate">
        <summary>Stima da test di soglia</summary>
        <form class="estimate-form"
@submit.prevent="onEstimate">
          <div class="field">
            <label for="test-power">Media potenza test (W)</label>
            <input
              id="test-power"
              v-model.number="testPower"
              type="number"
              min="1"
              required
            />
          </div>
          <div class="field">
            <label for="test-dur">Durata test (min)</label>
            <input
              id="test-dur"
              v-model.number="testDuration"
              type="number"
              min="1"
              step="0.5"
            />
          </div>
          <p v-if="estimatedFtp != null" class="estimate-result">
            FTP stimata: <strong>{{ Math.round(estimatedFtp) }} W</strong>
          </p>
          <button
type="submit" :disabled="saving">Calcola stima</button>
        </form>
      </details>

      <p v-if="error" class="error">
        {{ error }}
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import BaseChart from "./BaseChart.vue";
import type { ChartConfiguration } from "../utils/chartTypes";
import { usePerformanceStore } from "../stores/performance";

const store = usePerformanceStore();

const ftpWatts = ref<number>(250);
const ftpDate = ref<string>(new Date().toISOString().slice(0, 10));
const ftpSource = ref<string>("test");
const testPower = ref<number>(260);
const testDuration = ref<number>(20);
const estimatedFtp = ref<number | null>(null);

const latestFtp = computed(() => store.latestFtp);
const saving = computed(() => store.saving);
const error = computed(() => store.error);

const ftpChartConfig = computed<ChartConfiguration>(() => ({
  type: "line",
  data: {
    labels: store.ftpHistory.map((f) => f.date),
    datasets: [
      {
        label: "FTP (W)",
        data: store.ftpHistory.map((f) => f.ftp_watts),
        borderColor: "#4ecca3",
        backgroundColor: "rgba(78, 204, 163, 0.2)",
        fill: true,
        tension: 0.3,
        pointRadius: 4,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { title: { display: true, text: "Data" } },
      y: { title: { display: true, text: "Watt" }, beginAtZero: false },
    },
  },
}));

async function onRecord() {
  estimatedFtp.value = null;
  await store.recordFtp({
    ftp_watts: ftpWatts.value,
    date: ftpDate.value,
    source: ftpSource.value,
  });
}

async function onEstimate() {
  try {
    estimatedFtp.value = await store.estimateFtp({
      test_power: testPower.value,
      test_duration_min: testDuration.value,
    });
  } catch {
    estimatedFtp.value = null;
  }
}

onMounted(async () => {
  await store.fetchFtpHistory();
});
</script>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem 1.25rem;
}
h3 {
  margin: 0 0 0.75rem;
}
.ftp-current {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.ftp-current .label {
  color: var(--text-muted);
  font-size: 0.9rem;
}
.ftp-current .value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--accent, #4ecca3);
}
.ftp-form,
.estimate-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: flex-end;
  margin-top: 0.75rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.field label {
  font-size: 0.8rem;
  color: var(--text-muted);
}
.field input,
.field select {
  padding: 0.4rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
button {
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  border: none;
  background: var(--accent, #4ecca3);
  color: #04221a;
  font-weight: 600;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: default;
}
.estimate {
  margin-top: 1rem;
  font-size: 0.9rem;
}
.estimate-result {
  width: 100%;
  color: var(--text-muted);
}
.error {
  color: #b91c1c;
  margin-top: 0.5rem;
}
</style>
