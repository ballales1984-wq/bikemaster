import {
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  watch,
  type Ref,
} from "vue";
import ChartConstructor from "chart.js/auto";
import { chartTheme } from "../utils/chartTheme";
import type { ChartConfiguration, ChartOptions } from "../utils/chartTypes";

export type { ChartConfiguration, ChartOptions };

export type ChartInstance = any;

/**
 * Reactive, theme-aware wrapper around a Chart.js instance.
 *
 * - (Re)creates the chart when `config` changes (deep watch).
 * - Re-themes axis/legend colors when the active light/dark theme changes.
 * - Observes the container resize so charts stay responsive inside flex/grid.
 * - Destroys the instance on unmount to avoid canvas/context leaks.
 */
export function useChart(config: Ref<ChartConfiguration>) {
  const canvas = ref<HTMLCanvasElement | null>(null);
  const chart = shallowRef<ChartInstance | null>(null);
  let observer: ResizeObserver | null = null;

  function buildConfig(): ChartConfiguration {
    return chartTheme.apply(config.value);
  }

  function render() {
    if (!canvas.value) return;
    const ctx = canvas.value.getContext("2d");
    if (!ctx) return;
    chart.value?.destroy();
    chart.value = new ChartConstructor(ctx, buildConfig());
  }

  function retheme() {
    if (!chart.value) return;
    const next = buildConfig();
    chart.value.config = next as ChartInstance["config"];
    chart.value.options = next.options as ChartInstance["options"];

    chart.value.update("none" as any);
  }

  watch(config, () => render(), { deep: true });

  watch(
    () => chartTheme.isDark.value,
    () => retheme(),
  );

  onMounted(() => {
    render();
    if (canvas.value?.parentElement && typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(() => chart.value?.resize());
      observer.observe(canvas.value.parentElement);
    }
  });

  onBeforeUnmount(() => {
    observer?.disconnect();
    observer = null;
    chart.value?.destroy();
    chart.value = null;
  });

  return { canvas, chart, render };
}
