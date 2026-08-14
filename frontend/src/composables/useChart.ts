/**
 * Reactive, theme-aware wrapper around Chart.js instances.
 * Recreates the chart on deep changes of `config`, applies the re-theme
 * (light/dark) and observes the container resize; destroys the instance
 * on unmount to avoid canvas/context leaks. Exposes `canvas`,
 * `chart` and `render`.
 */
import {
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  watch,
  type Ref,
} from "vue";
import ChartConstructor from "chart.js/auto";
import "chartjs-adapter-date-fns";
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
export function useChart(config: Ref<ChartConfiguration>, plugins: any[] = []) {
  const canvas = ref<HTMLCanvasElement | null>(null);
  const chart = shallowRef<ChartInstance | null>(null);
  let observer: ResizeObserver | null = null;

  function buildConfig(): ChartConfiguration {
    const cfg = chartTheme.apply(config.value);
    if (plugins.length) {
      cfg.options = {
        ...cfg.options,
        plugins: {
          ...((cfg.options?.plugins as Record<string, any>) || {}),
          ...(plugins as Record<string, any>),
        },
      } as ChartOptions;
    }
    return cfg;
  }

  let lastType = "";

  function render() {
    if (!canvas.value) return;
    const ctx = canvas.value.getContext("2d");
    if (!ctx) return;
    chart.value?.destroy();
    const next = buildConfig();
    chart.value = new ChartConstructor(ctx, next as any);
    lastType = next.type ?? "";
  }

  function retheme() {
    if (!chart.value) return;
    const next = buildConfig();
    chart.value.config = next as ChartInstance["config"];
    chart.value.options = next.options as ChartInstance["options"];

    chart.value.update("none" as any);
  }

  watch(
    config,
    () => {
      const next = buildConfig();
      const typeChanged = (next.type ?? "") !== lastType;
      if (typeChanged || !chart.value) {
        render();
        return;
      }
      chart.value.data = next.data;
      chart.value.options = next.options as ChartInstance["options"];
      chart.value.update("none" as any);
    },
    { deep: true },
  );

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
