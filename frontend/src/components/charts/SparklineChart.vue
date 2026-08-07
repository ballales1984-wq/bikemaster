<!-- SparklineChart: mini grafico compatto per card e KPI.
     Props: data (array numerico), color, height (default 60px).
     UI: BaseChart con line chart minimale, senza assi/legend, solo linea e tooltip essenziale. -->
<template>
  <BaseChart :config="config" :height="height" empty-label="" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import BaseChart from "../BaseChart.vue";
import type { ChartConfiguration } from "../../utils/chartTypes";
import { chartTheme } from "../../utils/chartTheme";

const props = withDefaults(
  defineProps<{
    data: number[];
    color?: string;
    height?: string;
  }>(),
  {
    height: "60px",
    color: "#00ffcc",
  },
);

const p = chartTheme.palette.value;

const config = computed<ChartConfiguration>(() => {
  const color = props.color || p.accent;
  const labels = props.data.map((_, i) => i);
  return {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "",
          data: props.data,
          borderColor: color,
          backgroundColor: "transparent",
          tension: 0.3,
          pointRadius: 0,
          pointHoverRadius: 0,
          borderWidth: 1.5,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
      scales: {
        x: { display: false },
        y: { display: false },
      },
    },
  } as ChartConfiguration;
});
</script>
