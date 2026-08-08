<!-- Componente grafico di base: wrapper che renderizza un grafico Chart.js su canvas tramite il composable useChart.
     Props: config (ChartConfiguration), height (es. "260px"), emptyLabel (testo se non ci sono dati), plugins (plugin Chart.js aggiuntivi).
     Eventi: nessuno. Espone "chart" via defineExpose. UI: contenitore con canvas, export menu opzionale e messaggio "nessun dato" sovrapposto se vuoto. -->
<template>
  <div class="base-chart" :style="{ height }">
    <canvas ref="canvas" />
    <p v-if="!hasData" class="base-chart__empty">
      {{ emptyLabel }}
    </p>
    <ChartExportMenu
      v-if="showExport && hasData"
      :chart="chart"
      :filename="exportFilename"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, toRef } from "vue";
import type { ChartConfiguration } from "../utils/chartTypes";
import { useChart } from "../composables/useChart";
import ChartExportMenu from "../components/charts/ChartExportMenu.vue";

const props = withDefaults(
  defineProps<{
    config: ChartConfiguration;
    height?: string;
    emptyLabel?: string;
    plugins?: any[];
    showExport?: boolean;
    exportFilename?: string;
  }>(),
  {
    height: "260px",
    emptyLabel: "Nessun dato",
    plugins: () => [],
    showExport: false,
    exportFilename: "chart",
  },
);

const configRef = toRef(props, "config");

const { canvas, chart } = useChart(configRef, props.plugins);

const hasData = computed(() => {
  const datasets = props.config?.data?.datasets;
  if (!datasets?.length) return false;
  return datasets.some((d) => Array.isArray(d.data) && d.data.length > 0);
});

defineExpose({ chart });
</script>

<style scoped>
.base-chart {
  position: relative;
  width: 100%;
}
.base-chart__empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.9rem;
  pointer-events: none;
}
</style>
