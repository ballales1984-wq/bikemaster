/**
 * Tipi di dominio principale dell'applicazione BikeMaster.
 *
 * Definisce le interfacce per le entità core: corsa, atleta, summary,
 * training score, coach data, evento calendario, badge, punto GPS,
 * segmento di gara, campionamento GPS nativo e istanza di tracciamento.
 * Include anche l'augmentazione globale di Window per il tracking nativo.
 */
export interface Ride {
  id: number;
  athlete_id: number;
  name: string;
  date: string;
  duration_seconds: number;
  distance_meters: number;
  distance_km?: number;
  calories?: number;
  avg_speed_kmh?: number;
  max_speed_kmh?: number;
  elev_gain_meters?: number;
  elev_loss_meters?: number;
  elevation_gain_m?: number;
  created_at?: string;
  duration_minutes?: number;
  gps_points?: GpsPoint[];
  heart_rate_avg?: number;
  max_heart_rate?: number;
  fatigue_score?: number;
  recovery_hours?: number;
  calories_per_km?: number;
  title?: string;
  activity_type?: string;
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
  isDemo?: boolean;
}

export interface Athlete {
  id?: number;
  username: string;
  email?: string | null;
  is_admin?: boolean;
  is_client?: boolean;
  tenant_id?: number;
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
