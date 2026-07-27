<!-- Sync settings panel: chooses between "Local (Never)" mode (100% offline) and "Cloud sync" (optional bidirectional).
     Props: none. Events: none (uses auth.apiFetch /api/v1/sync). Shows sync status, pending items, last sync and export/import actions.
     UI: radiogroup of two options, status row with badge, messages and Export/Import rides actions. -->
<template>
  <section class="card sync-card">
    <h2>{{ t("sync.modeTitle") }}</h2>
    <p class="hint">
      {{ t("sync.modeHint") }}
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
        <span class="sync-option-icon"></span>
        <span class="sync-option-title">{{ t("sync.localTitle") }}</span>
        <span class="sync-option-desc">{{ t("sync.localDesc") }}</span>
      </button>
      <button
        type="button"
        :class="['sync-option', { active: mode === 'cloud' }]"
        role="radio"
        :aria-checked="mode === 'cloud'"
        :disabled="saving"
        @click="setMode('cloud')"
      >
        <span class="sync-option-icon"></span>
        <span class="sync-option-title">{{ t("sync.cloudTitle") }}</span>
        <span class="sync-option-desc">{{ t("sync.cloudDesc") }}</span>
      </button>
    </div>

    <div class="row sync-status-row">
      <span class="badge" :class="statusClass">{{ statusLabel }}</span>
      <span v-if="status.pending_count != null" class="pending">
        {{ t("sync.pending") }}: {{ status.pending_count }}
      </span>
      <span v-if="lastSyncLabel" class="last-sync">{{ lastSyncLabel }}</span>
      <button class="btn btn-ghost" :disabled="loading" @click="refresh">
        {{ loading ? "…" : t("sync.refresh") }}
      </button>
    </div>

    <p v-if="message" class="status" :class="messageClass">{{ message }}</p>

    <div class="row sync-actions">
      <button class="btn" :disabled="saving || !canImport" @click="exportData">
        {{ t("sync.export") }}
      </button>
      <button class="btn btn-ghost" :disabled="saving" @click="importData">
        {{ t("sync.import") }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useToast } from "../composables/useToast";
import { useI18n } from "../composables/useI18n";

const auth = useAuthStore();
const toast = useToast();
const { t } = useI18n();

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
  if (status.mode === "cloud") return "Sincronizzazione cloud";
  if (status.mode === "local") return t("sync.localTitle");
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
    return `Ultima sincronizzazione: ${d.toLocaleString()}`;
  } catch {
    return `Ultima sincronizzazione: ${status.last_sync_at}`;
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
    toast.error(t("sync.readError"));
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
      next === "cloud" ? t("sync.cloudActivated") : t("sync.localActivated"),
    );
    await refresh();
  } catch (e) {
    message.value = `Setting not saved: ${(e as Error).message}`;
    messageClass.value = "err";
    toast.error(t("sync.saveError"));
  } finally {
    saving.value = false;
  }
}

async function exportData() {
  try {
    await auth.apiFetch("/api/v1/sync/export", { method: "GET" });
    toast.success(t("sync.exportStarted"));
  } catch (e) {
    toast.error(t("sync.exportFailed"));
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
    toast.success(t("sync.importDone"));
    await refresh();
  } catch (e) {
    toast.error(t("sync.importFailed"));
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
