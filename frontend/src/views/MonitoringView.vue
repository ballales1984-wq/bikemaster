<template>
  <div class="monitoring-page">
    <div class="monitoring-header">
      <h1>{{ t("monitoring.title") }}</h1>
      <div class="monitoring-actions">
        <button
          class="btn btn-ghost"
          :disabled="store.loading"
          @click="store.fetchHealth"
        >
          {{ store.loading ? t("common.loading") : t("monitoring.refresh") }}
        </button>
        <span v-if="store.lastUpdated" class="last-updated">
          {{ t("monitoring.lastUpdated") }}: {{ store.lastUpdated }}
        </span>
      </div>
    </div>

    <div class="monitoring-grid">
      <div class="card status-card" :class="overallStatusClass">
        <div class="status-icon">{{ overallStatusIcon }}</div>
        <div class="status-content">
          <div class="status-label">{{ t("monitoring.overallStatus") }}</div>
          <div class="status-value">{{ overallStatusText }}</div>
        </div>
      </div>

      <div v-for="check in healthChecks" :key="check.key" class="card">
        <div class="check-header">
          <span class="check-icon">{{ check.icon }}</span>
          <span class="check-label">{{ check.label }}</span>
        </div>
        <div class="check-status" :class="check.statusClass">
          {{ check.status }}
        </div>
        <div v-if="check.message" class="check-message">
          {{ check.message }}
        </div>
      </div>

      <div v-if="diskInfo" class="card">
        <div class="check-header">
          <span class="check-icon">💾</span>
          <span class="check-label">{{ t("monitoring.disk") }}</span>
        </div>
        <div class="check-message">
          <div>Path: {{ diskInfo.db_path }}</div>
          <div>Exists: {{ diskInfo.db_exists ? "Yes" : "No" }}</div>
          <div v-if="diskInfo.db_size_bytes !== undefined">
            Size: {{ formatBytes(toNumber(diskInfo.db_size_bytes)) }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="store.error" class="card">
      <div class="error-section">
        <div class="error-icon">⚠️</div>
        <div class="error-text">{{ store.error }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from "vue";
import { useI18n } from "../composables/useI18n";
import { useMonitoringStore } from "../stores/monitoring";

const { t } = useI18n();
const store = useMonitoringStore();

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function statusClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "healthy" || s === "ok") return "status-ok";
  if (s === "degraded" || s === "warning") return "status-warn";
  if (s === "unhealthy" || s === "error") return "status-error";
  return "status-unknown";
}

const healthChecks = computed(() => {
  if (!store.health || !store.health.checks) return [];
  const checks = (store.health.checks as Record<string, string>) || {};
  const icons: Record<string, string> = {
    database: "🗄️",
    redis: "📦",
    task_queue: "📋",
  };
  return Object.entries(checks).map(([key, raw]) => {
    const parts = raw.split(":", 2);
    const status = parts[0] ?? "unknown";
    const message = parts[1]?.trim() ?? "";
    return {
      key,
      label: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " "),
      icon: icons[key] || "🔌",
      status,
      message,
      statusClass: statusClass(status),
    };
  });
});

const overallStatus = computed(() => {
  if (!store.health) return "unknown";
  if (store.health.healthy) return "healthy";
  return "unhealthy";
});

const overallStatusClass = computed(() => {
  return statusClass(overallStatus.value);
});

const overallStatusText = computed(() => {
  if (overallStatus.value === "healthy") return t("monitoring.healthy");
  if (overallStatus.value === "unhealthy") return t("monitoring.unhealthy");
  return t("monitoring.unknown");
});

const diskInfo = computed(() => {
  if (!store.health || !store.health.disk) return null;
  return store.health.disk as Record<string, unknown>;
});

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value ?? 0);
}

onMounted(() => {
  store.fetchHealth();
  store.startAutoRefresh();
});

onUnmounted(() => {
  store.stopAutoRefresh();
});
</script>

<style scoped>
.monitoring-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.monitoring-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.monitoring-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.monitoring-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.last-updated {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.monitoring-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-icon {
  font-size: 2.5rem;
  line-height: 1;
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.check-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.check-icon {
  font-size: 1.2rem;
}

.check-label {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.95rem;
}

.check-status {
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 4px;
}

.check-message {
  font-size: 0.8rem;
  color: var(--text-muted);
  white-space: pre-wrap;
  word-break: break-word;
}

.status-ok {
  color: #00ff88;
}

.status-warn {
  color: #ffaa00;
}

.status-error {
  color: #ff3366;
}

.status-unknown {
  color: var(--text-muted);
}

.error-section {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 16px;
  background: rgba(255, 51, 102, 0.1);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--error);
}

.error-icon {
  font-size: 1.2rem;
  line-height: 1.4;
}

.error-text {
  color: var(--error);
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .monitoring-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .monitoring-grid {
    grid-template-columns: 1fr;
  }
}
</style>
