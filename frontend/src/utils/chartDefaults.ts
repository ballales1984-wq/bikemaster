import type { ChartOptions } from "./chartTypes";

export const AXIS_COLORS = {
  text: "rgba(255,255,255,0.6)",
  grid: "rgba(255,255,255,0.06)",
  gridStrong: "rgba(255,255,255,0.1)",
} as const;

export function baseScales(
  overrides: ChartOptions["scales"] = {},
): ChartOptions["scales"] {
  return {
    x: {
      ticks: { color: AXIS_COLORS.text, maxRotation: 0 },
      grid: { color: AXIS_COLORS.grid },
      ...(overrides?.x || {}),
    },
    y: {
      ticks: { color: AXIS_COLORS.text },
      grid: { color: AXIS_COLORS.gridStrong },
      ...(overrides?.y || {}),
    },
  };
}

export function interactionDefaults() {
  return {
    mode: "index" as const,
    intersect: false,
  };
}

export function tooltipDefaults() {
  return {
    mode: "index" as const,
    intersect: false,
    backgroundColor: "rgba(10,10,18,0.95)",
    titleColor: "rgba(255,255,255,0.95)",
    bodyColor: "rgba(255,255,255,0.8)",
    borderColor: "rgba(255,255,255,0.08)",
    borderWidth: 1,
    padding: 10,
    cornerRadius: 8,
    displayColors: true,
    boxPadding: 3,
  };
}

export const DEFAULT_HEIGHT = "260px";

export const DECIMATION_ENABLED = true;
export const DECIMATION_THRESHOLD = 500;
