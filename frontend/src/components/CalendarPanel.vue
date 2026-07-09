<template>
  <section>
    <div class="panel">
      <h2>📅 Calendar & Goals</h2>

      <div class="calendar-controls">
        <div class="calendar-nav">
          <button class="btn btn-secondary btn-sm"
@click="prevMonth"
>
◀
</button>
          <span class="month-label">{{ monthLabel }}</span>
          <button class="btn btn-secondary btn-sm"
@click="nextMonth"
>
▶
</button>
          <button class="btn btn-secondary btn-sm" @click="goToday">
            {{ t("calendar.today") }}
          </button>
        </div>
        <div class="athlete-select">
          <label>{{ t("calendar.athlete") }}:</label>
          <select v-model.number="athleteId" @change="loadEvents">
            <option :value="0">
              {{ t("calendar.general") }}
            </option>
            <option v-for="a in athletes" :key="a.id" :value="a.id">
              {{ a.name }}
            </option>
          </select>
        </div>
      </div>

      <div class="calendar-legend">
        <span class="legend-item legend-training">Training</span>
        <span class="legend-item legend-race">Race</span>
        <span class="legend-item legend-recovery">Recovery</span>
        <span class="legend-item legend-goal">Goal</span>
        <span class="legend-item legend-test">Test</span>
        <span class="legend-item legend-other">Other</span>
      </div>

      <CalendarGrid
        :days="calendarDays"
        :week-days="weekDays"
        @add-for-date="openAddForDate"
      />

      <FitnessChart v-if="fitnessData.length" :data="fitnessData" />
    </div>

    <div class="panel">
      <h2>🎯 Linked Goals</h2>
      <div class="objectives-box">
        <div
          v-for="obj in recommendedObjectives"
          :key="obj.label"
          class="obj-card"
        >
          <div class="obj-icon">
            {{ obj.icon }}
          </div>
          <div class="obj-text">
            <strong>{{ obj.label }}</strong>
            <small>{{ obj.hint }}</small>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="panel form-overlay">
      <h3>
        <h3>
          {{ editingEvent ? t("calendar.editEvent") : t("calendar.addEvent") }}
        </h3>
        <form class="form-grid" @submit.prevent="saveEvent">
          <div class="form-group">
            <label for="event-title">Title *</label>
            <input
              id="event-title"
              v-model="form.title"
              required
              maxlength="200"
            />
          </div>
          <div class="form-actions">
            <button type="submit"
class="btn btn-primary"
>
Save
</button>
            <button
              type="button"
              class="btn btn-secondary"
              @click="showForm = false"
            >
              Cancel
            </button>
          </div>
        </form>
      </h3>
    </div>
    <ConfirmModal
      v-model="showDeleteModal"
      title="{{ t('calendar.deleteEvent') }}"
      :message="`Delete event '${deleteTargetTitle}'?`"
      confirm-label="Delete"
      cancel-label="Cancel"
      @confirm="handleDelete"
    />
  </section>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "../composables/useI18n";
import { apiGet, apiPost, apiDelete, apiPut } from "../utils/api";
import ConfirmModal from "./ConfirmModal.vue";
import CalendarGrid from "./calendar/CalendarGrid.vue";
import FitnessChart from "./calendar/FitnessChart.vue";

const { t } = useI18n();

const athleteId = ref(null);
const athletes = ref([]);
const currentYear = ref(new Date().getFullYear());
const currentMonth = ref(new Date().getMonth());
const events = ref([]);
const fitnessData = ref([]);
const showForm = ref(false);
const showDeleteModal = ref(false);
const deleteTargetId = ref(null);
const deleteTargetTitle = ref("");
const editingEvent = ref(null);
const form = ref({
  title: "",
  event_type: "training",
  date: "",
  duration_minutes: 0,
  description: "",
  completed: false,
});
const athleteGoals = ref("");
const calendarError = ref("");

const weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const monthLabel = computed(() => {
  const months = [
    t("calendar.january"),
    t("calendar.february"),
    t("calendar.march"),
    t("calendar.april"),
    t("calendar.may"),
    t("calendar.june"),
    t("calendar.july"),
    t("calendar.august"),
    t("calendar.september"),
    t("calendar.october"),
    t("calendar.november"),
    t("calendar.december"),
  ];
  return `${months[currentMonth.value]} ${currentYear.value}`;
});

const calendarDays = computed(() => {
  const firstDay = new Date(currentYear.value, currentMonth.value, 1);
  let startWeekDay = firstDay.getDay() - 1;
  if (startWeekDay < 0) startWeekDay = 6;
  const daysInMonth = new Date(
    currentYear.value,
    currentMonth.value + 1,
    0,
  ).getDate();
  const prevMonthDays = new Date(
    currentYear.value,
    currentMonth.value,
    0,
  ).getDate();
  const result = [];
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, "0")}-${today.getDate().toString().padStart(2, "0")}`;
  for (let i = 0; i < startWeekDay; i++) {
    const d = prevMonthDays - startWeekDay + 1 + i;
    const m = currentMonth.value === 0 ? 12 : currentMonth.value;
    const y =
      currentMonth.value === 0 ? currentYear.value - 1 : currentYear.value;
    result.push({
      day: d,
      date: `${y}-${m.toString().padStart(2, "0")}-${d.toString().padStart(2, "0")}`,
      currentMonth: false,
      events: [],
    });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${currentYear.value}-${(currentMonth.value + 1).toString().padStart(2, "0")}-${d.toString().padStart(2, "0")}`;
    const dayEvents = events.value.filter((e) => e.date === dateStr);
    result.push({
      day: d,
      date: dateStr,
      currentMonth: true,
      events: dayEvents,
      isToday: dateStr === todayStr,
    });
  }
  const remaining = 42 - result.length;
  for (let i = 1; i <= remaining; i++) {
    const m = currentMonth.value === 11 ? 1 : currentMonth.value + 2;
    const y =
      currentMonth.value === 11 ? currentYear.value + 1 : currentYear.value;
    result.push({
      day: i,
      date: `${y}-${m.toString().padStart(2, "0")}-${i.toString().padStart(2, "0")}`,
      currentMonth: false,
      events: [],
    });
  }
  return result;
});

const selectedDate = computed(() => {
  const today = new Date();
  const y = today.getFullYear(),
    m = today.getMonth(),
    d = today.getDate();
  if (currentMonth.value === m && currentYear.value === y) {
    return today.toLocaleDateString("en-US");
  }
  return `${d}/${m + 1}/${y}`;
});

const selectedDateEvents = computed(() => {
  const today = new Date();
  const y = today.getFullYear(),
    m = today.getMonth(),
    d = today.getDate();
  if (currentMonth.value === m && currentYear.value === y) {
    const todayStr = `${y}-${(m + 1).toString().padStart(2, "0")}-${d.toString().padStart(2, "0")}`;
    return events.value
      .filter((e) => e.date === todayStr)
      .sort((a, b) => a.id - b.id);
  }
  return [];
});

const recommendedObjectives = computed(() => [
  {
    label: "Interval Training",
    icon: "⚡",
    hint: "HIIT session",
    event_type: "training",
    duration: 45,
    title: "Interval Training",
  },
  {
    label: "Long Ride",
    icon: "🏔️",
    hint: "Easy ride",
    event_type: "training",
    duration: 120,
    title: "Long Ride",
  },
  {
    label: "Active Recovery",
    icon: "🧘",
    hint: "Stretching",
    event_type: "recovery",
    duration: 30,
    title: "Active Recovery",
  },
  {
    label: "FTP Test",
    icon: "🔬",
    hint: "Power test",
    event_type: "test",
    duration: 60,
    title: "FTP Test",
  },
  {
    label: "Race",
    icon: "🏁",
    hint: "Competition",
    event_type: "race",
    duration: 180,
    title: "Race",
  },
  {
    label: "Goal Deadline",
    icon: "🎯",
    hint: "Deadline",
    event_type: "goal_deadline",
    duration: 0,
    title: "Goal Deadline",
  },
]);

function isToday(day) {
  if (!day.isToday) return false;
  const today = new Date();
  return (
    day.date ===
    `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, "0")}-${today.getDate().toString().padStart(2, "0")}`
  );
}

function prevMonth() {
  if (currentMonth.value === 0) {
    currentMonth.value = 11;
    currentYear.value--;
  } else {
    currentMonth.value--;
  }
  loadEvents();
}
function nextMonth() {
  if (currentMonth.value === 11) {
    currentMonth.value = 0;
    currentYear.value++;
  } else {
    currentMonth.value++;
  }
  loadEvents();
}
function goToday() {
  const today = new Date();
  currentYear.value = today.getFullYear();
  currentMonth.value = today.getMonth();
  loadEvents();
}

function eventLabel(type) {
  const map = {
    training: "Training",
    race: "Race",
    recovery: "Recovery",
    goal_deadline: "Goal",
    test: "Test",
    other: "Other",
  };
  return map[type] || type;
}

function openAddForDate(date) {
  editingEvent.value = null;
  form.value = {
    title: "",
    event_type: "training",
    date,
    duration_minutes: 0,
    description: "",
    completed: false,
    lat: null,
    lon: null,
  };
  showForm.value = true;
}

function openEdit(ev) {
  editingEvent.value = ev;
  form.value = { ...ev };
  showForm.value = true;
}

function quickAddFromObjective(obj) {
  const today = new Date();
  const dateStr = `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, "0")}-${today.getDate().toString().padStart(2, "0")}`;
  editingEvent.value = null;
  form.value = {
    title: obj.title,
    event_type: obj.event_type,
    date: dateStr,
    duration_minutes: obj.duration,
    description: obj.hint,
    completed: false,
    lat: null,
    lon: null,
  };
  showForm.value = true;
}

async function loadAthletes() {
  try {
    const data = await apiGet("/api/v1/athletes");
    athletes.value = data.athletes || [];
    if (athletes.value.length > 0 && !athleteId.value) {
      athleteId.value = athletes.value[0].id;
    }
  } catch (e) {
    athletes.value = [];
  }
}

async function loadEvents() {
  if (!athleteId.value) {
    events.value = [];
    fitnessData.value = [];
    return;
  }
  try {
    const [eventsData, fitness] = await Promise.all([
      apiGet("/api/v1/calendar/events", {
        athlete_id: athleteId.value,
        year: currentYear.value,
        month: currentMonth.value + 1,
      }),
      apiGet("/api/v1/training/load", {
        athlete_id: athleteId.value,
        days: 30,
      }).catch(() => ({ training_loads: [] })),
    ]);
    events.value = eventsData.events || [];
    fitnessData.value = fitness.training_loads || [];
  } catch (e) {
    events.value = [];
    fitnessData.value = [];
  }
}

async function loadGoals() {
  if (!athleteId.value) {
    athleteGoals.value = "";
    return;
  }
  try {
    const data = await apiGet("/api/v1/athletes/" + athleteId.value);
    athleteGoals.value = data.goals || "";
  } catch (e) {
    athleteGoals.value = "";
  }
}

async function saveEvent() {
  try {
    const payload = { ...form.value, athlete_id: athleteId.value };
    if (editingEvent.value) {
      await apiPut(`/api/v1/calendar/events/${editingEvent.value.id}`, payload);
    } else {
      await apiPost("/api/v1/calendar/events", payload);
    }
    showForm.value = false;
    editingEvent.value = null;
    loadEvents();
    loadGoals();
  } catch (e) {
    calendarError.value = e.message || "Error saving";
  }
}

async function handleDelete() {
  if (!deleteTargetId.value) return;
  try {
    await apiDelete(`/api/v1/calendar/events/${deleteTargetId.value}`);
    loadEvents();
  } catch (e) {
    calendarError.value = e.message || "Error deleting";
  } finally {
    deleteTargetId.value = null;
    deleteTargetTitle.value = "";
  }
}

function askDeleteEvent(id) {
  const ev = events.value.find((e) => e.id === id);
  deleteTargetId.value = id;
  deleteTargetTitle.value = ev ? ev.title : "";
  showDeleteModal.value = true;
}

async function toggleComplete(ev) {
  try {
    await apiPost(`/api/v1/calendar/events/${ev.id}/complete`, {});
    loadEvents();
  } catch (e) {
    calendarError.value = e.message || "Error completing";
  }
}

let initialized = false;

onMounted(async () => {
  await loadAthletes();
  initialized = true;
  await loadEvents();
  await loadGoals();
});

watch(athleteId, () => {
  if (!initialized) return;
  loadEvents();
  loadGoals();
});

watch([currentYear, currentMonth], () => {
  if (!initialized) return;
  loadEvents();
});
</script>

<style scoped>
.fitness-chart-panel {
  position: relative;
  height: 260px;
}
</style>
