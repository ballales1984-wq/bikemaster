<!-- Grafico fitness: linee ATL (fatica), CTL (fitness) e TSB (forma) nel tempo, basato sui dati di carico di allenamento.
     Props: data (array di {date, atl, ctl, tsb}). Eventi: nessuno. Usa AreaChart per il rendering del grafico a linee.
     UI: pannello con titolo e AreaChart 220px; label date formattate gg/mm; gestisce lo stato "nessun dato". -->
<template>
  <div class="panel fitness-chart-panel">
    <h2>Fitness ATL / CTL / TSB</h2>
    <AreaChart
      v-if="data.length"
      :labels="labels"
      :datasets="areaDatasets"
      height="220px"
      empty-label="Nessun dato di carico disponibile"
    />
    <BaseChart
      v-else
      :config="emptyConfig"
      height="220px"
      empty-label="Nessun dato di carico disponibile"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BaseChart from "../BaseChart.vue";
import AreaChart from "../../components/charts/AreaChart.vue";
import type { ChartConfiguration } from "../../utils/chartTypes";
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

const p = chartTheme.palette.value;

const areaDatasets = computed(() => [
  {
    label: "ATL (Fatica)",
    data: props.data.map((d) => d.atl),
    borderColor: p.efficiency,
    backgroundColor: "rgba(255,107,53,0.1)",
    tension: 0.3,
    pointRadius: 3,
  },
  {
    label: "CTL (Fitness)",
    data: props.data.map((d) => d.ctl),
    borderColor: p.endurance,
    backgroundColor: "rgba(0,136,255,0.1)",
    tension: 0.3,
    pointRadius: 3,
  },
  {
    label: "TSB (Forma)",
    data: props.data.map((d) => d.tsb),
    borderColor: p.performance,
    backgroundColor: "rgba(0,255,204,0.1)",
    tension: 0.3,
    pointRadius: 3,
  },
]);

const emptyConfig = computed<ChartConfiguration>(() => ({
  type: "line",
  data: { labels: [], datasets: [] },
  options: { responsive: true, maintainAspectRatio: false },
}));
</script>

<style scoped>
.fitness-chart-panel {
  position: relative;
  height: 260px;
}
</style>
