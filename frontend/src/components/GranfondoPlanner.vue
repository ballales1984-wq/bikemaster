<!-- Planner Granfondo: genera un piano di allenamento multi-settimana per un atleta (endpoint /api/v1/training/granfondo).
     Props: nessuna. Eventi: nessuno. Seleziona data inizio/numero settimane e mostra un calendario con gli allenamenti;
     permette di salvare il piano generato. UI: form, barra date, griglia giorni con i workout e pulsante "Save Plan". -->
<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { apiGet, apiPost } from "../utils/api";

interface Athlete {
  id: number;
  name: string;
}

interface Workout {
  date: string;
  title: string;
  workout_type: string;
  duration_minutes: number;
  target_intensity: number;
}

interface PlanResponse {
  plan: Workout[];
}

const athleteId = ref(0);
const startDate = ref(new Date().toISOString().split("T")[0]);
const weeks = ref(8);
const loading = ref(false);
const plan = ref<Workout[] | null>(null);
const errorMessage = ref("");
const saving = ref(false);
const success = ref(false);

const _weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;

const endDate = computed(() => {
  const d = new Date(startDate.value);
  d.setDate(d.getDate() + weeks.value * 7);
  return d.toISOString().split("T")[0];
});

const calendarDays = computed(() => {
  if (!plan.value) return [];
  const start = new Date(startDate.value);
  const startDay = start.getDay() || 7;
  const totalDays = weeks.value * 7 + 1;
  const days: {
    day: number;
    date: string;
    workouts: Workout[];
    isToday: boolean;
  }[] = [];
  const today = new Date().toISOString().split("T")[0];
  for (let offset = -startDay + 1; offset < totalDays; offset++) {
    const d = new Date(start);
    d.setDate(d.getDate() + offset);
    const dateStr = d.toISOString().split("T")[0];
    const workouts = plan.value.filter((w) => w.date === dateStr);
    days.push({
      day: d.getDate(),
      date: dateStr,
      workouts,
      isToday: dateStr === today,
    });
  }
  return days;
});

async function loadAthletes() {
  try {
    const res = await apiGet<{ athletes: Athlete[] }>("/api/v1/athletes");
    athleteId.value = res.athletes?.[0]?.id ?? 0;
  } catch {
    athleteId.value = 0;
  }
}

async function generatePlan() {
  if (!athleteId.value) return;
  loading.value = true;
  errorMessage.value = "";
  success.value = false;
  try {
    const res = await apiPost<PlanResponse>("/api/v1/training/granfondo/plan", {
      athlete_id: athleteId.value,
      start_date: startDate.value,
      target_weeks: weeks.value,
    });
    plan.value = res.plan || [];
  } catch (e: unknown) {
    plan.value = null;
    errorMessage.value =
      e instanceof Error ? e.message : "Failed to generate plan";
  } finally {
    loading.value = false;
  }
}

async function savePlan() {
  if (!plan.value) return;
  saving.value = true;
  errorMessage.value = "";
  success.value = false;
  try {
    await apiPost("/api/v1/training/granfondo/save", {
      plan: plan.value,
      athlete_id: athleteId.value,
    });
    success.value = true;
  } catch (e: unknown) {
    success.value = false;
    errorMessage.value = e instanceof Error ? e.message : "Failed to save plan";
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadAthletes().catch(console.error);
});
</script>

<template>
  <div class="panel">
    <h2>Granfondo Planner</h2>
    <div class="form-grid">
      <div class="form-group">
        <label for="gf-start-date">Start date</label>
        <input id="gf-start-date" v-model="startDate" type="date" />
      </div>
      <div class="form-group">
        <label for="gf-weeks">Weeks</label>
        <input id="gf-weeks" v-model="weeks" type="number" min="1" />
      </div>
      <button
        class="btn-primary"
        :disabled="!athleteId || loading"
        @click="generatePlan"
      >
        Generate Plan
      </button>
    </div>

    <p v-if="loading" class="loading-text">Generating plan…</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <div v-if="plan" class="plan-container">
      <div class="plan-header">
        <div class="plan-dates">{{ startDate }} → {{ endDate }}</div>
        <div v-if="plan.length" class="plan-actions">
          <button class="btn-success" :disabled="saving" @click="savePlan">
            Save Plan
          </button>
        </div>
      </div>
      <div class="calendar-grid plan-grid">
        <div v-for="day in calendarDays" :key="day.date" class="day-cell">
          <div class="day-num">{{ day.day }}</div>
          <div class="day-workouts">
            <div
              v-for="workout in day.workouts"
              :key="workout.date + workout.title"
              class="workout-meta"
            >
              {{ workout.title }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel {
  padding: 1rem;
}
.form-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.loading-text {
  color: #666;
}
.error-text {
  color: red;
}
.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 1rem 0;
}
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 0.5rem;
}
.day-cell {
  border: 1px solid #eee;
  padding: 0.5rem;
  border-radius: 4px;
}
.day-num {
  font-weight: bold;
}
.day-workouts {
  margin-top: 0.25rem;
  font-size: 0.8rem;
}
.workout-meta {
  margin-top: 0.25rem;
}
</style>
