/**
 * Global constants for the BikeMaster app.
 *
 * Includes validation limits for rides and athletes, default map
 * coordinates and zoom, and color palettes for risk, grade,
 * speed and workout types.
 */

export const RIDE_LIMITS = {
  MIN_DISTANCE_KM: 0,
  MAX_DISTANCE_KM: 500,
  MIN_DURATION_MINUTES: 1,
  MAX_DURATION_MINUTES: 1440,
  MAX_SPEED_KMH: 150,
} as const;

export const ATHLETE_LIMITS = {
  MIN_AGE: 10,
  MAX_AGE: 100,
  MIN_WEIGHT_KG: 20,
  MAX_WEIGHT_KG: 300,
  MIN_HEIGHT_CM: 100,
  MAX_HEIGHT_CM: 250,
  MIN_FTP_W: 50,
  MAX_FTP_W: 500,
  MIN_FAT_PCT: 2,
  MAX_FAT_PCT: 60,
  MIN_SUBCUTANEOUS_FAT_KG: 0,
  MAX_SUBCUTANEOUS_FAT_KG: 100,
  MIN_SUBCUTANEOUS_FAT_PCT: 0,
  MAX_SUBCUTANEOUS_FAT_PCT: 100,
  MIN_VISCERAL_FAT_LEVEL: 1,
  MAX_VISCERAL_FAT_LEVEL: 59,
  MIN_VISCERAL_FAT_PCT: 0,
  MAX_VISCERAL_FAT_PCT: 100,
  MIN_VISCERAL_FAT_KG: 0,
  MAX_VISCERAL_FAT_KG: 50,
  MIN_MUSCLE_MASS_KG: 0,
  MAX_MUSCLE_MASS_KG: 120,
  MIN_BONE_MASS_KG: 0,
  MAX_BONE_MASS_KG: 20,
  MIN_PROTEIN_PCT: 0,
  MAX_PROTEIN_PCT: 100,
  MIN_PROTEIN_KG: 0,
  MAX_PROTEIN_KG: 100,
  MIN_BODY_AGE: 10,
  MAX_BODY_AGE: 100,
  MIN_APPARENT_AGE: 10,
  MAX_APPARENT_AGE: 100,
  MIN_BMI: 0,
  MAX_BMI: 100,
  MIN_LEAN_BODY_MASS_KG: 0,
  MAX_LEAN_BODY_MASS_KG: 300,
  MIN_BMR_KCAL: 500,
  MAX_BMR_KCAL: 10000,
} as const;

export const DEFAULT_MAP_CENTER = [45.4642, 9.19] as const;
export const DEFAULT_MAP_ZOOM = 11;
export const DEFAULT_RIDE_MAP_CENTER = [45.0, 9.0] as [number, number];
export const DEFAULT_RIDE_MAP_ZOOM = 13;

export const RISK_COLORS = {
  LOW: "#27ae60",
  MEDIUM: "#f1c40f",
  HIGH: "#e67e22",
  SEVERE: "#e74c3c",
} as const;

export const GRADE_COLORS = {
  FLAT: "#27ae60",
  MODERATE: "#f1c40f",
  STEEP: "#e67e22",
  VERY_STEEP: "#e74c3c",
} as const;

export const SPEED_COLORS = {
  SLOW: "#e74c3c",
  MEDIUM: "#f1c40f",
  FAST: "#27ae60",
} as const;

export const WORKOUT_COLORS = {
  ENDURANCE: "#3498db",
  THRESHOLD: "#e74c3c",
  SWEETSPOT: "#9b59b6",
  RECOVERY: "#2ecc71",
  OPENERS: "#f39c12",
  RACE: "#f39c12",
} as const;
