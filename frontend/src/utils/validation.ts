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
    form.height_cm !== undefined &&
    form.height_cm !== null &&
    form.height_cm !== "" &&
    !isNaN(height) &&
    (height < ATHLETE_LIMITS.MIN_HEIGHT_CM ||
      height > ATHLETE_LIMITS.MAX_HEIGHT_CM)
  ) {
    errors.height_cm = `Altezza deve essere tra ${ATHLETE_LIMITS.MIN_HEIGHT_CM} e ${ATHLETE_LIMITS.MAX_HEIGHT_CM} cm`;
  }

  const fatPct = Number(form.fat_percentage);
  if (
    form.fat_percentage !== undefined &&
    form.fat_percentage !== null &&
    form.fat_percentage !== "" &&
    !isNaN(fatPct) &&
    (fatPct < ATHLETE_LIMITS.MIN_FAT_PCT || fatPct > ATHLETE_LIMITS.MAX_FAT_PCT)
  ) {
    errors.fat_percentage = `Massa grassa deve essere tra ${ATHLETE_LIMITS.MIN_FAT_PCT} e ${ATHLETE_LIMITS.MAX_FAT_PCT}%`;
  }

  const bodyWaterPct = Number(form.body_water_percentage);
  if (
    form.body_water_percentage !== undefined &&
    form.body_water_percentage !== null &&
    form.body_water_percentage !== "" &&
    !isNaN(bodyWaterPct) &&
    (bodyWaterPct < 0 || bodyWaterPct > 100)
  ) {
    errors.body_water_percentage = "Acqua corporea deve essere tra 0 e 100%";
  }

  const muscleMassPct = Number(form.muscle_mass_percentage);
  if (
    form.muscle_mass_percentage !== undefined &&
    form.muscle_mass_percentage !== null &&
    form.muscle_mass_percentage !== "" &&
    !isNaN(muscleMassPct) &&
    (muscleMassPct < 0 || muscleMassPct > 100)
  ) {
    errors.muscle_mass_percentage = "Massa muscolare % deve essere tra 0 e 100";
  }

  const bmr = Number(form.bmr_kcal);
  if (
    form.bmr_kcal !== undefined &&
    form.bmr_kcal !== null &&
    form.bmr_kcal !== "" &&
    !isNaN(bmr) &&
    (bmr < ATHLETE_LIMITS.MIN_BMR_KCAL || bmr > ATHLETE_LIMITS.MAX_BMR_KCAL)
  ) {
    errors.bmr_kcal = `Metabolismo basale deve essere tra ${ATHLETE_LIMITS.MIN_BMR_KCAL} e ${ATHLETE_LIMITS.MAX_BMR_KCAL} kcal`;
  }

  const fatMassKg = Number(form.fat_mass_kg);
  if (
    form.fat_mass_kg !== undefined &&
    form.fat_mass_kg !== null &&
    form.fat_mass_kg !== "" &&
    !isNaN(fatMassKg) &&
    (fatMassKg < 0 || fatMassKg > 300)
  ) {
    errors.fat_mass_kg = "Massa grassa corporea deve essere tra 0 e 300 kg";
  }

  const subFatKg = Number(form.subcutaneous_fat_kg);
  if (
    form.subcutaneous_fat_kg !== undefined &&
    form.subcutaneous_fat_kg !== null &&
    form.subcutaneous_fat_kg !== "" &&
    !isNaN(subFatKg) &&
    (subFatKg < ATHLETE_LIMITS.MIN_SUBCUTANEOUS_FAT_KG ||
      subFatKg > ATHLETE_LIMITS.MAX_SUBCUTANEOUS_FAT_KG)
  ) {
    errors.subcutaneous_fat_kg = `Grasso sottocutaneo deve essere tra ${ATHLETE_LIMITS.MIN_SUBCUTANEOUS_FAT_KG} e ${ATHLETE_LIMITS.MAX_SUBCUTANEOUS_FAT_KG} kg`;
  }

  const subFatPct = Number(form.subcutaneous_fat_percentage);
  if (
    form.subcutaneous_fat_percentage !== undefined &&
    form.subcutaneous_fat_percentage !== null &&
    form.subcutaneous_fat_percentage !== "" &&
    !isNaN(subFatPct) &&
    (subFatPct < ATHLETE_LIMITS.MIN_SUBCUTANEOUS_FAT_PCT ||
      subFatPct > ATHLETE_LIMITS.MAX_SUBCUTANEOUS_FAT_PCT)
  ) {
    errors.subcutaneous_fat_percentage = `Grasso sottocutaneo % deve essere tra ${ATHLETE_LIMITS.MIN_SUBCUTANEOUS_FAT_PCT} e ${ATHLETE_LIMITS.MAX_SUBCUTANEOUS_FAT_PCT}%`;
  }

  const visceralFatLevel = Number(form.visceral_fat_level);
  if (
    form.visceral_fat_level !== undefined &&
    form.visceral_fat_level !== null &&
    form.visceral_fat_level !== "" &&
    !isNaN(visceralFatLevel) &&
    (visceralFatLevel < ATHLETE_LIMITS.MIN_VISCERAL_FAT_LEVEL ||
      visceralFatLevel > ATHLETE_LIMITS.MAX_VISCERAL_FAT_LEVEL)
  ) {
    errors.visceral_fat_level = `Grasso viscerale deve essere tra ${ATHLETE_LIMITS.MIN_VISCERAL_FAT_LEVEL} e ${ATHLETE_LIMITS.MAX_VISCERAL_FAT_LEVEL}`;
  }

  const visceralFatPct = Number(form.visceral_fat_percentage);
  if (
    form.visceral_fat_percentage !== undefined &&
    form.visceral_fat_percentage !== null &&
    form.visceral_fat_percentage !== "" &&
    !isNaN(visceralFatPct) &&
    (visceralFatPct < ATHLETE_LIMITS.MIN_VISCERAL_FAT_PCT ||
      visceralFatPct > ATHLETE_LIMITS.MAX_VISCERAL_FAT_PCT)
  ) {
    errors.visceral_fat_percentage = `Grasso viscerale % deve essere tra ${ATHLETE_LIMITS.MIN_VISCERAL_FAT_PCT} e ${ATHLETE_LIMITS.MAX_VISCERAL_FAT_PCT}%`;
  }

  const visceralFatKg = Number(form.visceral_fat_kg);
  if (
    form.visceral_fat_kg !== undefined &&
    form.visceral_fat_kg !== null &&
    form.visceral_fat_kg !== "" &&
    !isNaN(visceralFatKg) &&
    (visceralFatKg < ATHLETE_LIMITS.MIN_VISCERAL_FAT_KG ||
      visceralFatKg > ATHLETE_LIMITS.MAX_VISCERAL_FAT_KG)
  ) {
    errors.visceral_fat_kg = `Grasso viscerale kg deve essere tra ${ATHLETE_LIMITS.MIN_VISCERAL_FAT_KG} e ${ATHLETE_LIMITS.MAX_VISCERAL_FAT_KG} kg`;
  }

  const muscleMassKg = Number(form.muscle_mass_kg);
  if (
    form.muscle_mass_kg !== undefined &&
    form.muscle_mass_kg !== null &&
    form.muscle_mass_kg !== "" &&
    !isNaN(muscleMassKg) &&
    (muscleMassKg < ATHLETE_LIMITS.MIN_MUSCLE_MASS_KG ||
      muscleMassKg > ATHLETE_LIMITS.MAX_MUSCLE_MASS_KG)
  ) {
    errors.muscle_mass_kg = `Massa muscolare deve essere tra ${ATHLETE_LIMITS.MIN_MUSCLE_MASS_KG} e ${ATHLETE_LIMITS.MAX_MUSCLE_MASS_KG} kg`;
  }

  const boneMassKg = Number(form.bone_mass_kg);
  if (
    form.bone_mass_kg !== undefined &&
    form.bone_mass_kg !== null &&
    form.bone_mass_kg !== "" &&
    !isNaN(boneMassKg) &&
    (boneMassKg < ATHLETE_LIMITS.MIN_BONE_MASS_KG ||
      boneMassKg > ATHLETE_LIMITS.MAX_BONE_MASS_KG)
  ) {
    errors.bone_mass_kg = `Massa ossea deve essere tra ${ATHLETE_LIMITS.MIN_BONE_MASS_KG} e ${ATHLETE_LIMITS.MAX_BONE_MASS_KG} kg`;
  }

  const proteinPct = Number(form.protein_percentage);
  if (
    form.protein_percentage !== undefined &&
    form.protein_percentage !== null &&
    form.protein_percentage !== "" &&
    !isNaN(proteinPct) &&
    (proteinPct < ATHLETE_LIMITS.MIN_PROTEIN_PCT ||
      proteinPct > ATHLETE_LIMITS.MAX_PROTEIN_PCT)
  ) {
    errors.protein_percentage = `Proteine % deve essere tra ${ATHLETE_LIMITS.MIN_PROTEIN_PCT} e ${ATHLETE_LIMITS.MAX_PROTEIN_PCT}%`;
  }

  const proteinKg = Number(form.protein_kg);
  if (
    form.protein_kg !== undefined &&
    form.protein_kg !== null &&
    form.protein_kg !== "" &&
    !isNaN(proteinKg) &&
    (proteinKg < ATHLETE_LIMITS.MIN_PROTEIN_KG ||
      proteinKg > ATHLETE_LIMITS.MAX_PROTEIN_KG)
  ) {
    errors.protein_kg = `Proteine kg deve essere tra ${ATHLETE_LIMITS.MIN_PROTEIN_KG} e ${ATHLETE_LIMITS.MAX_PROTEIN_KG} kg`;
  }

  const bodyAge = Number(form.body_age);
  if (
    form.body_age !== undefined &&
    form.body_age !== null &&
    form.body_age !== "" &&
    !isNaN(bodyAge) &&
    (bodyAge < ATHLETE_LIMITS.MIN_BODY_AGE ||
      bodyAge > ATHLETE_LIMITS.MAX_BODY_AGE)
  ) {
    errors.body_age = `Età corporea deve essere tra ${ATHLETE_LIMITS.MIN_BODY_AGE} e ${ATHLETE_LIMITS.MAX_BODY_AGE}`;
  }

  const apparentAge = Number(form.apparent_age);
  if (
    form.apparent_age !== undefined &&
    form.apparent_age !== null &&
    form.apparent_age !== "" &&
    !isNaN(apparentAge) &&
    (apparentAge < ATHLETE_LIMITS.MIN_APPARENT_AGE ||
      apparentAge > ATHLETE_LIMITS.MAX_APPARENT_AGE)
  ) {
    errors.apparent_age = `Età apparente deve essere tra ${ATHLETE_LIMITS.MIN_APPARENT_AGE} e ${ATHLETE_LIMITS.MAX_APPARENT_AGE}`;
  }

  const bmi = Number(form.bmi);
  if (
    form.bmi !== undefined &&
    form.bmi !== null &&
    form.bmi !== "" &&
    !isNaN(bmi) &&
    (bmi < ATHLETE_LIMITS.MIN_BMI || bmi > ATHLETE_LIMITS.MAX_BMI)
  ) {
    errors.bmi = `BMI deve essere tra ${ATHLETE_LIMITS.MIN_BMI} e ${ATHLETE_LIMITS.MAX_BMI}`;
  }

  const leanMass = Number(form.lean_body_mass_kg);
  if (
    form.lean_body_mass_kg !== undefined &&
    form.lean_body_mass_kg !== null &&
    form.lean_body_mass_kg !== "" &&
    !isNaN(leanMass) &&
    (leanMass < ATHLETE_LIMITS.MIN_LEAN_BODY_MASS_KG ||
      leanMass > ATHLETE_LIMITS.MAX_LEAN_BODY_MASS_KG)
  ) {
    errors.lean_body_mass_kg = `Massa magra deve essere tra ${ATHLETE_LIMITS.MIN_LEAN_BODY_MASS_KG} e ${ATHLETE_LIMITS.MAX_LEAN_BODY_MASS_KG} kg`;
  }

  const yearsActive = Number(form.years_active);
  if (
    form.years_active !== undefined &&
    form.years_active !== null &&
    form.years_active !== "" &&
    !isNaN(yearsActive) &&
    (yearsActive < 0 || yearsActive > 80)
  ) {
    errors.years_active = "Anni di attività deve essere tra 0 e 80";
  }

  const weeklySessions = Number(form.weekly_sessions);
  if (
    form.weekly_sessions !== undefined &&
    form.weekly_sessions !== null &&
    form.weekly_sessions !== "" &&
    !isNaN(weeklySessions) &&
    (weeklySessions < 0 || weeklySessions > 14)
  ) {
    errors.weekly_sessions = "Sessioni/settimana deve essere tra 0 e 14";
  }

  const monthlyHours = Number(form.monthly_hours);
  if (
    form.monthly_hours !== undefined &&
    form.monthly_hours !== null &&
    form.monthly_hours !== "" &&
    !isNaN(monthlyHours) &&
    monthlyHours < 0
  ) {
    errors.monthly_hours = "Ore/mese non può essere negativo";
  }

  const annualHours = Number(form.annual_hours);
  if (
    form.annual_hours !== undefined &&
    form.annual_hours !== null &&
    form.annual_hours !== "" &&
    !isNaN(annualHours) &&
    annualHours < 0
  ) {
    errors.annual_hours = "Ore/anno non può essere negativo";
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
