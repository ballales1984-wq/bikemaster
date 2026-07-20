<template>
  <div class="food-log-panel">
    <h3>Alimentazione - {{ date }}</h3>
    <div class="summary-bar">
      <span>Totale: <strong>{{ Math.round(totalKcal) }} kcal</strong></span>
      <span>Pasti: {{ logs.length }}</span>
    </div>
    <NutritionSearch :date="date" @added="onNutritionAdded" />
    <form class="form-inline" @submit.prevent="add">
      <input v-model="newLog.description" placeholder="Descrizione" required maxlength="500" />
      <select v-model="newLog.meal_type">
        <option value="breakfast">Colazione</option>
        <option value="lunch">Pranzo</option>
        <option value="dinner">Cena</option>
        <option value="snack">Spuntino</option>
        <option value="other">Altro</option>
      </select>
      <input v-model.number="newLog.kcal" type="number" placeholder="kcal" min="0" step="1" />
      <button class="btn btn-primary" type="submit" :disabled="saving">Aggiungi</button>
    </form>
    <ul class="log-list">
      <li v-for="log in logs" :key="log.id" class="log-item">
        <div class="log-main">
          <span class="log-meal">{{ mealLabel(log.meal_type) }}</span>
          <span class="log-desc">{{ log.description }}</span>
          <span class="log-kcal">{{ Math.round(log.kcal || 0) }} kcal</span>
        </div>
        <div class="log-actions">
          <button class="btn btn-small btn-secondary" @click="editLog(log)">Modifica</button>
          <button class="btn btn-small btn-danger" @click="remove(log.id!)">Elimina</button>
        </div>
      </li>
    </ul>
    <div v-if="editing" class="edit-form">
      <input v-model="editForm.description" placeholder="Descrizione" required maxlength="500" />
      <select v-model="editForm.meal_type">
        <option value="breakfast">Colazione</option>
        <option value="lunch">Pranzo</option>
        <option value="dinner">Cena</option>
        <option value="snack">Spuntino</option>
        <option value="other">Altro</option>
      </select>
      <input v-model.number="editForm.kcal" type="number" placeholder="kcal" min="0" step="1" />
      <button class="btn btn-primary" @click="saveEdit">Salva</button>
      <button class="btn btn-secondary" @click="editing = null">Annulla</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from "vue";
import { useMetabolismStore } from "../stores/metabolism";
import { useToast } from "../composables/useToast";
import NutritionSearch from "./NutritionSearch.vue";
import type { FoodLog } from "../types/index";

const props = defineProps<{ date: string }>();
const store = useMetabolismStore();
const toast = useToast();
const saving = computed(() => store.saving);

const logs = computed(() => store.foodLogs);
const totalKcal = computed(() => logs.value.reduce((s, l) => s + (l.kcal || 0), 0));

function onNutritionAdded() {
  store.fetchFoodLogs(props.date);
}

const newLog = reactive({
  description: "",
  meal_type: "other" as FoodLog["meal_type"],
  kcal: 0,
  carbs_g: null as number | null,
  protein_g: null as number | null,
  fat_g: null as number | null,
  fiber_g: null as number | null,
  water_ml: null as number | null,
  note: null as string | null,
});

const editing = ref<number | null>(null);
const editForm = reactive({
  description: "",
  meal_type: "other" as FoodLog["meal_type"],
  kcal: 0,
});

function mealLabel(type: string) {
  const map: Record<string, string> = {
    breakfast: "Colazione",
    lunch: "Pranzo",
    dinner: "Cena",
    snack: "Spuntino",
    other: "Altro",
  };
  return map[type] || type;
}

async function add() {
  try {
    await store.createFoodLog({ ...newLog, date: props.date });
    newLog.description = "";
    newLog.kcal = 0;
    newLog.meal_type = "other";
    toast.add("Log alimentare aggiunto", "success");
  } catch {
    toast.add("Errore aggiunta log", "error");
  }
}

function editLog(log: FoodLog) {
  editing.value = log.id!;
  editForm.description = log.description;
  editForm.meal_type = log.meal_type;
  editForm.kcal = log.kcal;
}

async function saveEdit() {
  if (editing.value == null) return;
  try {
    await store.updateFoodLog(editing.value, editForm);
    editing.value = null;
    toast.add("Log aggiornato", "success");
  } catch {
    toast.add("Errore aggiornamento log", "error");
  }
}

async function remove(id: number) {
  try {
    await store.removeFoodLog(id);
    toast.add("Log eliminato", "success");
  } catch {
    toast.add("Errore eliminazione log", "error");
  }
}
</script>

<style scoped>
.summary-bar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: var(--text-muted);
}
.form-inline {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 1rem;
}
.form-inline input,
.form-inline select {
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--surface);
  color: var(--text);
  min-width: 120px;
}
.log-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.log-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--surface);
}
.log-main {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}
.log-meal {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-muted);
  min-width: 70px;
}
.log-desc {
  flex: 1;
}
.log-kcal {
  font-weight: 600;
}
.log-actions {
  display: flex;
  gap: 0.5rem;
}
.edit-form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--surface);
}
</style>
