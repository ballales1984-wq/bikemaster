<template>
  <div v-if="auth.isAdmin"
class="admin-panel">
    <div class="panel">
      <h2>⚙️ Administration</h2>

      <div class="admin-grid">
        <button class="admin-card"
@click="$router.push('/admin/users')">
          <div class="admin-icon">👥</div>
          <div class="admin-label">
            {{ t("admin.users") }}
          </div>
          <div class="admin-desc">Manage users and roles</div>
        </button>

        <button class="admin-card"
@click="loadStats" :disabled="loadingStats">
          <div class="admin-icon">📊</div>
          <div class="admin-label">System Stats</div>
          <div class="admin-desc">View database and API metrics</div>
        </button>

        <button class="admin-card"
@click="backupDb">
          <div class="admin-icon">💾</div>
          <div class="admin-label">Backup DB</div>
          <div class="admin-desc">Download database dump</div>
        </button>

        <button
          class="admin-card"
          :disabled="loadingIndexes"
          @click="
            askConfirm(
              'Create Indexes',
              'Rebuild the knowledge base indexes?',
              createIndexes,
            )
          "
        >
          <div class="admin-icon">🗂️</div>
          <div class="admin-label">Create Indexes</div>
          <div class="admin-desc">Rebuild knowledge base indexes</div>
        </button>

        <button
          class="admin-card danger"
          :disabled="loadingReset"
          @click="
            askConfirm(
              'Reset Demo',
              'This will restore demo data and overwrite current data. Continue?',
              resetDemo,
            )
          "
        >
          <div class="admin-icon">🔄</div>
          <div class="admin-label">Reset Demo</div>
          <div class="admin-desc">Restore demo data</div>
        </button>

        <button
          class="admin-card"
          :disabled="loadingAudit"
          @click="loadAuditLogs"
        >
          <div class="admin-icon">📝</div>
          <div class="admin-label">{{ t("admin.auditLogs") }}</div>
          <div class="admin-desc">{{ t("admin.auditLogsDesc") }}</div>
        </button>

        <button
          class="admin-card"
          :disabled="loadingCeo"
          @click="loadCeoAnalytics"
        >
          <div class="admin-icon">📈</div>
          <div class="admin-label">{{ t("admin.ceoAnalytics") }}</div>
          <div class="admin-desc">{{ t("admin.ceoAnalyticsDesc") }}</div>
        </button>

        <button
          class="admin-card"
          :disabled="loadingSentry"
          @click="testSentry"
        >
          <div class="admin-icon">🚨</div>
          <div class="admin-label">{{ t("admin.testSentry") }}</div>
          <div class="admin-desc">{{ t("admin.testSentryDesc") }}</div>
        </button>
      </div>

      <div v-if="stats"
class="result-section">
        <div class="result-header">📋 Statistics Output</div>
        <pre class="result-box">{{ stats }}</pre>
      </div>

      <div v-if="error"
class="error-section">
        <div class="error-icon">⛔</div>
        <div class="error-text">
          {{ error }}
        </div>
      </div>
    </div>

    <ConfirmModal
      v-model="confirmVisible"
      :title="confirmTitle"
      :message="confirmMessage"
      confirm-label="Confirm"
      cancel-label="Cancel"
      @confirm="onConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { useI18n } from "../composables/useI18n";
import { apiGet, apiPost } from "../utils/api";
import ConfirmModal from "./ConfirmModal.vue";

const { t } = useI18n();
const auth = useAuthStore();

const stats = ref("");
const error = ref("");
const loadingStats = ref(false);
const loadingIndexes = ref(false);
const loadingReset = ref(false);
const loadingAudit = ref(false);
const loadingCeo = ref(false);
const loadingSentry = ref(false);
const confirmVisible = ref(false);
const confirmTitle = ref("");
const confirmMessage = ref("");
let pendingAction: (() => void) | null = null;

function askConfirm(title: string, message: string, action: () => void) {
  confirmTitle.value = title;
  confirmMessage.value = message;
  pendingAction = action;
  confirmVisible.value = true;
}

function onConfirm() {
  const action = pendingAction;
  pendingAction = null;
  confirmVisible.value = false;
  action?.();
}

async function loadStats() {
  loadingStats.value = true;
  try {
    error.value = "";
    const data = await apiGet("/api/v1/admin/stats");
    stats.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = "Access denied: " + (e instanceof Error ? e.message : e);
  } finally {
    loadingStats.value = false;
  }
}

async function backupDb() {
  try {
    error.value = "";
    const resp = await fetch("/api/v1/admin/backup", {
      headers: auth.getAuthHeader(),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bikemaster_backup.db";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    error.value = "Backup failed: " + (e instanceof Error ? e.message : e);
  }
}

async function createIndexes() {
  loadingIndexes.value = true;
  try {
    error.value = "";
    await apiPost("/api/v1/admin/indexes", {});
    stats.value = "✅ Indexes created successfully";
  } catch (e) {
    error.value = "Error: " + (e instanceof Error ? e.message : e);
    stats.value = "";
  } finally {
    loadingIndexes.value = false;
  }
}

async function resetDemo() {
  loadingReset.value = true;
  try {
    error.value = "";
    await apiPost("/api/v1/admin/reset-demo", {});
    stats.value = "✅ Demo data restored successfully";
  } catch (e) {
    error.value = "Error: " + (e instanceof Error ? e.message : e);
    stats.value = "";
  } finally {
    loadingReset.value = false;
  }
}

async function loadAuditLogs() {
  loadingAudit.value = true;
  try {
    error.value = "";
    const data = await apiGet("/api/v1/admin/audit-logs");
    stats.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = "Access denied: " + (e instanceof Error ? e.message : e);
  } finally {
    loadingAudit.value = false;
  }
}

async function loadCeoAnalytics() {
  loadingCeo.value = true;
  try {
    error.value = "";
    const data = await apiGet("/api/v1/admin/ceo");
    stats.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = "Access denied: " + (e instanceof Error ? e.message : e);
  } finally {
    loadingCeo.value = false;
  }
}

async function testSentry() {
  loadingSentry.value = true;
  try {
    error.value = "";
    const data = await apiGet("/api/v1/admin/test-sentry");
    stats.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = "Error: " + (e instanceof Error ? e.message : e);
  } finally {
    loadingSentry.value = false;
  }
}
</script>

<style scoped>
.admin-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.admin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-top: 20px;
}

.admin-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 16px;
  text-align: center;
  cursor: pointer;
  transition: var(--transition);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.admin-card:hover:not(:disabled) {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.admin-card.danger {
  border-color: rgba(255, 51, 102, 0.3);
}

.admin-card.danger:hover:not(:disabled) {
  border-color: var(--error);
}

.admin-card:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.admin-icon {
  font-size: 2rem;
}

.admin-label {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.95rem;
}

.admin-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.result-section {
  margin-top: 20px;
}

.result-header {
  color: var(--accent);
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.result-box {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: var(--radius-sm);
  margin-top: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  border-left: 3px solid var(--accent);
  color: var(--text-secondary);
  font-size: 0.85rem;
  max-height: 300px;
  overflow-y: auto;
}

.error-section {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 12px 16px;
  background: rgba(255, 51, 102, 0.1);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--error);
}

.error-icon {
  font-size: 1.2rem;
}

.error-text {
  color: var(--error);
  font-size: 0.9rem;
}
</style>

<style scoped>
.admin-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.admin-section h3 {
  color: var(--text-secondary);
  font-size: 1rem;
  margin-bottom: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.admin-stat-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px 12px;
  text-align: center;
  transition: var(--transition);
}

.admin-stat-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent);
  font-family: "Outfit", sans-serif;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-top: 4px;
  letter-spacing: 0.5px;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.error-box {
  background: rgba(255, 51, 102, 0.1);
  border: 1px solid var(--error);
  border-radius: var(--radius-sm);
  padding: 12px;
  color: var(--error);
}
</style>
