<template>
  <div class="panel">
    <h2>🚴‍♂️ Granfondo Planner</h2>

    <div class="form-grid">
      <div class="form-group">
        <label for="gf-start-date">{{ t("granfondo.startDate") }}</label>
        <input id="gf-start-date"
v-model="startDate" type="date"
/>
      </div>
      <div class="form-group">
        <label for="gf-weeks">{{ t("granfondo.targetWeeks") }}</label>
        <select id="gf-weeks" v-model.number="weeks">
          <option :value="8">
            {{ t("granfondo.week8") }}
          </option>
          <option :value="9">
            {{ t("granfondo.week9") }}
          </option>
          <option :value="10">
            {{ t("granfondo.week10") }}
          </option>
          <option :value="11">
            {{ t("granfondo.week11") }}
          </option>
          <option :value="12">
            {{ t("granfondo.week12") }}
          </option>
        </select>
      </div>
      <div class="form-group">
        <button class="btn btn-primary" @click="generatePlan">
          📅 {{ t("granfondo.generate") }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-text">
      {{ t("granfondo.generating") }}
    </div>

    <div v-if="plan" class="plan-container">
      <div class="plan-header">
        <h3>
          {{ t("granfondo.planTitle") }} {{ weeks }}
          {{ t("granfondo.weeksLabel") }}
        </h3>
        <p class="plan-dates">
          {{ t("granfondo.from") }} {{ startDate }} {{ t("granfondo.to") }}
          {{ endDate }}
        </p>
      </div>

      <div class="plan-actions">
        <button class="btn btn-success" :disabled="saving" @click="savePlan">
          {{ saving ? t("granfondo.saving") : t("granfondo.saveToCalendar") }}
        </button>
        <span
          v-if="saveMessage"
          class="save-message"
          :class="{ success: saveSuccess, error: !saveSuccess }"
        >
          {{ saveMessage }}
        </span>
      </div>

      <div class="tapering-info">
        <span class="badge badge-info">{{ t("granfondo.tapering") }}</span>
      </div>
    </div>
    <div class="calendar-grid plan-grid">
      <div v-for="d in weekDays" :key="d" class="cal-header">
        {{ d }}
      </div>
      <div
        v-for="(day, idx) in calendarDays"
        :key="idx"
        class="cal-cell"
        :class="{ today: day.isToday }"
      >
        <span class="day-num">{{ day.day }}</span>
        <div class="day-workouts">
          <div
            v-for="w in day.workouts"
            :key="w.title"
            class="workout-item"
            :class="'type-' + w.workout_type"
          >
            {{ w.title }}
            <span class="workout-meta">{{ w.duration_minutes }}min
              {{ Math.round(w.target_intensity * 100) }}%</span>
          </div>
        </div>
      </div>
    </div>
    <div class="workout-legend">
      <span class="legend-item legend-endurance">{{
        t("granfondo.legendEndurance")
      }}</span>
      <span class="legend-item legend-threshold">{{
        t("granfondo.legendThreshold")
      }}</span>
      <span class="legend-item legend-sweetspot">{{
        t("granfondo.legendSweetspot")
      }}</span>
      <span class="legend-item legend-recovery">{{
        t("granfondo.legendRecovery")
      }}</span>
      <span class="legend-item legend-race">{{
        t("granfondo.legendRace")
      }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useI18n } from "../composables/useI18n";
import { apiGet, apiPost } from "../utils/api";

const { t } = useI18n();

const athleteId = ref(null);
const startDate = ref(new Date().toISOString().split("T")[0]);
const weeks = ref(8);
const loading = ref(false);
const saving = ref(false);
const plan = ref(null);
const saveMessage = ref("");
const saveSuccess = ref(true);

const weekDays = [
  t("granfondo.weekMon"),
  t("granfondo.weekTue"),
  t("granfondo.weekWed"),
  t("granfondo.weekThu"),
  t("granfondo.weekFri"),
  t("granfondo.weekSat"),
  t("granfondo.weekSun"),
];

async function loadAthleteId() {
  const data = await apiGet("/api/v1/athletes");
  athleteId.value = data.athletes?.[0]?.id ?? 0;
}

async function savePlan() {
  if (!plan.value) return;
  saving.value = true;
  saveMessage.value = "";
  try {
    await apiPost("/api/v1/training/granfondo/save", { plan: plan.value });
    saveMessage.value = t("granfondo.saveSuccess");
    saveSuccess.value = true;
  } catch (e) {
    saveMessage.value = e.message || t("granfondo.saveError");
    saveSuccess.value = false;
  } finally {
    saving.value = false;
  }
}

const endDate = computed(() => {
  const d = new Date(startDate.value);
  d.setDate(d.getDate() + weeks.value * 7);
  return d.toISOString().split("T")[0];
});

async function generatePlan() {
  if (!athleteId.value) return;
  loading.value = true;
  try {
    const result = await apiPost("/api/v1/training/granfondo/plan", {
      athlete_id: athleteId.value,
      start_date: startDate.value,
      target_weeks: weeks.value,
    });
    plan.value = result.plan;
  } catch (e) {
    console.error("plan error", e);
    plan.value = null;
  } finally {
    loading.value = false;
  }
}

const calendarDays = computed(() => {
  if (!plan.value) return [];

  const start = new Date(startDate.value);
  const firstDay = start.getDay() || 7;
  const totalDays = weeks.value * 7 + 1;

  const result = [];
  const today = new Date().toISOString().split("T")[0];

  for (let i = -firstDay + 1; i < totalDays; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().split("T")[0];
    const dayWorkouts = plan.value.filter((w) => w.date === dateStr);

    result.push({
      day: d.getDate(),
      date: dateStr,
      workouts: dayWorkouts,
      isToday: dateStr === today,
    });
  }

  return result;
});

onMounted(() => {
  loadAthleteId().catch(console.error);
});
</script>

<style scoped>
.plan-container {
  margin-top: 20px;
}

.plan-header h3 {
  color: var(--accent);
  margin-bottom: 5px;
}

.plan-dates {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.tapering-info {
  margin: 15px 0;
}

.badge-info {
  background: var(--accent-secondary);
  color: var(--text-primary);
}

.plan-grid {
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  margin-top: 15px;
}

.workout-item {
  font-size: 0.65rem;
  padding: 2px 4px;
  border-radius: 3px;
  margin-bottom: 2px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workout-meta {
  display: block;
  font-size: 0.6rem;
  opacity: 0.8;
}

.legend-endurance {
  background: var(--color-legend-endurance);
}
.legend-threshold {
  background: var(--color-legend-threshold);
}
.legend-sweetspot {
  background: var(--color-legend-sweetspot);
}
.legend-recovery {
  background: var(--color-legend-recovery);
}
.legend-race {
  background: var(--color-legend-race);
}

.workout-legend {
  display: flex;
  gap: 8px;
  margin-top: 15px;
  flex-wrap: wrap;
}

.workout-legend .legend-item {
  font-size: 0.78rem;
  padding: 3px 8px;
  border-radius: 12px;
  color: var(--text-primary);
}

.plan-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}

.save-message {
  font-size: 0.9rem;
}

.save-message.success {
  color: var(--color-success-text);
}

.save-message.error {
  color: var(--color-error-text);
}

.btn-success {
  background: var(--color-success-strong);
  color: var(--text-primary);
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
}

.btn-success:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
