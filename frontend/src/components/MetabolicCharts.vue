<template>
  <div class="metabolic-charts">
    <h3>Trend metabolico</h3>
    <AreaChart
      v-if="hasData"
      :labels="sortedDates"
      :datasets="areaDatasets"
      height="260px"
      empty-label="Nessun dato disponibile"
    />
    <p v-else class="empty">
      Registra alimentazione e attivita' per visualizzare i trend.
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import AreaChart from "./charts/AreaChart.vue";
import type { MetabolicDailySummary } from "../types/index";

const props = defineProps<{
  summaries: MetabolicDailySummary[];
}>();

const sorted = computed(() =>
  [...props.summaries]
    .filter((s) => s.date)
    .sort((a, b) => a.date.localeCompare(b.date)),
);

const hasData = computed(() => sorted.value.length > 0);

const sortedDates = computed(() => sorted.value.map((s) => s.date.slice(5)));

const areaDatasets = computed(() => {
  const s = sorted.value;
  return [
    {
      label: "TDEE",
      data: s.map((d) => d.tdee_kcal),
      borderColor: "#3b82f6",
      backgroundColor: "rgba(59,130,246,0.1)",
      tension: 0.3,
      pointRadius: 3,
    },
    {
      label: "Intake",
      data: s.map((d) => d.intake_kcal),
      borderColor: "#10b981",
      backgroundColor: "rgba(16,185,129,0.1)",
      tension: 0.3,
      pointRadius: 3,
    },
    {
      label: "Bilancio",
      data: s.map((d) => d.balance_kcal),
      borderColor: "#f59e0b",
      backgroundColor: "rgba(245,158,11,0.1)",
      tension: 0.3,
      pointRadius: 3,
    },
  ];
});
</script>

<style scoped>
.empty {
  color: var(--text-muted);
  font-size: 0.9rem;
}
</style>
