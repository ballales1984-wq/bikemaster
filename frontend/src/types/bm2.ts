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
  confidence?: number;
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

/** Payload per lo scenario "what if" su una ride reale del prodotto. */
export interface Bm2SimulateRidePayload {
  ride_id?: number | null;
  override?: Record<string, unknown>;
  athlete?: Record<string, unknown>;
  bike?: Record<string, unknown>;
  world?: Record<string, unknown>;
  gps_points?: Record<string, unknown>[];
}

export interface Bm2Comparison {
  baseline: Record<string, Bm2ModelResult>;
  scenario: Record<string, Bm2ModelResult>;
  deltas: Record<string, number>;
}

export interface Bm2SimulateRideResult {
  ride_id: number | null;
  comparison: Bm2Comparison;
  summary: string;
}

/** Payload per la validazione del kernel fisico contro i power-meter. */
export interface Bm2ValidatePayload {
  ride_id?: number | null;
  athlete?: Record<string, unknown>;
  bike?: Record<string, unknown>;
  world?: Record<string, unknown>;
  override?: Record<string, unknown>;
  gps_points?: Record<string, unknown>[];
}

export interface Bm2Validation {
  n_points: number;
  mae_w: number;
  rmse_w: number;
  bias_w: number;
  mean_measured_w: number;
  mean_estimated_w: number;
  r2: number;
}

export interface Bm2ValidateResult {
  ride_id: number | null;
  validation: Bm2Validation;
}

export interface Bm2CoachResultValidation {
  validation: Bm2Validation;
  ride_id: number;
}

export interface Bm2CoachResultAnswer {
  question: string;
  models_used: string[];
  results: Record<string, Bm2ModelResult>;
  insights: Bm2Insight[];
  confidence?: number;
  simulation: {
    baseline: Record<string, Bm2ModelResult>;
    scenario: Record<string, Bm2ModelResult>;
    deltas: Bm2SimulationDelta;
  } | null;
}

export type Bm2CoachResult = Bm2CoachResultValidation | Bm2CoachResultAnswer;

export interface Bm2CoachChatResponse {
  response: string;
  history: Array<Record<string, unknown>>;
  bm2_result: Bm2CoachResult | null;
}
