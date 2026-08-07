import type { ChartConfiguration } from "../utils/chartTypes";
import { chartTheme } from "../utils/chartTheme";
import {
  baseScales,
  interactionDefaults,
  tooltipDefaults,
  DECIMATION_THRESHOLD,
} from "../utils/chartDefaults";

export interface UseLineChartOptions {
  label: string;
  data: number[];
  labels: string[];
  color?: string;
  fill?: boolean;
  tension?: number;
  unit?: string;
  pointRadius?: number;
  pointHoverRadius?: number;
  showRollingAvg?: boolean;
  rollingAvg?: number[];
  rollingWindow?: number;
}

export interface UseBarChartOptions {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    yAxisID?: string;
  }[];
  horizontal?: boolean;
}

export interface UseAreaChartOptions {
  datasets: {
    label: string;
    data: number[];
    borderColor: string;
    backgroundColor?: string;
    fill?: boolean;
    tension?: number;
    pointRadius?: number;
  }[];
  labels: string[];
}

export function useLineChart(opts: UseLineChartOptions): ChartConfiguration {
  const p = chartTheme.palette.value;
  const color = opts.color || p.accent;
  const datasets: ChartConfiguration["data"]["datasets"] = [
    {
      label: opts.label,
      data: opts.data,
      borderColor: color,
      backgroundColor:
        opts.fill !== false ? hexToRgba(color, 0.1) : "transparent",
      tension: opts.tension ?? 0.3,
      pointRadius: opts.pointRadius ?? 3,
      pointHoverRadius: opts.pointHoverRadius ?? 6,
    },
  ];

  if (opts.fill !== false) {
    (datasets[0] as any).fill = true;
  }

  if (opts.showRollingAvg && opts.rollingAvg?.length) {
    datasets.push({
      label: `Moving avg (${opts.rollingWindow ?? 7})`,
      data: opts.rollingAvg,
      borderColor: p.accent,
      backgroundColor: "transparent",
      borderDash: [5, 5],
      tension: 0.4,
      pointRadius: 0,
      fill: false,
    });
  }

  return {
    type: "line",
    data: {
      labels: opts.labels,
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: interactionDefaults(),
      plugins: {
        legend: {
          labels: { usePointStyle: true, color: p.textSecondary, padding: 16 },
        },
        tooltip: tooltipDefaults(),
      },
      scales: baseScales({
        x: { ticks: { maxTicksLimit: 12 } },
        y: {
          ticks: { color: p.textMuted },
          grid: { color: "rgba(255,255,255,0.06)" },
        },
      }),
    },
  } as ChartConfiguration;
}

export function useBarChart(opts: UseBarChartOptions): ChartConfiguration {
  return {
    type: "bar",
    data: {
      labels: opts.labels,
      datasets: opts.datasets.map((ds) => ({
        ...ds,
        backgroundColor: ds.backgroundColor || chartTheme.palette.value.accent,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: interactionDefaults(),
      plugins: {
        legend: { labels: { usePointStyle: true } },
        tooltip: tooltipDefaults(),
      },
      scales: baseScales(
        opts.datasets.length > 1
          ? {
              y: {
                position: "left",
                ticks: { color: opts.datasets[0]?.backgroundColor },
              },
              y1: {
                position: "right",
                grid: { display: false },
                ticks: { color: opts.datasets[1]?.backgroundColor },
              },
            }
          : {},
      ),
    },
  } as ChartConfiguration;
}

export function useAreaChart(opts: UseAreaChartOptions): ChartConfiguration {
  return {
    type: "line",
    data: {
      labels: opts.labels,
      datasets: opts.datasets.map((ds) => ({
        ...ds,
        fill: ds.fill ?? true,
        tension: ds.tension ?? 0.3,
        pointRadius: ds.pointRadius ?? 3,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: interactionDefaults(),
      plugins: {
        legend: { labels: { usePointStyle: true } },
        tooltip: tooltipDefaults(),
      },
      scales: baseScales(),
    },
  } as ChartConfiguration;
}

export function decimateData<T>(
  data: T[],
  _getValue: (item: T) => number,
): T[] {
  if (data.length <= DECIMATION_THRESHOLD) return data;
  const step = Math.ceil(data.length / DECIMATION_THRESHOLD);
  const result: T[] = [];
  for (let i = 0; i < data.length; i += step) {
    result.push(data[i]);
  }
  return result;
}

function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.substring(0, 2), 16);
  const g = parseInt(clean.substring(2, 4), 16);
  const b = parseInt(clean.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
