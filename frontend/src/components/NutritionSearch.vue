<template>
  <div class="nutrition-search">
    <h4>{{ t("metabolism.nutritionSearch") }}</h4>
    <div class="search-bar">
      <input
        v-model="searchQuery"
        :placeholder="t('metabolism.nutritionSearchPlaceholder')"
        class="search-input"
        @input="onSearchInput"
        @focus="showResults = true"
      />
      <select
        v-model="selectedCategory"
        class="category-select"
        @change="doSearch"
      >
        <option value="">{{ t("metabolism.allCategories") }}</option>
        <option v-for="cat in categories" :key="cat" :value="cat">
          {{ cat }}
        </option>
      </select>
    </div>
    <div
      v-if="showResults && (searchResults.length > 0 || hasSearched)"
      class="results-dropdown"
    >
      <div v-if="searching" class="searching-hint">
        {{ t("common.loading") }}
      </div>
      <div v-else-if="searchResults.length === 0" class="no-results">
        {{ t("metabolism.noResults") }}
      </div>
      <ul v-else class="search-results">
        <li
          v-for="item in searchResults"
          :key="item.id"
          class="result-item"
          @click="selectItem(item)"
        >
          <div class="result-main">
            <span class="result-name">{{ item.name }}</span>
            <span class="result-category">{{ item.category }}</span>
          </div>
          <div class="result-macros">
            <span
              >{{ Math.round(item.kcal_per_100g) }}
              {{ t("metabolism.kcal") }}/100g</span
            >
            <span v-if="item.carbs_g_per_100g"
              >C: {{ item.carbs_g_per_100g }}g</span
            >
            <span v-if="item.protein_g_per_100g"
              >P: {{ item.protein_g_per_100g }}g</span
            >
            <span v-if="item.fat_g_per_100g"
              >F: {{ item.fat_g_per_100g }}g</span
            >
          </div>
        </li>
      </ul>
    </div>
    <div v-if="selectedItem" class="quantity-form">
      <div class="selected-item-info">
        <strong>{{ selectedItem.name }}</strong>
        <span class="item-category">{{ selectedItem.category }}</span>
      </div>
      <div class="quantity-inputs">
        <label>
          {{ t("metabolism.quantity") }}
          <input
            v-model.number="quantity"
            type="number"
            min="1"
            max="5000"
            step="1"
          />
        </label>
        <div class="calculated-values">
          <span
            ><strong>{{ calculatedKcal }}</strong>
            {{ t("metabolism.kcal") }}</span
          >
          <span v-if="calculatedCarbs">C: {{ calculatedCarbs }}g</span>
          <span v-if="calculatedProtein">P: {{ calculatedProtein }}g</span>
          <span v-if="calculatedFat">F: {{ calculatedFat }}g</span>
          <span v-if="calculatedFiber">Fibra: {{ calculatedFiber }}g</span>
        </div>
      </div>
      <div class="quantity-actions">
        <button
          class="btn btn-primary"
          :disabled="!canAdd || saving"
          @click="addToLog"
        >
          {{ t("metabolism.addFood") }}
        </button>
        <button class="btn btn-secondary" @click="cancelSelection">
          {{ t("common.cancel") }}
        </button>
      </div>
    </div>
    <div class="add-custom">
      <button
        class="btn btn-small btn-secondary"
        @click="showCustomForm = true"
      >
        {{ t("metabolism.addCustomFood") }}
      </button>
      <div v-if="showCustomForm" class="custom-form">
        <input v-model="customName" :placeholder="t('common.name')" />
        <select v-model="customCategory">
          <option v-for="cat in categories" :key="cat" :value="cat">
            {{ cat }}
          </option>
        </select>
        <input
          v-model.number="customKcal"
          type="number"
          :placeholder="`${t('metabolism.kcal')}/100g`"
          min="0"
        />
        <input
          v-model.number="customCarbs"
          type="number"
          :placeholder="`${t('metabolism.carbs')}`"
          min="0"
        />
        <input
          v-model.number="customProtein"
          type="number"
          :placeholder="`${t('metabolism.protein')}`"
          min="0"
        />
        <input
          v-model.number="customFat"
          type="number"
          :placeholder="`${t('metabolism.fat')}`"
          min="0"
        />
        <input
          v-model.number="customFiber"
          type="number"
          :placeholder="`${t('metabolism.fiber')}`"
          min="0"
        />
        <button
          class="btn btn-primary"
          :disabled="!canAddCustom || saving"
          @click="addCustomFood"
        >
          {{ t("common.save") }}
        </button>
        <button class="btn btn-secondary" @click="showCustomForm = false">
          {{ t("common.cancel") }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useMetabolismStore } from "../stores/metabolism";
import { useToast } from "../composables/useToast";
import { useI18n } from "../composables/useI18n";
import type { NutritionFoodItem } from "../types/index";

const props = defineProps<{ date: string }>();
const emit = defineEmits<{
  added: [];
}>();
const store = useMetabolismStore();
const toast = useToast();
const { t } = useI18n();

const searchQuery = ref("");
const selectedCategory = ref("");
const categories = ref<string[]>([]);
const searchResults = ref<NutritionFoodItem[]>([]);
const searching = ref(false);
const hasSearched = ref(false);
const showResults = ref(false);
const selectedItem = ref<NutritionFoodItem | null>(null);
const quantity = ref(100);
const saving = ref(false);
const showCustomForm = ref(false);
const customName = ref("");
const customCategory = ref("pasta");
const customKcal = ref(0);
const customCarbs = ref(0);
const customProtein = ref(0);
const customFat = ref(0);
const customFiber = ref(0);

let searchTimeout: number | null = null;

const calculatedKcal = computed(() => {
  if (!selectedItem.value) return 0;
  return Math.round((selectedItem.value.kcal_per_100g * quantity.value) / 100);
});
const calculatedCarbs = computed(() => {
  if (!selectedItem.value) return 0;
  return +(
    (selectedItem.value.carbs_g_per_100g * quantity.value) /
    100
  ).toFixed(1);
});
const calculatedProtein = computed(() => {
  if (!selectedItem.value) return 0;
  return +(
    (selectedItem.value.protein_g_per_100g * quantity.value) /
    100
  ).toFixed(1);
});
const calculatedFat = computed(() => {
  if (!selectedItem.value) return 0;
  return +((selectedItem.value.fat_g_per_100g * quantity.value) / 100).toFixed(
    1,
  );
});
const calculatedFiber = computed(() => {
  if (!selectedItem.value) return 0;
  return +(
    (selectedItem.value.fiber_g_per_100g * quantity.value) /
    100
  ).toFixed(1);
});
const canAdd = computed(
  () => selectedItem.value !== null && quantity.value > 0,
);
const canAddCustom = computed(
  () => customName.value.trim().length > 0 && customKcal.value > 0,
);

function mealLabel(type: string): string {
  const map: Record<string, string> = {
    breakfast: t("metabolism.breakfast"),
    lunch: t("metabolism.lunch"),
    dinner: t("metabolism.dinner"),
    snack: t("metabolism.snack"),
    other: t("metabolism.other"),
  };
  return map[type] || type;
}

async function loadCategories() {
  try {
    categories.value = await store.fetchNutritionCategories();
    if (categories.value.length === 0) {
      categories.value = [
        "pasta",
        "pizza",
        "carne",
        "pesce",
        "uova",
        "pane",
        "cereali",
        "latticini",
        "insalate",
        "zuppe",
        "verdure",
        "legumi",
        "dolci",
        "colazione",
        "street_food",
        "bevande",
      ];
    }
  } catch {
    categories.value = [
      "pasta",
      "pizza",
      "carne",
      "pesce",
      "uova",
      "pane",
      "cereali",
      "latticini",
      "insalate",
      "zuppe",
      "verdure",
      "legumi",
      "dolci",
      "colazione",
      "street_food",
      "bevande",
    ];
  }
}

async function doSearch() {
  searching.value = true;
  hasSearched.value = true;
  try {
    searchResults.value = await store.searchNutritionFood(
      searchQuery.value,
      selectedCategory.value || undefined,
    );
  } catch {
    searchResults.value = [];
  } finally {
    searching.value = false;
  }
}

function onSearchInput() {
  hasSearched.value = true;
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = window.setTimeout(() => doSearch(), 250);
}

function selectItem(item: NutritionFoodItem) {
  selectedItem.value = item;
  quantity.value = 100;
  showResults.value = false;
  searchQuery.value = item.name;
}

function cancelSelection() {
  selectedItem.value = null;
  quantity.value = 100;
  searchQuery.value = "";
  showResults.value = false;
}

async function addToLog() {
  if (!selectedItem.value || quantity.value <= 0) return;
  saving.value = true;
  try {
    await store.createFoodLog({
      date: props.date,
      meal_type: "other",
      description: `${selectedItem.value.name} (${quantity.value}g)`,
      kcal: calculatedKcal.value,
      carbs_g: calculatedCarbs.value,
      protein_g: calculatedProtein.value,
      fat_g: calculatedFat.value,
      fiber_g: calculatedFiber.value,
    });
    toast.add(t("common.success"), "success");
    emit("added");
    cancelSelection();
  } catch {
    toast.add(t("common.error"), "error");
  } finally {
    saving.value = false;
  }
}

async function addCustomFood() {
  if (!customName.value.trim() || customKcal.value <= 0) return;
  saving.value = true;
  try {
    const item = await store.createNutritionFoodItem({
      name: customName.value.trim(),
      category: customCategory.value,
      kcal_per_100g: customKcal.value,
      carbs_g_per_100g: customCarbs.value,
      protein_g_per_100g: customProtein.value,
      fat_g_per_100g: customFat.value,
      fiber_g_per_100g: customFiber.value,
    });
    toast.add(t("metabolism.foodAdded"), "success");
    customName.value = "";
    customKcal.value = 0;
    customCarbs.value = 0;
    customProtein.value = 0;
    customFat.value = 0;
    customFiber.value = 0;
    showCustomForm.value = false;
    await loadCategories();
    selectItem(item as NutritionFoodItem);
  } catch {
    toast.add(t("common.error"), "error");
  } finally {
    saving.value = false;
  }
}

function onClickOutside(e: MouseEvent) {
  const el = e.target as HTMLElement;
  if (!el.closest(".nutrition-search")) {
    showResults.value = false;
  }
}

onMounted(async () => {
  await loadCategories();
  document.addEventListener("click", onClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", onClickOutside);
  if (searchTimeout) clearTimeout(searchTimeout);
});
</script>

<style scoped>
.nutrition-search {
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 1rem;
  background: var(--surface);
  margin-bottom: 1rem;
}
.nutrition-search h4 {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
}
.search-bar {
  display: flex;
  gap: 0.5rem;
}
.search-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--bg);
  color: var(--text);
}
.category-select {
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--bg);
  color: var(--text);
}
.results-dropdown {
  margin-top: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  max-height: 240px;
  overflow-y: auto;
  background: var(--bg);
}
.search-results {
  list-style: none;
  padding: 0;
  margin: 0;
}
.result-item {
  padding: 0.6rem 0.75rem;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}
.result-item:hover {
  background: var(--surface-hover, rgba(128, 128, 128, 0.08));
}
.result-item:last-child {
  border-bottom: none;
}
.result-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.result-name {
  font-weight: 500;
}
.result-category {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
}
.result-macros {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}
.no-results,
.searching-hint {
  padding: 0.75rem;
  color: var(--text-muted);
  text-align: center;
}
.quantity-form {
  margin-top: 0.75rem;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--bg);
}
.selected-item-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.item-category {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
}
.quantity-inputs {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 0.5rem;
}
.quantity-inputs label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}
.quantity-inputs input {
  width: 80px;
  padding: 0.35rem;
  border: 1px solid var(--border);
  border-radius: 0.25rem;
  background: var(--surface);
  color: var(--text);
}
.calculated-values {
  display: flex;
  gap: 0.75rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}
.calculated-values strong {
  color: var(--text);
}
.quantity-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.add-custom {
  margin-top: 0.75rem;
}
.custom-form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 0.5rem;
}
.custom-form input,
.custom-form select {
  padding: 0.35rem;
  border: 1px solid var(--border);
  border-radius: 0.25rem;
  background: var(--surface);
  color: var(--text);
  font-size: 0.85rem;
}
</style>
