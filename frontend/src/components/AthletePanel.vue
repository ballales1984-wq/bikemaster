<!--
  Pannello profilo atleta: form di inserimento/modifica dati anagrafici e di allenamento dell'utente.
  Props: nessuna. Eventi: emit "toast" per notifiche. Carica l'atleta da /api/v1/athletes/me e salva via store.
  UI: input grid (name, age, weight, height, body fat, level, goals) with validation and Save button.
       Dopo il salvataggio mostra i grafici storici delle metriche tracciate.
-->
<template>
  <div class="panel">
    <h2>Profilo Atleta</h2>
    <AthleteSelector />
    <div v-if="isFirstLogin" class="welcome-banner">
      <span class="welcome-icon"></span> Benvenuto! Completa il tuo profilo per
      iniziare
    </div>
    <form id="athlete-form" class="form-grid" novalidate>
      <div class="form-group">
        <label for="athlete-name">Nome</label>
        <input
          id="athlete-name"
          v-model="form.name"
          type="text"
          required
          :class="{
            error: fieldErrors.name,
            valid: !fieldErrors.name && form.name.length >= 2,
          }"
        />
        <span v-if="fieldErrors.name" class="field-error">{{
          fieldErrors.name
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-age">Età</label>
        <input
          id="athlete-age"
          v-model.number="form.age"
          type="number"
          min="10"
          max="100"
          :class="{ error: fieldErrors.age, valid: !fieldErrors.age }"
        />
        <span v-if="fieldErrors.age" class="field-error">{{
          fieldErrors.age
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-weight">Peso (kg)</label>
        <input
          id="athlete-weight"
          v-model.number="form.weight_kg"
          type="number"
          min="20"
          max="300"
          step="0.1"
          :class="{
            error: fieldErrors.weight_kg,
            valid: !fieldErrors.weight_kg,
          }"
        />
        <span v-if="fieldErrors.weight_kg" class="field-error">{{
          fieldErrors.weight_kg
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-height">Altezza (cm)</label>
        <input
          id="athlete-height"
          v-model.number="form.height_cm"
          type="number"
          min="100"
          max="250"
          :class="{
            error: fieldErrors.height_cm,
            valid: !fieldErrors.height_cm,
          }"
        />
        <span v-if="fieldErrors.height_cm" class="field-error">{{
          fieldErrors.height_cm
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-fat">Massa Grassa (%)</label>
        <input
          id="athlete-fat"
          v-model.number="form.fat_percentage"
          type="number"
          min="2"
          max="60"
          step="0.1"
          :class="{
            error: fieldErrors.fat_percentage,
            valid: !fieldErrors.fat_percentage,
          }"
        />
        <span v-if="fieldErrors.fat_percentage" class="field-error">{{
          fieldErrors.fat_percentage
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-water">Acqua Corporea (%)</label>
        <input
          id="athlete-water"
          v-model.number="form.body_water_percentage"
          type="number"
          min="0"
          max="100"
          step="0.1"
          :class="{
            error: fieldErrors.body_water_percentage,
            valid: !fieldErrors.body_water_percentage,
          }"
        />
        <span v-if="fieldErrors.body_water_percentage" class="field-error">{{
          fieldErrors.body_water_percentage
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-muscle-pct">Massa Muscolare (%)</label>
        <input
          id="athlete-muscle-pct"
          v-model.number="form.muscle_mass_percentage"
          type="number"
          min="0"
          max="100"
          step="0.1"
          :class="{
            error: fieldErrors.muscle_mass_percentage,
            valid: !fieldErrors.muscle_mass_percentage,
          }"
        />
        <span v-if="fieldErrors.muscle_mass_percentage" class="field-error">{{
          fieldErrors.muscle_mass_percentage
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-bmr">Metabolismo Basale (kcal)</label>
        <input
          id="athlete-bmr"
          v-model.number="form.bmr_kcal"
          type="number"
          min="500"
          max="10000"
          step="1"
          :class="{
            error: fieldErrors.bmr_kcal,
            valid: !fieldErrors.bmr_kcal,
          }"
        />
        <span v-if="fieldErrors.bmr_kcal" class="field-error">{{
          fieldErrors.bmr_kcal
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-fat-mass">Massa Grassa Corporea (kg)</label>
        <input
          id="athlete-fat-mass"
          v-model.number="form.fat_mass_kg"
          type="number"
          min="0"
          max="300"
          step="0.1"
          :class="{
            error: fieldErrors.fat_mass_kg,
            valid: !fieldErrors.fat_mass_kg,
          }"
        />
        <span v-if="fieldErrors.fat_mass_kg" class="field-error">{{
          fieldErrors.fat_mass_kg
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-sub-fat">Grasso Sottocutaneo (%)</label>
        <input
          id="athlete-sub-fat"
          v-model.number="form.subcutaneous_fat_percentage"
          type="number"
          min="0"
          max="100"
          step="0.1"
          :class="{
            error: fieldErrors.subcutaneous_fat_percentage,
            valid: !fieldErrors.subcutaneous_fat_percentage,
          }"
        />
        <span
          v-if="fieldErrors.subcutaneous_fat_percentage"
          class="field-error"
          >{{ fieldErrors.subcutaneous_fat_percentage }}</span
        >
      </div>
      <div class="form-group">
        <label for="athlete-sub-fat-pct">Grasso Viscerale (%)</label>
        <input
          id="athlete-sub-fat-pct"
          v-model.number="form.visceral_fat_percentage"
          type="number"
          min="0"
          max="100"
          step="0.1"
          :class="{
            error: fieldErrors.visceral_fat_percentage,
            valid: !fieldErrors.visceral_fat_percentage,
          }"
        />
        <span v-if="fieldErrors.visceral_fat_percentage" class="field-error">{{
          fieldErrors.visceral_fat_percentage
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-muscle">Massa Muscolare (kg)</label>
        <input
          id="athlete-muscle"
          v-model.number="form.muscle_mass_kg"
          type="number"
          min="0"
          max="120"
          step="0.1"
          :class="{
            error: fieldErrors.muscle_mass_kg,
            valid: !fieldErrors.muscle_mass_kg,
          }"
        />
        <span v-if="fieldErrors.muscle_mass_kg" class="field-error">{{
          fieldErrors.muscle_mass_kg
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-bone">Massa Ossea (kg)</label>
        <input
          id="athlete-bone"
          v-model.number="form.bone_mass_kg"
          type="number"
          min="0"
          max="20"
          step="0.1"
          :class="{
            error: fieldErrors.bone_mass_kg,
            valid: !fieldErrors.bone_mass_kg,
          }"
        />
        <span v-if="fieldErrors.bone_mass_kg" class="field-error">{{
          fieldErrors.bone_mass_kg
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-protein-pct">Proteine (%)</label>
        <input
          id="athlete-protein-pct"
          v-model.number="form.protein_percentage"
          type="number"
          min="0"
          max="100"
          step="0.1"
          :class="{
            error: fieldErrors.protein_percentage,
            valid: !fieldErrors.protein_percentage,
          }"
        />
        <span v-if="fieldErrors.protein_percentage" class="field-error">{{
          fieldErrors.protein_percentage
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-body-age">Età Corporea</label>
        <input
          id="athlete-body-age"
          v-model.number="form.body_age"
          type="number"
          min="10"
          max="100"
          step="1"
          readonly
        />
        <span class="field-hint">Calcolata automaticamente</span>
      </div>
      <div class="form-group">
        <label for="athlete-apparent-age">Età Apparente</label>
        <input
          id="athlete-apparent-age"
          v-model.number="form.apparent_age"
          type="number"
          min="10"
          max="100"
          step="1"
          :class="{
            error: fieldErrors.apparent_age,
            valid: !fieldErrors.apparent_age,
          }"
        />
        <span v-if="fieldErrors.apparent_age" class="field-error">{{
          fieldErrors.apparent_age
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-bmi">BMI (IMC)</label>
        <input
          id="athlete-bmi"
          v-model.number="form.bmi"
          type="number"
          step="0.1"
          readonly
          :class="{
            error: fieldErrors.bmi,
            valid: !fieldErrors.bmi,
          }"
        />
        <span v-if="fieldErrors.bmi" class="field-error">{{
          fieldErrors.bmi
        }}</span>
        <span v-if="form.bmi" class="field-hint">{{ bmiInterpretation }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-lean-mass">Massa Corporea Magra (kg)</label>
        <input
          id="athlete-lean-mass"
          v-model.number="form.lean_body_mass_kg"
          type="number"
          min="0"
          max="300"
          step="0.1"
          :class="{
            error: fieldErrors.lean_body_mass_kg,
            valid: !fieldErrors.lean_body_mass_kg,
          }"
        />
        <span v-if="fieldErrors.lean_body_mass_kg" class="field-error">{{
          fieldErrors.lean_body_mass_kg
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-years">Anni di attività</label>
        <input
          id="athlete-years"
          v-model.number="form.years_active"
          type="number"
          min="0"
          max="80"
          :class="{
            error: fieldErrors.years_active,
            valid: !fieldErrors.years_active,
          }"
        />
        <span v-if="fieldErrors.years_active" class="field-error">{{
          fieldErrors.years_active
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-weekly">Sessioni/settimana</label>
        <input
          id="athlete-weekly"
          v-model.number="form.weekly_sessions"
          type="number"
          min="0"
          max="14"
          :class="{
            error: fieldErrors.weekly_sessions,
            valid: !fieldErrors.weekly_sessions,
          }"
        />
        <span v-if="fieldErrors.weekly_sessions" class="field-error">{{
          fieldErrors.weekly_sessions
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-monthly">Ore/mese</label>
        <input
          id="athlete-monthly"
          v-model.number="form.monthly_hours"
          type="number"
          min="0"
          step="0.5"
          :class="{
            error: fieldErrors.monthly_hours,
            valid: !fieldErrors.monthly_hours,
          }"
        />
        <span v-if="fieldErrors.monthly_hours" class="field-error">{{
          fieldErrors.monthly_hours
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-annual">Ore/anno</label>
        <input
          id="athlete-annual"
          v-model.number="form.annual_hours"
          type="number"
          min="0"
          step="0.5"
          :class="{
            error: fieldErrors.annual_hours,
            valid: !fieldErrors.annual_hours,
          }"
        />
        <span v-if="fieldErrors.annual_hours" class="field-error">{{
          fieldErrors.annual_hours
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-level">Livello</label>
        <select
          id="athlete-level"
          v-model="form.experience_level"
          :class="{
            error: fieldErrors.experience_level,
            valid: !fieldErrors.experience_level,
          }"
        >
          <option value="Beginner">Principiante</option>
          <option value="Amateur">Amatoriale</option>
          <option value="Intermediate">Intermedio</option>
          <option value="Advanced">Avanzato</option>
          <option value="Elite">Elite</option>
        </select>
        <span v-if="fieldErrors.experience_level" class="field-error">{{
          fieldErrors.experience_level
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-goals">Obiettivo</label>
        <input
          id="athlete-goals"
          v-model="form.goals"
          type="text"
          maxlength="500"
          placeholder="Gran Fondo, criterium, ecc."
        />
      </div>
    </form>
    <div class="form-actions">
      <button class="btn btn-primary" @click="save">Salva Profilo</button>
    </div>
    <div v-if="result" class="result-box">
      {{ result }}
    </div>

    <section v-if="athleteId" class="new-measurement">
      <h3>Inserisci Nuova Misurazione</h3>
      <p class="section-hint">
        Aggiungi un nuovo dato antropometrico. Il profilo verrà aggiornato e lo
        storico dei grafici si refresherà automaticamente.
      </p>
      <div class="form-grid">
        <div class="form-group">
          <label for="measurement-date">Data</label>
          <input id="measurement-date" v-model="measurementDate" type="date" />
        </div>
        <div class="form-group">
          <label for="measurement-weight">Peso (kg)</label>
          <input
            id="measurement-weight"
            v-model.number="measurement.weight_kg"
            type="number"
            min="20"
            max="300"
            step="0.1"
            placeholder="Es. 68"
          />
        </div>
        <div class="form-group">
          <label for="measurement-fat">Massa Grassa (%)</label>
          <input
            id="measurement-fat"
            v-model.number="measurement.fat_percentage"
            type="number"
            min="2"
            max="60"
            step="0.1"
            placeholder="Es. 22.3"
          />
        </div>
        <div class="form-group">
          <label for="measurement-water">Acqua Corporea (%)</label>
          <input
            id="measurement-water"
            v-model.number="measurement.body_water_percentage"
            type="number"
            min="0"
            max="100"
            step="0.1"
            placeholder="Es. 53.4"
          />
        </div>
        <div class="form-group">
          <label for="measurement-muscle-pct">Massa Muscolare (%)</label>
          <input
            id="measurement-muscle-pct"
            v-model.number="measurement.muscle_mass_percentage"
            type="number"
            min="0"
            max="100"
            step="0.1"
            placeholder="Es. 53.4"
          />
        </div>
        <div class="form-group">
          <label for="measurement-bmr">Metabolismo Basale (kcal)</label>
          <input
            id="measurement-bmr"
            v-model.number="measurement.bmr_kcal"
            type="number"
            min="500"
            max="10000"
            step="1"
            placeholder="Es. 1465"
          />
        </div>
        <div class="form-group">
          <label for="measurement-fat-mass">Massa Grassa Corporea (kg)</label>
          <input
            id="measurement-fat-mass"
            v-model.number="measurement.fat_mass_kg"
            type="number"
            min="0"
            max="300"
            step="0.1"
            placeholder="Es. 52.8"
          />
        </div>
        <div class="form-group">
          <label for="measurement-sub-fat">Grasso Sottocutaneo (%)</label>
          <input
            id="measurement-sub-fat"
            v-model.number="measurement.subcutaneous_fat_percentage"
            type="number"
            min="0"
            max="100"
            step="0.1"
            placeholder="Es. 15.1"
          />
        </div>
        <div class="form-group">
          <label for="measurement-visceral-fat">Grasso Viscerale (%)</label>
          <input
            id="measurement-visceral-fat"
            v-model.number="measurement.visceral_fat_percentage"
            type="number"
            min="0"
            max="100"
            step="0.1"
            placeholder="Es. 9.9"
          />
        </div>
        <div class="form-group">
          <label for="measurement-muscle">Massa Muscolare (kg)</label>
          <input
            id="measurement-muscle"
            v-model.number="measurement.muscle_mass_kg"
            type="number"
            min="0"
            max="120"
            step="0.1"
            placeholder="Es. 49.5"
          />
        </div>
        <div class="form-group">
          <label for="measurement-bone">Massa Ossea (kg)</label>
          <input
            id="measurement-bone"
            v-model.number="measurement.bone_mass_kg"
            type="number"
            min="0"
            max="20"
            step="0.1"
            placeholder="Es. 8.5"
          />
        </div>
        <div class="form-group">
          <label for="measurement-protein">Proteine (%)</label>
          <input
            id="measurement-protein"
            v-model.number="measurement.protein_percentage"
            type="number"
            min="0"
            max="100"
            step="0.1"
            placeholder="Es. 20.3"
          />
        </div>
        <div class="form-group">
          <label for="measurement-ftp">FTP (watt)</label>
          <input
            id="measurement-ftp"
            v-model.number="measurement.ftp_watts"
            type="number"
            min="50"
            max="500"
            step="1"
            placeholder="Es. 250"
          />
        </div>
      </div>
      <div class="form-actions">
        <button
          class="btn btn-primary"
          :disabled="!hasMeasurementData"
          @click="saveMeasurement"
        >
          Salva Misurazione
        </button>
      </div>
      <div v-if="measurementResult" class="result-box">
        {{ measurementResult }}
      </div>
    </section>

    <section v-if="showHistory" class="metric-history">
      <h3>Andamento storico</h3>
      <MetricHistoryChart
        :key="`weight-${chartRefreshToken}`"
        metric-type="weight_kg"
        :days="365"
        label="Peso"
      />
      <MetricHistoryChart
        :key="`fat-${chartRefreshToken}`"
        metric-type="fat_percentage"
        :days="365"
        label="Massa Grassa"
      />
      <MetricHistoryChart
        :key="`water-${chartRefreshToken}`"
        metric-type="body_water_percentage"
        :days="365"
        label="Acqua Corporea"
      />
      <MetricHistoryChart
        :key="`muscle-pct-${chartRefreshToken}`"
        metric-type="muscle_mass_percentage"
        :days="365"
        label="Massa Muscolare %"
      />
      <MetricHistoryChart
        :key="`bmr-${chartRefreshToken}`"
        metric-type="bmr_kcal"
        :days="365"
        label="Metabolismo Basale"
      />
      <MetricHistoryChart
        :key="`fat-mass-${chartRefreshToken}`"
        metric-type="fat_mass_kg"
        :days="365"
        label="Massa Grassa corporea"
      />
      <MetricHistoryChart
        :key="`muscle-mass-${chartRefreshToken}`"
        metric-type="muscle_mass_kg"
        :days="365"
        label="Massa Muscolare"
      />
      <MetricHistoryChart
        :key="`bone-${chartRefreshToken}`"
        metric-type="bone_mass_kg"
        :days="365"
        label="Massa Ossea"
      />
      <MetricHistoryChart
        :key="`protein-${chartRefreshToken}`"
        metric-type="protein_percentage"
        :days="365"
        label="Proteine %"
      />
      <MetricHistoryChart
        :key="`ftp-${chartRefreshToken}`"
        metric-type="ftp_watts"
        :days="365"
        label="FTP"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "../composables/useToast";
import { useAuthStore } from "../stores/auth";
import { useAthleteStore } from "../stores/athlete";
import { validateAthleteForm } from "../utils/validation";
import MetricHistoryChart from "./MetricHistoryChart.vue";
import AthleteSelector from "./AthleteSelector.vue";

const auth = useAuthStore();
const athleteStore = useAthleteStore();

const router = useRouter();
const toast = useToast();
defineEmits(["toast"]);

interface AthleteForm {
  name: string;
  age: number;
  weight_kg: number;
  height_cm: number;
  fat_percentage: number;
  body_water_percentage: number;
  muscle_mass_percentage: number;
  bmr_kcal: number;
  fat_mass_kg: number;
  subcutaneous_fat_kg: number | undefined;
  subcutaneous_fat_percentage: number;
  visceral_fat_level: number | undefined;
  visceral_fat_percentage: number;
  visceral_fat_kg: number | undefined;
  muscle_mass_kg: number;
  bone_mass_kg: number;
  protein_percentage: number;
  protein_kg: number | undefined;
  body_age: number;
  apparent_age: number;
  bmi: number | null;
  lean_body_mass_kg: number | null;
  years_active: number;
  weekly_sessions: number;
  monthly_hours: number;
  annual_hours: number;
  experience_level: string;
  goals: string;
}

const form = ref<AthleteForm>({
  name: "",
  age: 30,
  weight_kg: 70,
  height_cm: 175,
  fat_percentage: 15,
  body_water_percentage: 50,
  muscle_mass_percentage: 40,
  bmr_kcal: 1500,
  fat_mass_kg: 10.5,
  subcutaneous_fat_kg: undefined,
  subcutaneous_fat_percentage: 12,
  visceral_fat_level: undefined,
  visceral_fat_percentage: 0,
  visceral_fat_kg: undefined,
  muscle_mass_kg: 28,
  bone_mass_kg: 3.5,
  protein_percentage: 16,
  protein_kg: undefined,
  body_age: 30,
  apparent_age: 30,
  bmi: null,
  lean_body_mass_kg: null,
  years_active: 1,
  weekly_sessions: 3,
  monthly_hours: 0,
  annual_hours: 0,
  experience_level: "Beginner",
  goals: "",
});
const result = ref("");
const athleteId = ref<number | null>(null);
const isFirstLogin = ref(false);
const profileWasIncomplete = ref(false);
const fieldErrors = ref<Record<string, string>>({});
const showHistory = ref(false);
const chartRefreshToken = ref(0);
const measurementDate = ref(new Date().toISOString().split("T")[0]);
const measurement = ref({
  weight_kg: undefined as number | undefined,
  fat_percentage: undefined as number | undefined,
  body_water_percentage: undefined as number | undefined,
  muscle_mass_percentage: undefined as number | undefined,
  bmr_kcal: undefined as number | undefined,
  fat_mass_kg: undefined as number | undefined,
  subcutaneous_fat_percentage: undefined as number | undefined,
  visceral_fat_percentage: undefined as number | undefined,
  muscle_mass_kg: undefined as number | undefined,
  bone_mass_kg: undefined as number | undefined,
  protein_percentage: undefined as number | undefined,
  ftp_watts: undefined as number | undefined,
});
const measurementResult = ref("");

const hasMeasurementData = computed(() => {
  return Object.values(measurement.value).some(
    (v) => v !== undefined && v !== null,
  );
});

const bmiDisplay = computed(() => {
  const w = form.value.weight_kg;
  const h = form.value.height_cm;
  if (w && h && h > 0) {
    const hm = h / 100;
    return +(w / (hm * hm)).toFixed(1);
  }
  return "";
});

const bmiInterpretation = computed(() => {
  const v = Number(bmiDisplay.value);
  if (isNaN(v)) return "";
  if (v < 18.5) return "Sottopeso";
  if (v < 25) return "Normopeso";
  if (v < 30) return "Sovrappeso";
  return "Obeso";
});

watch([() => form.value.weight_kg, () => form.value.height_cm], ([w, h]) => {
  if (w && h && h > 0) {
    const hm = h / 100;
    form.value.bmi = +(w / (hm * hm)).toFixed(1);
  } else {
    form.value.bmi = null;
  }
});

watch(
  [
    () => form.value.fat_mass_kg,
    () => form.value.fat_percentage,
    () => form.value.weight_kg,
  ],
  ([fatKg, fatPct, weight]) => {
    if (form.value.lean_body_mass_kg) return;
    if (fatKg != null && weight != null && weight > fatKg) {
      form.value.lean_body_mass_kg = +(weight - fatKg).toFixed(1);
    } else if (fatPct != null && weight != null) {
      form.value.lean_body_mass_kg = +(weight * (1 - fatPct / 100)).toFixed(1);
    }
  },
);

watch(
  () => form.value.age,
  (newAge) => {
    if (newAge != null && newAge > 0) {
      form.value.body_age = newAge;
    }
  },
);

function validateForm(): boolean {
  fieldErrors.value = validateAthleteForm(form.value);
  return Object.keys(fieldErrors.value).length === 0;
}

async function loadAthlete() {
  const athlete = await athleteStore.fetchProfile();
  if (athlete) {
    athleteId.value = athlete.id ?? null;
    form.value = { ...form.value, ...athlete } as AthleteForm;
    isFirstLogin.value = false;
    profileWasIncomplete.value = !(
      athlete.age != null &&
      athlete.weight_kg != null &&
      (athlete.experience_level || "").trim() !== ""
    );
  } else {
    isFirstLogin.value = true;
    profileWasIncomplete.value = true;
    form.value.name = auth.user?.username || "";
  }
}

async function save() {
  if (!validateForm()) {
    result.value = "Correggi gli errori nel form";
    return;
  }
  try {
    const editableFields: Record<string, unknown> = { ...form.value };
    delete editableFields.bmi;
    delete editableFields.subcutaneous_fat_kg;
    delete editableFields.visceral_fat_level;
    delete editableFields.visceral_fat_kg;
    delete editableFields.protein_kg;
    await athleteStore.updateProfile(editableFields);
    athleteId.value = athleteStore.profile?.id ?? null;
    result.value = "Profilo atleta aggiornato";
    toast.show("Profilo salvato con successo", "success");
    showHistory.value = true;
    const shouldRedirect = isFirstLogin.value || profileWasIncomplete.value;
    if (shouldRedirect) {
      setTimeout(() => router.push("/rides"), 1200);
    }
  } catch (e: unknown) {
    result.value = "Errore: " + (e instanceof Error ? e.message : String(e));
  }
}

async function saveMeasurement() {
  if (!hasMeasurementData.value) return;
  measurementResult.value = "";
  try {
    const payload: Record<string, unknown> = { ...measurement.value };
    if (measurementDate.value) {
      payload.recorded_at = measurementDate.value;
    }
    const cleanPayload = Object.fromEntries(
      Object.entries(payload).filter(
        ([, v]) => v !== undefined && v !== null && v !== "",
      ),
    );
    await athleteStore.updateProfile(cleanPayload);
    measurementResult.value = "Misurazione salvata. Storico aggiornato.";
    toast.show("Misurazione registrata", "success");
    showHistory.value = true;
    chartRefreshToken.value += 1;
    measurement.value = {
      weight_kg: undefined,
      fat_percentage: undefined,
      body_water_percentage: undefined,
      muscle_mass_percentage: undefined,
      bmr_kcal: undefined,
      fat_mass_kg: undefined,
      subcutaneous_fat_percentage: undefined,
      visceral_fat_percentage: undefined,
      muscle_mass_kg: undefined,
      bone_mass_kg: undefined,
      protein_percentage: undefined,
      ftp_watts: undefined,
    };
  } catch (e: unknown) {
    measurementResult.value =
      "Errore: " + (e instanceof Error ? e.message : String(e));
  }
}

onMounted(() => {
  loadAthlete().catch((e) => {
    result.value = "Errore: " + (e instanceof Error ? e.message : String(e));
  });
});
</script>

<style scoped>
.welcome-banner {
  background: linear-gradient(135deg, var(--accent) 0%, #3b82f6 100%);
  color: white;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.welcome-icon {
  font-size: 1.2rem;
}
.new-measurement {
  margin-top: 1.5rem;
  padding: 1rem;
  border: 1px solid var(--border, #444);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.03);
}
.new-measurement h3 {
  margin-bottom: 0.4rem;
  color: #eee;
}
.section-hint {
  font-size: 0.85rem;
  color: #aaa;
  margin-bottom: 1rem;
}
.metric-history {
  margin-top: 1.5rem;
}
.metric-history h3 {
  margin-bottom: 0.8rem;
  color: #eee;
}
</style>
