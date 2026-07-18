<!-- Griglia calendario mensile riutilizzabile: intestazioni giorni + celle con numero, eventi (pallini) e indicatore "+N".
     Props: days (array con date/eventi), weekDays (etichette Lun-Dom). Eventi: add-for-date (click sul numero di un giorno).
     UI: griglia 7 colonne; celle evidenziate per oggi/mese-altro/eventi e cliccabili per aggiungere un evento in quella data. -->
<template>
  <div class="calendar-grid">
    <div v-for="d in weekDays"
:key="d" class="cal-header">
      {{ d }}
    </div>
    <div
      v-for="(day, idx) in days"
      :key="idx"
      class="cal-cell"
      :class="{
        'other-month': !day.currentMonth,
        today: isToday(day),
        'has-events': day.events.length > 0,
      }"
    >
      <span class="day-num"
@click="$emit('add-for-date', day.date)">
        {{ day.day }}
      </span>
      <div class="day-events">
        <span
          v-for="ev in day.events.slice(0, 3)"
          :key="ev.id"
          class="event-dot"
          :class="'dot-' + ev.event_type"
        >
          {{ ev.title }}
        </span>
        <span v-if="day.events.length > 3"
class="more-events"
        >+{{ day.events.length - 3 }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "../../composables/useI18n";

const { t } = useI18n();

interface DayData {
  date: string;
  day: number;
  currentMonth: boolean;
  isToday?: boolean;
  events: Array<{
    id: number;
    title: string;
    event_type: string;
  }>;
}

defineProps<{
  days: DayData[];
  weekDays: string[];
}>();

defineEmits<{
  (e: "add-for-date", date: string): void;
}>();

function isToday(day: DayData): boolean {
  if (!day.isToday) return false;
  const today = new Date();
  return (
    day.date ===
    `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, "0")}-${today.getDate().toString().padStart(2, "0")}`
  );
}
</script>

<style scoped>
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.cal-header {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  text-align: center;
  padding: 8px;
  font-weight: bold;
  font-size: 0.85rem;
}

.cal-cell {
  background: var(--bg-secondary);
  min-height: 90px;
  padding: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.cal-cell:hover {
  background: var(--color-calendar-1);
}

.cal-cell.other-month {
  background: var(--color-calendar-2);
  opacity: 0.7;
}

.cal-cell.today {
  border: 2px solid var(--accent);
}

.cal-cell.has-events {
  background: var(--color-calendar-3);
}

.day-num {
  font-size: 0.85rem;
  font-weight: bold;
  color: var(--text-primary);
}

.day-events {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.event-dot {
  font-size: 0.7rem;
  padding: 1px 4px;
  border-radius: 3px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.more-events {
  font-size: 0.7rem;
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .cal-cell {
    min-height: 70px;
    padding: 4px;
  }

  .event-dot {
    font-size: 0.6rem;
    padding: 1px 3px;
  }
}
</style>
