<template>
  <div class="panel fitness-chart-panel">
    <h2>📈 Fitness ATL / CTL / TSB</h2>
    <BaseChart
      :config="chartConfig"
      height="220px"
      empty-label="Nessun dato di carico disponibile"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ChartConfiguration } from "../../utils/chartTypes";
import BaseChart from "../BaseChart.vue";
import { chartTheme } from "../../utils/chartTheme";

interface FitnessData {
  date: string;
  atl: number;
  ctl: number;
  tsb: number;
}

const props = defineProps<{
  data: FitnessData[];
}>();

const labels = computed(() =>
  props.data.map((d) => {
    const dt = new Date(d.date);
    return `${dt.getDate()}/${dt.getMonth() + 1}`;
  }),
);

const chartConfig = computed<ChartConfiguration>(() => {
  const p = chartTheme.palette.value;
  return {
    type: "line",
    data: {
      labels: labels.value,
      datasets: [
        {
          label: "ATL (Fatica)",
          data: props.data.map((d) => d.atl),
          borderColor: p.efficiency,
          backgroundColor: "rgba(255,107,53,0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
        {
          label: "CTL (Fitness)",
          data: props.data.map((d) => d.ctl),
          borderColor: p.endurance,
          backgroundColor: "rgba(0,136,255,0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
        {
          label: "TSB (Forma)",
          data: props.data.map((d) => d.tsb),
          borderColor: p.performance,
          backgroundColor: "rgba(0,255,204,0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
    },
  } as ChartConfiguration;
});
</script>

<style scoped>
.fitness-chart-panel {
  position: relative;
  height: 260px;
}
</style>
