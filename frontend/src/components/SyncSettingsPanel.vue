<template>
  <section class="card sync-card">
    <h2>🔄 Modalità di sincronizzazione</h2>
    <p class="hint">
      Scegli dove risiedono i tuoi dati. <strong>Local (Mai)</strong> tiene
      tutto sul dispositivo: l'app funziona al 100% offline. <strong>Cloud
        sync</strong> abilita la sincronizzazione bidirezionale opzionale con il
      backend cloud.
    </p>

    <div class="sync-toggle" role="radiogroup" aria-label="Sync mode">
      <button
        type="button"
        :class="['sync-option', { active: mode === 'local' }]"
        role="radio"
        :aria-checked="mode === 'local'"
        :disabled="saving"
        @click="setMode('local')"
      >
        <span class="sync-option-icon">📱</span>
        <span class="sync-option-title">Local (Mai)</span>
        <span class="sync-option-desc">100% offline, solo su questo dispositivo</span>
      </button>
      <button
        type="button"
        :class="['sync-option', { active: mode === 'cloud' }]"
        role="radio"
        :aria-checked="mode === 'cloud'"
        :disabled="saving"
        @click="setMode('cloud')"
      >
        <span class="sync-option-icon">☁️</span>
        <span class="sync-option-title">Cloud sync</span>
        <span class="sync-option-desc">Sincronizzazione bidirezionale opzionale</span>
      </button>
    </div>

    <div class="row sync-status-row">
      <span class="badge" :class="statusClass">{{ statusLabel }}</span>
      <span v-if="status.pending_count != null" class="pending">
        {{ status.pending_count }} in attesa
      </span>
      <span v-if="lastSyncLabel" class="last-sync">{{ lastSyncLabel }}</span>
      <button class="btn btn-ghost" :disabled="loading" @click="refresh">
        {{ loading ? "…" : "Aggiorna" }}
      </button>
    </div>

    <p v-if="message" class="status" :class="messageClass">{{ message }}</p>

    <div class="row sync-actions">
      <button class="btn" :disabled="saving || !canImport" @click="exportData">
        Esporta dati
      </button>
      <button class="btn btn-ghost" :disabled="saving" @click="importData">
        Importa uscite
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useToast } from "../composables/useToast";

const auth = useAuthStore();
const toast = useToast();

type SyncMode = "local" | "cloud";

interface SyncStatus {
  mode: SyncMode | string;
  last_sync_at: string | null;
  pending_count: number;
}

const mode = ref<SyncMode>("local");
const loading = ref(false);
const saving = ref(false);
const message = ref("");
const messageClass = ref("");
const status = reactive<SyncStatus>({
  mode: "local",
  last_sync_at: null,
  pending_count: 0,
});

const statusLabel = computed(() => {
  if (status.mode === "cloud") return "Cloud sync";
  if (status.mode === "local") return "Local (Mai)";
  return String(status.mode || "—");
});

const statusClass = computed(() => ({
  "badge-local": status.mode === "local",
  "badge-render": status.mode === "cloud",
}));

const lastSyncLabel = computed(() => {
  if (!status.last_sync_at) return "";
  try {
    const d = new Date(status.last_sync_at);
    return `Ultima sync: ${d.toLocaleString()}`;
  } catch {
    return `Ultima sync: ${status.last_sync_at}`;
  }
});

const canImport = computed(() => !!auth.token);

async function refresh() {
  loading.value = true;
  try {
    const data = await auth.apiFetch<SyncStatus>("/api/v1/sync/status", {
      method: "GET",
    });
    Object.assign(status, {
      mode: data.mode ?? "local",
      last_sync_at: data.last_sync_at ?? null,
      pending_count: data.pending_count ?? 0,
    });
    mode.value = status.mode === "cloud" ? "cloud" : "local";
  } catch (e) {
    toast.error("Impossibile leggere lo stato di sincronizzazione.");
    message.value = (e as Error).message;
    messageClass.value = "err";
  } finally {
    loading.value = false;
  }
}

async function setMode(next: SyncMode) {
  if (next === mode.value) return;
  saving.value = true;
  message.value = "";
  try {
    await auth.apiFetch("/api/v1/sync/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: next }),
    });
    mode.value = next;
    status.mode = next;
    toast.success(
      next === "cloud"
        ? "Modalità Cloud sync attivata."
        : "Modalità Local (Mai) attivata.",
    );
    await refresh();
  } catch (e) {
    message.value = `Impostazione non salvata: ${(e as Error).message}`;
    messageClass.value = "err";
    toast.error("Salvataggio modalità di sync fallito.");
  } finally {
    saving.value = false;
  }
}

async function exportData() {
  try {
    await auth.apiFetch("/api/v1/sync/export", { method: "GET" });
    toast.success("Esportazione avviata.");
  } catch (e) {
    toast.error("Esportazione fallita.");
    message.value = (e as Error).message;
    messageClass.value = "err";
  }
}

async function importData() {
  try {
    await auth.apiFetch("/api/v1/sync/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rides: [] }),
    });
    toast.success("Importazione completata.");
    await refresh();
  } catch (e) {
    toast.error("Importazione fallita.");
    message.value = (e as Error).message;
    messageClass.value = "err";
  }
}

onMounted(() => {
  void refresh();
});
</script>

<style scoped>
.sync-card {
  margin-bottom: 1.2rem;
}
.sync-toggle {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
  margin: 1rem 0;
}
.sync-option {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  align-items: flex-start;
  text-align: left;
  background: #0f0f0f;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 0.9rem 1rem;
  cursor: pointer;
  color: #eee;
  transition: all 0.2s;
}
.sync-option:hover:not(:disabled) {
  border-color: #42b983;
}
.sync-option.active {
  border-color: #42b983;
  box-shadow: 0 0 0 1px #42b983;
  background: #11271d;
}
.sync-option:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.sync-option-icon {
  font-size: 1.4rem;
}
.sync-option-title {
  font-weight: 600;
}
.sync-option-desc {
  font-size: 0.78rem;
  color: #999;
}
.sync-status-row {
  margin-top: 0.4rem;
}
.pending {
  font-size: 0.85rem;
  color: #e7c66e;
}
.last-sync {
  font-size: 0.82rem;
  color: #999;
}
.sync-actions {
  margin-top: 0.8rem;
}
.status {
  margin-top: 0.7rem;
  font-size: 0.85rem;
}
.status.ok {
  color: #42b983;
}
.status.err {
  color: #e57373;
}

/* Reuse SettingsView badge palette */
.badge {
  padding: 0.3rem 0.7rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}
.badge-local {
  background: #1b2a3a;
  color: #6eb8e7;
}
.badge-render {
  background: #1b3a2a;
  color: #6ee7a8;
}

@media (max-width: 480px) {
  .sync-toggle {
    grid-template-columns: 1fr;
  }
}
</style>
