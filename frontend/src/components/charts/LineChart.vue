<!-- LineChart: componente specializzato per grafici a linea.
     Props: labels, data, label, color, fill, tension, unit, height, emptyLabel.
     Supports rolling average via rollingAvg/rollingWindow.
     Exposes chart via defineExpose.
     UI: card con header e BaseChart; mostra KPI sopra il grafico se showKpi è true. -->
<template>
  <div class="line-chart">
    <div v-if="showKpi && hasData" class="line-chart__kpi">
      <span class="kpi-value">{{ kpiValue }}</span>
      <span class="kpi-label">{{ kpiLabel }}</span>
    </div>
    <BaseChart :config="config" :height="height" :empty-label="emptyLabel" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BaseChart from "../BaseChart.vue";
import type { ChartConfiguration } from "../../utils/chartTypes";
import { useLineChart } from "../../composables/useChartConfig";

const props = withDefaults(
  defineProps<{
    labels: string[];
    data: number[];
    label: string;
    color?: string;
    fill?: boolean;
    tension?: number;
    unit?: string;
    height?: string;
    emptyLabel?: string;
    showKpi?: boolean;
    rollingAvg?: number[];
    rollingWindow?: number;
  }>(),
  {
    color: "#00ffcc",
    fill: true,
    tension: 0.3,
    unit: "",
    height: "260px",
    emptyLabel: "Nessun dato",
    showKpi: false,
    rollingAvg: undefined,
    rollingWindow: 7,
  },
);

const config = computed<ChartConfiguration>(() =>
  useLineChart({
    label: props.label,
    data: props.data,
    labels: props.labels,
    color: props.color,
    fill: props.fill,
    tension: props.tension,
    unit: props.unit,
    showRollingAvg:
      props.rollingAvg !== undefined && props.rollingAvg.length > 0,
    rollingAvg: props.rollingAvg,
    rollingWindow: props.rollingWindow,
  }),
);

const hasData = computed(() => props.data.length > 0);

const kpiValue = computed(() => {
  if (!props.data.length) return "—";
  const last = props.data[props.data.length - 1];
  if (last == null) return "—";
  return Number(last).toFixed(1);
});

const kpiLabel = computed(() =>
  props.unit ? `${props.label} ${props.unit}` : props.label,
);
</script>

<style scoped>
.line-chart {
  width: 100%;
}
.line-chart__kpi {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.kpi-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--accent, #00ffcc);
  font-family: "Outfit", sans-serif;
}
.kpi-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>
