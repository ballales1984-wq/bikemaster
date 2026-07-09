<template>
  <div class="panel">
    <h2>🏃 Athlete Profile</h2>
    <div v-if="isFirstLogin"
class="welcome-banner">
      <span class="welcome-icon">🎉</span> Welcome! Complete your profile to get
      started
    </div>
    <form id="athlete-form"
class="form-grid" novalidate>
      <div class="form-group">
        <label for="athlete-name">Name</label>
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
        <span v-if="fieldErrors.name"
class="field-error">{{
          fieldErrors.name
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-age">Age</label>
        <input
          id="athlete-age"
          v-model.number="form.age"
          type="number"
          min="10"
          max="100"
          :class="{ error: fieldErrors.age, valid: !fieldErrors.age }"
        >
        <span v-if="fieldErrors.age"
class="field-error">{{
          fieldErrors.age
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-weight">Weight (kg)</label>
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
        <span v-if="fieldErrors.weight_kg"
class="field-error">{{
          fieldErrors.weight_kg
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-height">Height (cm)</label>
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
        <span v-if="fieldErrors.height_cm"
class="field-error">{{
          fieldErrors.height_cm
        }}</span>
      </div>
      <div class="form-group">
        <label for="athlete-fat">Body Fat (%)</label>
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
        <label for="athlete-years">Years Active</label>
        <input
          id="athlete-years"
          v-model.number="form.years_active"
          type="number"
          min="0"
          max="80"
        >
      </div>
      <div class="form-group">
        <label for="athlete-weekly">Sessions/week</label>
        <input
          id="athlete-weekly"
          v-model.number="form.weekly_sessions"
          type="number"
          min="0"
          max="14"
        >
      </div>
      <div class="form-group">
        <label for="athlete-monthly">Hours/month</label>
        <input
          id="athlete-monthly"
          v-model.number="form.monthly_hours"
          type="number"
          min="0"
          step="0.5"
        >
      </div>
      <div class="form-group">
        <label for="athlete-annual">Hours/year</label>
        <input
          id="athlete-annual"
          v-model.number="form.annual_hours"
          type="number"
          min="0"
          step="0.5"
        >
      </div>
      <div class="form-group">
        <label for="athlete-level">Level</label>
        <select
          id="athlete-level"
          v-model="form.experience_level"
          :class="{
            error: fieldErrors.experience_level,
            valid: !fieldErrors.experience_level,
          }"
        >
          <option>Beginner</option>
          <option>Amateur</option>
          <option>Intermediate</option>
          <option>Advanced</option>
          <option>Elite</option>
        </select>
        <span v-if="fieldErrors.experience_level"
class="field-error">{{
          fieldErrors.experience_level
        }}</span>
      </div>
    </form>
    <div class="form-actions">
      <button
class="btn btn-primary" @click="save">Save Athlete</button>
      <button
class="btn btn-secondary" @click="getScores">📊 Scores</button>
    </div>
    <div v-if="result"
class="result-box">
      {{ result }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "../composables/useToast";
import { apiGet, apiPost, apiPut } from "../utils/api";
import { useAuthStore } from "../stores/auth";
import { validateAthleteForm } from "../utils/validation";

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
}

interface AthleteResponse {
  athlete?: Partial<AthleteForm> & { id?: number };
  id?: number;
}

const auth = useAuthStore();

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
});
const result = ref("");
const athleteId = ref<number | null>(null);
const isFirstLogin = ref(false);
const profileWasIncomplete = ref(false);
const fieldErrors = ref<Record<string, string>>({});

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
    const data = (
      athleteId.value
        ? await apiPut("/api/v1/athletes/" + athleteId.value, form.value)
        : await apiPost("/api/v1/athletes", form.value)
    ) as { id?: number };
    athleteId.value = data.id ?? null;
    result.value = "Athlete profile saved (ID: " + data.id + ")";
    if (isFirstLogin.value) {
      toast.show("Profile created! Welcome to BikeMaster!", "success");
    }
    if (profileWasIncomplete.value) {
      setTimeout(() => router.push("/rides"), isFirstLogin.value ? 1500 : 500);
    }
  } catch (e: unknown) {
    result.value = "Error: " + (e instanceof Error ? e.message : String(e));
  }
}

async function getScores() {
  try {
    const id = athleteId.value;
    if (!id) {
      result.value = "Save athlete profile first";
      return;
    }
    const data = await apiGet("/api/v1/scores/athlete/" + id);
    result.value = JSON.stringify(data, null, 2);
  } catch (e: unknown) {
    result.value = "Error: " + (e instanceof Error ? e.message : String(e));
  }
}

onMounted(() => {
  loadAthlete().catch((e) => {
    result.value = "Error: " + (e instanceof Error ? e.message : String(e));
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
</style>
