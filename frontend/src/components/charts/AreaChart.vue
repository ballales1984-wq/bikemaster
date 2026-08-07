<!-- AreaChart: componente specializzato per grafici ad area multipla.
     Props: labels, datasets (array di {label, data, borderColor, backgroundColor, fill, tension, pointRadius}), height, emptyLabel.
     UI: BaseChart con linee e area riempita; utile per trend metabolici, zone, ecc. -->
<template>
  <BaseChart :config="config" :height="height" :empty-label="emptyLabel" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import BaseChart from "../BaseChart.vue";
import type { ChartConfiguration } from "../../utils/chartTypes";
import { useAreaChart } from "../../composables/useChartConfig";

const props = withDefaults(
  defineProps<{
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      borderColor: string;
      backgroundColor?: string;
      fill?: boolean;
      tension?: number;
      pointRadius?: number;
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
  useAreaChart({
    labels: props.labels,
    datasets: props.datasets,
  }),
);
</script>
