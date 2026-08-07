<!-- BarChart: componente specializzato per grafici a barre.
     Props: labels, datasets (array di {label, data, backgroundColor, yAxisID}), horizontal, height, emptyLabel.
     UI: BaseChart con config barre; mostra legend e assi duali se necessario. -->
<template>
  <BaseChart :config="config" :height="height" :empty-label="emptyLabel" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import BaseChart from "../BaseChart.vue";
import type { ChartConfiguration } from "../../utils/chartTypes";
import { useBarChart } from "../../composables/useChartConfig";

const props = withDefaults(
  defineProps<{
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      backgroundColor?: string | string[];
      yAxisID?: string;
    }[];
    height?: string;
    emptyLabel?: string;
  }>(),
  {
    height: "260px",
    emptyLabel: "Nessun dato",
  },
);

const config = computed<ChartConfiguration>(() =>
  useBarChart({
    labels: props.labels,
    datasets: props.datasets,
  }),
);
</script>
