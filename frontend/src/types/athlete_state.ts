/**
 * Tipi per lo stato di forma dell'atleta (fitness, fatigue, readiness).
 *
 * Espone AthleteState con i principali indicatori di training load
 * (ACWR, TSB, ATL, CTL, rischio sovrallenamento) e
 * AthleteStateResponse che incapsula lo stato calcolato.
 */
export interface AthleteState {
  athlete_id: number;
  computed_at: string;
  fatigue_score: number;
  readiness: number;
  acwr: number;
  tsb: number;
  atl: number;
  ctl: number;
  fitness: number;
  form: number;
  recovery_hours_needed: number;
  weekly_tss: number;
  monthly_tss: number;
  trend_7d: string;
  trend_30d: string;
  risk_indicators: string[];
  recommendation: string;
  risk_level: "ok" | "warning" | "high" | "block";
  is_overtraining_risk: boolean;
  is_fresh: boolean;
  is_ready_for_hard_effort: boolean;
}

export interface AthleteStateResponse {
  athlete_id: number;
  computed_at: string;
  state: AthleteState;
}
