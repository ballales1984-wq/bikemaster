<template>
  <div class="metabolic-charts">
    <h3>Trend metabolico</h3>
    <BaseChart
      v-if="hasData"
      :config="chartConfig"
      height="260px"
      empty-label="Nessun dato disponibile"
    />
    <p v-else class="empty">Registra alimentazione e attivita' per visualizzare i trend.</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BaseChart from "./BaseChart.vue";
import type { ChartConfiguration } from "../utils/chartTypes";
import type { MetabolicDailySummary } from "../types/index";

const props = defineProps<{
  summaries: MetabolicDailySummary[];
}>();

const sorted = computed(() =>
  [...props.summaries]
    .filter((s) => s.date)
    .sort((a, b) => a.date.localeCompare(b.date))
);

const hasData = computed(() => sorted.value.length > 0);

const chartConfig = computed<ChartConfiguration>(() => ({
  type: "line",
  data: {
    labels: sorted.value.map((s) => s.date.slice(5)),
    datasets: [
      {
        label: "TDEE",
        data: sorted.value.map((s) => s.tdee_kcal),
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.1)",
        fill: true,
        tension: 0.3,
      },
      {
        label: "Intake",
        data: sorted.value.map((s) => s.intake_kcal),
        borderColor: "#10b981",
        backgroundColor: "rgba(16,185,129,0.1)",
        fill: true,
        tension: 0.3,
      },
      {
        label: "Bilancio",
        data: sorted.value.map((s) => s.balance_kcal),
        borderColor: "#f59e0b",
        backgroundColor: "rgba(245,158,11,0.1)",
        fill: true,
        tension: 0.3,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    scales: {
      y: {
        beginAtZero: false,
        grid: { color: "rgba(128,128,128,0.1)" },
      },
      x: {
        grid: { display: false },
      },
    },
    plugins: {
      legend: { labels: { usePointStyle: true } },
    },
  },
}));
</script>

<style scoped>
.empty {
  color: var(--text-muted);
  font-size: 0.9rem;
}
</style>
