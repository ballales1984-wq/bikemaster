<!--
  Selezione atleta: dropdown per scegliere l'atleta attivo tra quelli dell'utente.
  Props: nessuna. Eventi: none (legge da authStore, chiama auth.switchAthlete).
-->
<template>
  <div v-if="athletes.length > 1" class="athlete-selector">
    <label for="athlete-select">{{ t("athlete.selectLabel") }}</label>
    <select
      id="athlete-select"
      :value="currentAthleteId"
      :disabled="loading"
      @change="onChange"
    >
      <option v-for="athlete in athletes" :key="athlete.id" :value="athlete.id">
        {{ athlete.name }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "../composables/useI18n";
import { useAuthStore } from "../stores/auth";

const { t } = useI18n();
const auth = useAuthStore();

const athletes = ref<Array<{ id: number; name: string }>>([]);
const loading = ref(false);

const currentAthleteId = computed(() => {
  return auth.user?.active_athlete_id ?? auth.user?.id ?? 0;
});

async function loadAthletes() {
  if (!auth.isLoggedIn) return;
  loading.value = true;
  try {
    const data = await auth.fetchMyAthletes();
    athletes.value = data.athletes || [];
  } catch {
    athletes.value = [];
  } finally {
    loading.value = false;
  }
}

async function onChange(event: Event) {
  const select = event.target as HTMLSelectElement;
  const id = Number(select.value);
  if (!id || id === currentAthleteId.value) return;
  loading.value = true;
  try {
    await auth.switchAthlete(id);
    await loadAthletes();
  } catch {
    select.value = String(currentAthleteId.value);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadAthletes();
});
</script>

<style scoped>
.athlete-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.athlete-selector label {
  font-size: 0.85rem;
  color: #9ca3af;
}
.athlete-selector select {
  background: #1f2937;
  color: #f3f4f6;
  border: 1px solid #374151;
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.9rem;
}
.athlete-selector select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
