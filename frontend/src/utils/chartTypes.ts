/**
 * Minimal, dependency-free typings for the Chart.js configuration objects we
 * build. chart.js v4 ships its own declarations, but the installed package's
 * `types` entry points at a missing file, so we describe just what we use.
 */

export type ChartDataset = Record<string, any>;

export type ChartScales = Record<string, any>;

export type ChartPlugins = Record<string, any>;

export interface ChartConfiguration {
  type?:
    | "line"
    | "bar"
    | "pie"
    | "doughnut"
    | "radar"
    | "bubble"
    | "scatter"
    | "polarArea";
  data: {
    labels?: (string | number)[];
    datasets: ChartDataset[];
  };
  options?: {
    responsive?: boolean;
    maintainAspectRatio?: boolean;
    interaction?: Record<string, unknown>;
    plugins?: ChartPlugins;
    scales?: ChartScales;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface ChartOptions {
  responsive?: boolean;
  maintainAspectRatio?: boolean;
  interaction?: Record<string, unknown>;
  plugins?: ChartPlugins;
  scales?: ChartScales;
  [key: string]: unknown;
}
