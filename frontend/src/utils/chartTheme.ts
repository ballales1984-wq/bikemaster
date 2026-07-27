/**
 * Applicazione del tema ai grafici Chart.js, con colori concreti per tema.
 *
 * Reflects design tokens (light/dark) into concrete palettes, because Chart.js
 * non legge le variabili CSS dal contesto 2d. `apply` fonde i default sensibili
 * al tema in una configurazione senza sovrascrivere le opzioni del componente.
 * `mergeScales` applica colori di tick/griglia agli assi; un `MutationObserver`
 * sincronizza il tema al cambio della classe su `body`.
 */

import { computed, ref } from "vue";
import type { ChartConfiguration, ChartOptions } from "./chartTypes";

/**
 * Resolves the active theme from the `body.light-theme` / dark class.
 * Charts need concrete colors (not CSS `var(...)` strings, which Chart.js
 * cannot read from the 2d context), so we mirror the design tokens here and
 * fall back to computed styles when possible.
 */

const isDark = ref(!document.body.classList.contains("light-theme"));

function syncTheme() {
  isDark.value = !document.body.classList.contains("light-theme");
}

if (typeof MutationObserver !== "undefined") {
  const bodyObserver = new MutationObserver(syncTheme);
  bodyObserver.observe(document.body, {
    attributes: true,
    attributeFilter: ["class"],
  });
}

function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

const palette = computed(() => ({
  textSecondary: cssVar("--text-secondary", "#b0b5c1"),
  textMuted: cssVar("--text-muted", "#6e7687"),
  border: cssVar("--border", "rgba(255,255,255,0.08)"),
  grid: isDark.value ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
  gridStrong: isDark.value ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
  performance: cssVar("--color-performance", "#00ffcc"),
  endurance: cssVar("--color-endurance", "#0088ff"),
  efficiency: cssVar("--color-efficiency", "#ff6b35"),
  recovery: cssVar("--color-recovery", "#a855f7"),
  accent: cssVar("--accent", "#00ffcc"),
}));

/**
 * Merges theme-aware defaults into a Chart.js config without clobbering
 * component-provided options. Returns a fresh object so the chart instance
 * can be re-created cleanly on theme change. Functions (e.g. tick callbacks)
 * are preserved — we never JSON-serialize the config.
 */
function apply(config: ChartConfiguration): ChartConfiguration {
  const p = palette.value;
  const baseOpts = config.options || {};
  const legend = baseOpts.plugins?.legend || {};
  const tooltip = baseOpts.plugins?.tooltip || {};

  const mergedScales = mergeScales(baseOpts.scales, p);

  const options = {
    ...baseOpts,
    responsive: baseOpts.responsive ?? true,
    maintainAspectRatio: baseOpts.maintainAspectRatio ?? false,
    interaction: baseOpts.interaction ?? {
      mode: "index" as const,
      intersect: false,
    },
    plugins: {
      ...baseOpts.plugins,
      legend: {
        ...legend,
        labels: {
          color: p.textSecondary,
          usePointStyle: true,
          padding: 16,
          ...(legend.labels || {}),
        },
      },
      tooltip: {
        mode: "index" as const,
        intersect: false,
        ...tooltip,
      },
    },
    scales: mergedScales,
  } as ChartOptions;

  return {
    ...config,
    options,
  };
}

function mergeScales(
  existing: ChartOptions["scales"],
  p: { textMuted: string; grid: string; gridStrong: string },
): ChartOptions["scales"] {
  if (!existing) {
    const defaults: Record<string, Record<string, unknown>> = {
      x: {
        ticks: { color: p.textMuted, maxRotation: 0 },
        grid: { color: p.grid },
      },
      y: {
        ticks: { color: p.textMuted },
        grid: { color: p.gridStrong },
      },
    };
    return defaults as ChartOptions["scales"];
  }

  const result: Record<string, Record<string, unknown>> = {};
  for (const key of Object.keys(existing)) {
    const axis =
      (existing as Record<string, Record<string, unknown>>)[key] || {};
    result[key] = {
      ticks: { color: p.textMuted, ...(axis.ticks || {}) },
      grid: { color: p.grid, ...(axis.grid || {}) },
      ...axis,
    };
  }
  return result as ChartOptions["scales"];
}

export const chartTheme = {
  isDark,
  palette,
  apply,
};
