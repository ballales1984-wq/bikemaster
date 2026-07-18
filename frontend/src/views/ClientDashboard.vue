<!--
  Vista cruscotto dedicata ai client/coach.
  Mostra l'elenco degli atleti associati e permette di assegnare nuovi atleti tramite ID.
  Interfaccia semplice con griglia di card atleta e modulo di assegnazione.
-->
<template>
  <div class="client-dashboard">
    <h2>{{ t("client.title") }}</h2>
    <div class="toolbar">
      <button class="btn-primary" @click="showAssignForm = true">
        {{ t("client.assignAthlete") }}
      </button>
    </div>

    <div v-if="showAssignForm" class="assign-form">
      <h3>{{ t("client.assignAthlete") }}</h3>
      <div class="form-group">
        <label>ID Atleta</label>
        <input v-model.number="assignId" type="number" min="1" />
      </div>
      <div class="form-actions">
        <button
          class="btn-primary"
          @click="assignAthlete"
          :disabled="assigning"
        >
          {{ assigning ? t("common.loading") : t("common.submit") }}
        </button>
        <button class="btn-secondary" @click="showAssignForm = false">
          {{ t("common.cancel") }}
        </button>
      </div>
    </div>

    <div class="athletes-grid">
      <div v-for="a in athletes" :key="a.id" class="athlete-card">
        <div class="athlete-name">{{ a.name || `Atleta ${a.id}` }}</div>
        <div class="athlete-meta">
          {{ a.email || "-" }} | {{ a.experience_level || "-" }}
        </div>
        <div class="athlete-meta">
          ID: {{ a.id }} | Tenant: {{ a.tenant_id }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "../composables/useI18n";
import { apiGet, apiPost } from "../utils/api";
import { useAuthStore } from "../stores/auth";

const { t } = useI18n();
const auth = useAuthStore();

const athletes = ref<
  Array<{
    id: number;
    name: string;
    email: string | null;
    experience_level: string | null;
    tenant_id: number;
  }>
>([]);

const showAssignForm = ref(false);
const assignId = ref<number | "">("");
const assigning = ref(false);

async function loadAthletes() {
  try {
    const data = await apiGet<{ athletes?: Array<{
      id: number;
      name: string;
      email: string | null;
      experience_level: string | null;
      tenant_id: number;
    }> }>("/api/v1/client/athletes", {}, { headers: auth.getAuthHeader() });
    athletes.value = data.athletes || [];
  } catch (e) {
    console.error("Failed to load client athletes", e);
  }
}

async function assignAthlete() {
  if (!assignId.value || assignId.value < 1) return;
  assigning.value = true;
  try {
    await apiPost(
      `/api/v1/client/athletes/${assignId.value}/assign`,
      {},
      { headers: auth.getAuthHeader() },
    );
    showAssignForm.value = false;
    assignId.value = "";
    await loadAthletes();
  } catch (e) {
    console.error("Failed to assign athlete", e);
  } finally {
    assigning.value = false;
  }
}

onMounted(() => {
  loadAthletes();
});
</script>

<style scoped>
.client-dashboard {
  padding: 20px;
}
.toolbar {
  margin-bottom: 16px;
}
.assign-form {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  border: 1px solid var(--border);
}
.form-group {
  margin-bottom: 10px;
}
.form-group label {
  display: block;
  margin-bottom: 4px;
  font-size: 0.85rem;
}
.form-group input {
  padding: 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-primary);
  width: 200px;
}
.form-actions {
  display: flex;
  gap: 8px;
}
.btn-primary {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--accent);
  background: var(--accent-gradient);
  color: #000;
  cursor: pointer;
  font-weight: bold;
}
.btn-secondary {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
}
.athletes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.athlete-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
}
.athlete-name {
  font-weight: bold;
  margin-bottom: 4px;
}
.athlete-meta {
  font-size: 0.85rem;
  color: var(--text-secondary);
}
</style>
