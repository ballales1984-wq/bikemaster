<template>
  <div class="base-chart"
:style="{ height }">
    <canvas ref="canvas" />
    <p v-if="!hasData"
class="base-chart__empty">
      {{ emptyLabel }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, toRef } from "vue";
import type { ChartConfiguration } from "../utils/chartTypes";
import { useChart } from "../composables/useChart";

const props = withDefaults(
  defineProps<{
    config: ChartConfiguration;
    height?: string;
    emptyLabel?: string;
  }>(),
  {
    height: "260px",
    emptyLabel: "No data",
  },
);

const configRef = toRef(props, "config");

const { canvas, chart } = useChart(configRef);

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
