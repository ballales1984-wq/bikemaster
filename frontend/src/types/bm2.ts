/** Tipi per l'integrazione BikeMaster 2.0 (motore knowledge/model-driven). */

export interface Bm2Quantity {
  value: number;
  unit: string;
  source?: string;
  precision?: number;
  confidence?: number;
}

export interface Bm2ModelResult {
  value: number;
  unit: string;
  formula: string;
  data_used: string[];
  precision: number;
  confidence: number;
  source: string;
  details?: Record<string, unknown>;
}

export interface Bm2Insight {
  concept: string;
  detail: string;
  severity: "info" | "note" | "warning" | "critical";
}

export interface Bm2SimulationDelta {
  [model: string]: number;
}

export interface Bm2Answer {
  question: string;
  models_used: string[];
  results: Record<string, Bm2ModelResult>;
  insights: Bm2Insight[];
  simulation: {
    baseline: Record<string, Bm2ModelResult>;
    scenario: Record<string, Bm2ModelResult>;
    deltas: Bm2SimulationDelta;
  } | null;
}

export interface Bm2AskPayload {
  question: string;
  athlete?: Record<string, unknown>;
  bike?: Record<string, unknown>;
  world?: Record<string, unknown>;
  gps_points?: Record<string, unknown>[];
  sensors?: Record<string, unknown>[];
  extra?: Record<string, unknown> | null;
}
