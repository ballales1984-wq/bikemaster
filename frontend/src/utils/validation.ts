/**
 * Validazione dei form, in particolare dell'anagrafica atleta.
 *
 * `validateAthleteForm` restituisce una mappa campo→errore controllando nome,
 * email (regex), age/weight/height/volume/ftp within `ATHLETE_LIMITS` and
 * livello di esperienza ammesso. Riesporta gli helper `validateEmail`,
 * `validateRequired`, `validateNumber`, `validateExperienceLevel` e l'elenco
 * `VALID_EXPERIENCE_LEVELS`.
 */

import { ATHLETE_LIMITS } from "../constants";

const VALID_EXPERIENCE_LEVELS = [
  "Beginner",
  "Amateur",
  "Intermediate",
  "Advanced",
  "Elite",
];

function validateEmail(email: string): string | null {
  if (!email) return null;
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return "Formato email non valido";
  }
  return null;
}

function validateRequired(value: string, minLength = 1): string | null {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length < minLength) {
    return `Minimo ${minLength} caratteri`;
  }
  return null;
}

function validateNumber(
  value: number | string,
  min: number,
  max: number,
  fieldName = "",
): string | null {
  const num = typeof value === "string" ? Number(value) : value;
  if (isNaN(num)) return `${fieldName || "Valore"} non valido`;
  if (num < min) return `${fieldName || "Valore"} minimo: ${min}`;
  if (num > max) return `${fieldName || "Valore"} massimo: ${max}`;
  return null;
}

function validateExperienceLevel(level: string): string | null {
  if (!VALID_EXPERIENCE_LEVELS.includes(level)) {
    return `Livello non valido. Valori consentiti: ${VALID_EXPERIENCE_LEVELS.join(", ")}`;
  }
  return null;
}

export function validateAthleteForm(
  form: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {};

  const nameError = validateRequired(String(form.name || ""), 2);
  if (nameError) errors.name = nameError;

  const email = String(form.email || "");
  if (email) {
    const emailError = validateEmail(email);
    if (emailError) errors.email = emailError;
  }

  const age = Number(form.age);
  if (
    isNaN(age) ||
    age < ATHLETE_LIMITS.MIN_AGE ||
    age > ATHLETE_LIMITS.MAX_AGE
  ) {
    errors.age = `Age must be between ${ATHLETE_LIMITS.MIN_AGE} and ${ATHLETE_LIMITS.MAX_AGE}`;
  }

  const weight = Number(form.weight_kg);
  if (
    isNaN(weight) ||
    weight < ATHLETE_LIMITS.MIN_WEIGHT_KG ||
    weight > ATHLETE_LIMITS.MAX_WEIGHT_KG
  ) {
    errors.weight_kg = `Peso deve essere tra ${ATHLETE_LIMITS.MIN_WEIGHT_KG} e ${ATHLETE_LIMITS.MAX_WEIGHT_KG} kg`;
  }

  const height = Number(form.height_cm);
  if (
    !isNaN(height) &&
    (height < ATHLETE_LIMITS.MIN_HEIGHT_CM ||
      height > ATHLETE_LIMITS.MAX_HEIGHT_CM)
  ) {
    errors.height_cm = `Altezza deve essere tra ${ATHLETE_LIMITS.MIN_HEIGHT_CM} e ${ATHLETE_LIMITS.MAX_HEIGHT_CM} cm`;
  }

  const level = String(form.experience_level || "");
  if (level) {
    const levelError = validateExperienceLevel(level);
    if (levelError) errors.experience_level = levelError;
  }

  const weeklyVolume = Number(form.weekly_volume_km);
  if (
    form.weekly_volume_km !== undefined &&
    form.weekly_volume_km !== null &&
    form.weekly_volume_km !== "" &&
    isNaN(weeklyVolume)
  ) {
    errors.weekly_volume_km = "Volume settimanale non valido";
  }

  const ftp = Number(form.ftp_watts);
  if (
    form.ftp_watts !== undefined &&
    form.ftp_watts !== null &&
    form.ftp_watts !== "" &&
    !isNaN(ftp) &&
    (ftp < ATHLETE_LIMITS.MIN_FTP_W || ftp > ATHLETE_LIMITS.MAX_FTP_W)
  ) {
    errors.ftp_watts = `FTP deve essere tra ${ATHLETE_LIMITS.MIN_FTP_W} e ${ATHLETE_LIMITS.MAX_FTP_W} watt`;
  }

  return errors;
}

export {
  validateEmail,
  validateRequired,
  validateNumber,
  validateExperienceLevel,
  VALID_EXPERIENCE_LEVELS,
};
