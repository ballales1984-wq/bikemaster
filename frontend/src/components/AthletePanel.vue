<!--
  Pannello profilo atleta: form di inserimento/modifica dati anagrafici e di allenamento dell'utente.
  Props: nessuna. Eventi: emit "toast" per notifiche. Carica l'atleta da /api/v1/athletes/me e salva via store.
  UI: input grid (name, age, weight, height, body fat, level, goals) with validation and Save button.
       Dopo il salvataggio mostra i grafici storici delle metriche tracciate.
-->
<template>
  <div class="panel">
    <h2> Profilo Atleta</h2>
    <div
      v-if="isFirstLogin"
      class="welcome-banner"
    >
      <span class="welcome-icon"></span> Benvenuto! Completa il tuo profilo per iniziare
    </div>
    <form
      id="athlete-form"
      class="form-grid"
      novalidate
    >
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
        >
        <span
          v-if="fieldErrors.name"
          class="field-error"
        >{{
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
        >
        <span
          v-if="fieldErrors.age"
          class="field-error"
        >{{
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
        >
        <span
          v-if="fieldErrors.weight_kg"
          class="field-error"
        >{{
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
        >
        <span
          v-if="fieldErrors.height_cm"
          class="field-error"
        >{{
            fieldErrors.height_cm
          }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-fat">Massa Grassa (%)</label>
        <input
          id="athlete-fat"
          v-model.number="form.fat_percentage"
          type="number"
          min="3"
          max="60"
          step="0.1"
        >
      </div>
      <div class="form-group">
        <label for="athlete-years">Anni di attività</label>
        <input
          id="athlete-years"
          v-model.number="form.years_active"
          type="number"
          min="0"
          max="80"
        >
      </div>
      <div class="form-group">
        <label for="athlete-weekly">Sessioni/settimana</label>
        <input
          id="athlete-weekly"
          v-model.number="form.weekly_sessions"
          type="number"
          min="0"
          max="14"
        >
      </div>
      <div class="form-group">
        <label for="athlete-monthly">Ore/mese</label>
        <input
          id="athlete-monthly"
          v-model.number="form.monthly_hours"
          type="number"
          min="0"
          step="0.5"
        >
      </div>
      <div class="form-group">
        <label for="athlete-annual">Ore/anno</label>
        <input
          id="athlete-annual"
          v-model.number="form.annual_hours"
          type="number"
          min="0"
          step="0.5"
        >
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
          <option>Principiante</option>
          <option>Amatoriale</option>
          <option>Intermedio</option>
          <option>Avanzato</option>
          <option>Elite</option>
        </select>
        <span
          v-if="fieldErrors.experience_level"
          class="field-error"
        >{{
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
        >
      </div>
    </form>
    <div class="form-actions">
      <button
        class="btn btn-primary"
        @click="save"
      >
        Salva Profilo
      </button>
    </div>
    <div
      v-if="result"
      class="result-box"
    >
      {{ result }}
    </div>

    <section v-if="showHistory" class="metric-history">
      <h3>Andamento storico</h3>
      <MetricHistoryChart
        metric-type="weight_kg"
        :days="365"
        label="Peso"
      />
      <MetricHistoryChart
        metric-type="fat_percentage"
        :days="365"
        label="Massa Grassa"
      />
      <MetricHistoryChart
        metric-type="ftp_watts"
        :days="365"
        label="FTP"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "../composables/useToast";
import { apiGet, apiPost } from "../utils/api";
import { useAuthStore } from "../stores/auth";
import { useAthleteStore } from "../stores/athlete";
import { validateAthleteForm } from "../utils/validation";
import MetricHistoryChart from "./MetricHistoryChart.vue";

interface AthleteForm {
  name: string;
  age: number;
  weight_kg: number;
  height_cm: number;
  fat_percentage: number;
  years_active: number;
  weekly_sessions: number;
  monthly_hours: number;
  annual_hours: number;
  experience_level: string;
  goals: string;
}

interface AthleteResponse {
  athlete?: Partial<AthleteForm> & { id?: number };
  id?: number;
}

const auth = useAuthStore();
const athleteStore = useAthleteStore();

const router = useRouter();
const toast = useToast();
const emit = defineEmits(["toast"]);
const form = ref<AthleteForm>({
  name: "",
  age: 30,
  weight_kg: 70,
  height_cm: 175,
  fat_percentage: 15,
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

function validateForm(): boolean {
  fieldErrors.value = validateAthleteForm(form.value);
  return Object.keys(fieldErrors.value).length === 0;
}

async function loadAthlete() {
  const data = (await apiGet("/api/v1/athletes/me")) as AthleteResponse;
  const athlete = data.athlete;
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
    await athleteStore.updateProfile(form.value);
    athleteId.value = athleteStore.profile?.id ?? null;
    result.value = "Profilo atleta aggiornato";
    toast.show("Profilo salvato con successo", "success");
    showHistory.value = true;
    if (isFirstLogin.value) {
      setTimeout(() => router.push("/rides"), 1500);
    }
    if (profileWasIncomplete.value) {
      setTimeout(() => router.push("/rides"), 500);
    }
  } catch (e: unknown) {
    result.value = "Errore: " + (e instanceof Error ? e.message : String(e));
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
.metric-history {
  margin-top: 1.5rem;
}
.metric-history h3 {
  margin-bottom: 0.8rem;
  color: #eee;
}
</style>
