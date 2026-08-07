/**
 * Main domain types for the BikeMaster application.
 *
 * Defines interfaces for core entities: ride, athlete, summary,
 * training score, coach data, calendar event, badge, GPS point,
 * race segment, native GPS sampling and tracking instance.
 * Also includes global Window augmentation for native tracking.
 */
export interface Ride {
  id: number;
  athlete_id: number;
  title: string;
  date: string;
  duration_minutes: number;
  distance_km: number;
  calories?: number;
  avg_speed_kmh?: number;
  max_speed_kmh?: number;
  elevation_gain_m?: number;
  elev_loss_meters?: number;
  gps_points?: GpsPoint[];
  heart_rate_avg?: number;
  fatigue_score?: number;
  recovery_hours?: number;
  calories_per_km?: number;
  activity_type?: string;
  weight_kg?: number;
  is_official?: boolean;
  source?: string;
}

export interface EnrichedRide extends Ride {
  gps_points: GpsPoint[];
  center: { lat: number; lon: number } | null;
  segments: RideSegment[];
  distanceM: number;
  elevationGain: number;
  weather: { score?: number; description?: string } | null;
  weatherScore: number;
  weatherUnavailable: boolean;
  weatherError: string;
  overallRisk: number;
  maxRisk: number;
}

export interface Athlete {
  id?: number;
  username: string;
  email?: string | null;
  is_admin?: boolean;
  is_client?: boolean;
  tenant_id?: number;
  active_athlete_id?: number;
  goal_type?: string;
  goal_target?: number;
  goal_current?: number;
}

export interface Summary {
  rides: number;
  distance_km: number;
  calories: number;
  avg_speed_kmh: number;
  duration_minutes: number;
}

export interface TrainingScore {
  label: string;
  value: number;
}

export interface CoachData {
  training_scores: TrainingScore[];
  training_advice: string;
  historical_analysis?: string;
  recovery_advice: string;
}

export interface CalendarEvent {
  id: number;
  athlete_id: number;
  date: string;
  title: string;
  event_type:
    "training" | "race" | "recovery" | "goal_deadline" | "test" | "other";
  description?: string;
  completed?: boolean;
  duration_minutes?: number;
}

export interface Badge {
  id: number;
  athlete_id: number;
  badge_type: string;
  title: string;
  description: string;
  earned_at: string;
}

export interface GpsPoint {
  lat: number;
  lon: number;
  altitude?: number | null;
  timestamp?: string | null;
  speed?: number | null;
  timestampNumber?: number;
  elevation?: number | null;
  elevation_m?: number | null;
  heartRate?: number | null;
  cadence?: number | null;
  power?: number | null;
}

export interface RideSegment {
  start: [number, number];
  end: [number, number];
  distance_m: number;
  elevation_delta_m: number;
  grade: number;
  risk: number;
  color: string;
  speed?: number | null;
  gradeRisk?: number;
  weatherRisk?: number;
  speedRisk?: number;
}

export interface Itinerary {
  id: number;
  athlete_id?: number;
  tenant_id?: number;
  name: string;
  description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  total_km?: number | null;
  total_elevation_m?: number | null;
  created_at?: string | null;
}

export interface Stage {
  id: number;
  itinerary_id: number;
  stage_day?: number;
  title?: string | null;
  distance_km?: number | null;
  elevation_gain_m?: number | null;
  ride_id?: number | null;
  poi_id?: number | null;
  estimated_km?: number | null;
  estimated_elevation_m?: number | null;
  notes?: string | null;
  created_at?: string | null;
}

export interface NativeGpsSample {
  lat: number;
  lon: number;
  altitude?: number | null;
  timestamp: number;
  speed?: number | null;
}

export interface BikeTrackingInstance {
  startTracking?: () => Promise<void>;
  stopTracking?: () => void;
  pauseTracking?: () => Promise<void>;
  resumeTracking?: () => Promise<void>;
  checkPermissions?: () => Promise<{ granted: boolean }>;
  isTracking?: () => boolean;
  onPosition?: (cb: (sample: NativeGpsSample) => void) => void;
  onError?: (cb: (error: { code: number; message: string }) => void) => void;
}

declare global {
  interface Window {
    BikeTracking?: BikeTrackingInstance;
  }
}

export interface MetabolicProfile {
  athlete_id: number;
  sex: "male" | "female";
  bmr_formula: "mifflin" | "cunningham";
  activity_level: "sedentary" | "light" | "moderate" | "active" | "very_active";
  bmr_kcal?: number;
  tdee_kcal?: number;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface FoodLog {
  id?: number;
  athlete_id: number;
  tenant_id: number;
  date: string;
  meal_type: "breakfast" | "lunch" | "dinner" | "snack" | "other";
  description: string;
  kcal: number;
  carbs_g?: number | null;
  protein_g?: number | null;
  fat_g?: number | null;
  fiber_g?: number | null;
  water_ml?: number | null;
  note?: string | null;
  recorded_at?: string | null;
  created_at?: string | null;
}

export interface MetabolicDailySummary {
  id?: number;
  athlete_id: number;
  tenant_id: number;
  date: string;
  bmr_kcal: number;
  neat_kcal: number;
  eat_kcal: number;
  climb_bonus_kcal: number;
  tdee_kcal: number;
  intake_kcal: number;
  balance_kcal: number;
  steps_estimated?: number | null;
  elevation_gain_estimated_m?: number | null;
  rides_count: number;
  gps_neat_kcal: number;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface NutritionFoodItem {
  id?: number;
  tenant_id: number;
  name: string;
  category: string;
  kcal_per_100g: number;
  carbs_g_per_100g: number;
  protein_g_per_100g: number;
  fat_g_per_100g: number;
  fiber_g_per_100g: number;
  source: string;
  is_builtin: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PerformanceMetrics {
  id?: number;
  athlete_id: number;
  tenant_id?: number;
  ride_id?: number | null;
  date: string;
  average_power?: number | null;
  normalized_power?: number | null;
  intensity_factor?: number | null;
  tss?: number | null;
  ftp_watts?: number | null;
  created_at?: string | null;
}

export interface FtpRecord {
  id?: number;
  athlete_id: number;
  tenant_id?: number;
  date: string;
  ftp_watts: number;
  source?: string;
  note?: string | null;
  created_at?: string | null;
}

export interface FtpHistoryResponse {
  athlete_id: number;
  latest_ftp: number | null;
  history: FtpRecord[];
}

export interface PowerComputeResult {
  average_power: number | null;
  normalized_power: number | null;
  intensity_factor: number | null;
  tss: number | null;
}

export interface AthleteMetricLogEntry {
  id: number;
  value: number;
  unit: string | null;
  note: string | null;
  source: string;
  recorded_at: string;
}

export interface AthleteMetricLogResponse {
  metric_type: string;
  series: AthleteMetricLogEntry[];
}

export interface BeckAssessment {
  id?: number;
  athlete_id: number;
  tenant_id: number;
  total_score: number;
  severity: "minimal" | "mild" | "moderate" | "severe";
  answers: [number, number][];
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface BeckHistory {
  items: BeckAssessment[];
  latest: BeckAssessment | null;
  trend: {
    date?: string | null;
    score?: number | null;
    severity?: string | null;
  }[];
}

export type BeckItemScore = 0 | 1 | 2 | 3;
export type BeckItemOption = [string, BeckItemScore];

export interface Hr24hSample {
  id: number;
  heart_rate: number;
  source: string;
  device_id: string | null;
  recorded_at: string;
}

export interface Hr24hSettings {
  enabled: boolean;
  interval_seconds: number;
  source: string;
  device_id: string | null;
  max_hr: number | null;
  resting_hr: number | null;
}

export interface HrDailySummary {
  day: string;
  resting_hr: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  min_hr: number | null;
  sample_count: number;
}
