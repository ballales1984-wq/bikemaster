<!-- Pannello import: caricamento file GPX/FIT (drag&drop o selezione) e import da servizi connessi (Strava, Google Fit/Health, Wahoo).
     Props: nessuna. Eventi: summary-change (dopo un import riuscito). Gestisce OAuth via popup e callback; mostra stato, errori e barra di avanzamento.
     UI: area upload, separatore OAuth, gruppi provider con connetti/disconnetti/sync, box risultato ed eventuale progress bar. -->
<template>
  <section>
    <div class="panel">
      <h2>Import Routes</h2>

      <div class="form-group">
        <label for="import-file">Carica file GPX o FIT</label>
        <div
          class="upload-area"
          @click="pickFile"
          @dragover.prevent
          @drop.prevent="onDrop"
        >
          <input
            id="import-file"
            ref="fileInput"
            type="file"
            accept=".gpx,.fit"
            multiple
            @change="onChange"
          />
          <div class="upload-placeholder">
            {{ label }}
          </div>
        </div>
      </div>

      <div
        v-if="importStatus?.message || status"
        class="result-box"
        :class="importStatus?.success ? 'success' : 'error'"
      >
        {{ importStatus?.message || status }}
      </div>
      <div class="form-actions">
        <button
          class="btn btn-primary"
          :disabled="!files.length || uploading"
          @click="upload"
        >
          {{ uploading ? "Importing..." : "Import selected files" }}
        </button>
      </div>

      <div class="oauth-separator">
        <span>or import from connected services</span>
      </div>

      <div v-if="isServiceAvailable('google_fit')" class="provider-group">
        <h3>Google Fit</h3>
        <button
          class="btn btn-google-fit"
          :disabled="importing"
          type="button"
          @click="connectGoogleFit"
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            style="margin-right: 6px"
          >
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.76h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c3.05 0 5.84-1.15 7.86-3l-3.57-2.76c-.98.66-2.23 1.06-3.62 1.44v2.26C15.24 21.23 13.71 22 12 22z"
            />
            <path
              fill="#FBBC05"
              d="M6.27 15.73a7.5 7.5 0 0 1 0-3.46l2.93-2.27a7.5 7.5 0 0 0 1.74 3.19l-2.93 2.27z"
            />
            <path
              fill="#EA4335"
              d="M18.57 6.43a7.5 7.5 0 0 0-6.57-4.43 7.5 7.5 0 0 0-1.57.23l2.93 2.26a4.99 4.99 0 0 1 5.17 4.17z"
            />
          </svg>
          {{ importing ? "Connecting..." : "Import from Google Fit" }}
        </button>
        <button
          class="btn btn-secondary"
          :disabled="importing"
          type="button"
          style="margin-top: 8px"
          @click="disconnectGoogleFit"
        >
          Disconnect Google Fit
        </button>
      </div>
      <div v-else class="provider-group provider-group--muted">
        <h3>Google Fit</h3>
        <p class="provider-hint">
          Coming soon: configure Google Fit credentials to enable import.
        </p>
      </div>

      <div v-if="isServiceAvailable('wahoo')" class="provider-group">
        <h3>Wahoo</h3>
        <button
          class="btn btn-secondary"
          :disabled="importing"
          type="button"
          @click="connectWahoo"
        >
          Connect Wahoo
        </button>
        <button
          class="btn btn-secondary"
          :disabled="importing"
          type="button"
          style="margin-top: 8px"
          @click="disconnectWahoo"
        >
          Disconnect Wahoo
        </button>
        <button
          class="btn btn-primary"
          :disabled="importing"
          type="button"
          style="margin-top: 8px"
          @click="wahooSync"
        >
          Import from Wahoo
        </button>
      </div>
      <div v-else class="provider-group provider-group--muted">
        <h3>Wahoo</h3>
        <p class="provider-hint">
          Coming soon: configure Wahoo credentials to enable import.
        </p>
      </div>

      <div v-if="isServiceAvailable('google_health')" class="provider-group">
        <h3>Google Health</h3>
        <button
          class="btn btn-google-fit"
          :disabled="importing"
          type="button"
          @click="connectGoogleHealth"
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            style="margin-right: 6px"
          >
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.76h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c3.05 0 5.84-1.15 7.86-3l-3.57-2.76c-.98.66-2.23 1.06-3.62 1.44v2.26C15.24 21.23 13.71 22 12 22z"
            />
            <path
              fill="#FBBC05"
              d="M6.27 15.73a7.5 7.5 0 0 1 0-3.46l2.93-2.27a7.5 7.5 0 0 0 1.74 3.19l-2.93 2.27z"
            />
            <path
              fill="#EA4335"
              d="M18.57 6.43a7.5 7.5 0 0 0-6.57-4.43 7.5 7.5 0 0 0-1.57.23l2.93 2.26a4.99 4.99 0 0 1 5.17 4.17z"
            />
          </svg>
          {{ importing ? "Connecting..." : "Import from Google Health" }}
        </button>
        <button
          class="btn btn-secondary"
          :disabled="importing"
          type="button"
          style="margin-top: 8px"
          @click="disconnectGoogleHealth"
        >
          Disconnect Google Health
        </button>
      </div>
      <div v-else class="provider-group provider-group--muted">
        <h3>Google Health</h3>
        <p class="provider-hint">
          Coming soon: configure Google Health credentials to enable import.
        </p>
      </div>

      <div v-if="isServiceAvailable('strava')" class="provider-group">
        <h3>Strava</h3>
        <button
          class="btn btn-strava"
          :disabled="importing"
          type="button"
          @click="connectStrava"
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            style="margin-right: 6px"
            aria-hidden="true"
          >
            <path fill="#FC5200" d="M13.5 16l-2.5 2.5L8.5 16l2.5-2.5z" />
            <path fill="#FC5200" d="M18 11.5L15.5 14 13 11.5l2.5-2.5z" />
          </svg>
          {{ importing ? "Connecting..." : "Connect Strava" }}
        </button>
        <button
          class="btn btn-secondary"
          :disabled="importing"
          type="button"
          style="margin-top: 8px"
          @click="disconnectStrava"
        >
          Disconnect Strava
        </button>
        <button
          class="btn btn-primary"
          :disabled="importing"
          type="button"
          style="margin-top: 8px"
          @click="stravaSync"
        >
          Import from Strava
        </button>
      </div>
      <div v-else class="provider-group provider-group--muted">
        <h3>Strava</h3>
        <p class="provider-hint">
          Coming soon: configure Strava credentials to enable import.
        </p>
      </div>

      <div
        v-if="uploading || uploadProgress > 0"
        class="progress-track"
        aria-label="Import progress"
      >
        <div class="progress-fill" :style="{ width: uploadProgress + '%' }" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { apiUpload } from "../utils/api";
import { useAuthStore } from "../stores/auth";
import { useConnectionsStore } from "../stores/connections";
import {
  useOAuthConnection,
  oauthProviders,
} from "../composables/useOAuthConnection";

const auth = useAuthStore();
const connectionsStore = useConnectionsStore();

const stravaOAuth = useOAuthConnection(oauthProviders.strava);
const googleFitOAuth = useOAuthConnection(oauthProviders.google_fit);
const googleHealthOAuth = useOAuthConnection(oauthProviders.google_health);
const wahooOAuth = useOAuthConnection(oauthProviders.wahoo);

const emit = defineEmits(["summary-change"]);
const fileInput = ref<HTMLInputElement | null>(null);
const files = ref<File[]>([]);
const status = ref("");
const uploading = ref(false);
const uploadProgress = ref(0);
const importing = ref(false);
const importStatus = ref<{ success: boolean; message: string } | null>(null);
const services = computed(() => connectionsStore.services);

function isServiceAvailable(service: string): boolean {
  return services.value.some((s) => s.service === service && s.available);
}

const label = computed(() => {
  if (!files.value.length)
    return "Drag files here or click to select (GPX/FIT)";
  return `${files.value.length} files selected`;
});

function pickFile() {
  fileInput.value?.click();
}

function onChange(e: Event) {
  files.value = Array.from((e.target as HTMLInputElement).files || []);
}

function onDrop(e: DragEvent) {
  files.value = Array.from(e.dataTransfer?.files || []);
}

onMounted(async () => {
  await connectionsStore.load();
});

async function uploadOne(file: File) {
  const ext = file.name.toLowerCase().split(".").pop();
  const path = ext === "fit" ? "/api/v1/import/fit" : "/api/v1/import/gpx";
  return apiUpload(path, file);
}

async function upload() {
  if (!files.value.length || uploading.value) return;
  try {
    uploading.value = true;
    uploadProgress.value = 0;
    status.value = "Import in progress...";
    for (let i = 0; i < files.value.length; i += 1) {
      await uploadOne(files.value[i]);
      uploadProgress.value = Math.round(((i + 1) / files.value.length) * 100);
      status.value = `Imported ${i + 1} of ${files.value.length} files`;
    }
    status.value = "Import completed";
    files.value = [];
    emit("summary-change");
  } catch (e: unknown) {
    status.value =
      "Import failed: " + (e instanceof Error ? e.message : String(e));
  } finally {
    uploading.value = false;
  }
}

async function connectGoogleFit() {
  importing.value = true;
  importStatus.value = null;
  try {
    await googleFitOAuth.connect();
    importStatus.value = {
      success: true,
      message: "Google Fit connected",
    };
    emit("summary-change");
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message: e instanceof Error ? e.message : String(e),
    };
  } finally {
    importing.value = false;
  }
}

async function connectGoogleHealth() {
  importing.value = true;
  importStatus.value = null;
  try {
    await googleHealthOAuth.connect();
    importStatus.value = {
      success: true,
      message: "Google Health connected",
    };
    emit("summary-change");
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message: e instanceof Error ? e.message : String(e),
    };
  } finally {
    importing.value = false;
  }
}

async function disconnectGoogleFit() {
  try {
    await googleFitOAuth.disconnect();
    importStatus.value = {
      success: true,
      message: "Google Fit disconnected",
    };
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message:
        e instanceof Error ? e.message : "Failed to disconnect Google Fit",
    };
  }
}

async function disconnectGoogleHealth() {
  try {
    await googleHealthOAuth.disconnect();
    importStatus.value = {
      success: true,
      message: "Google Health disconnected",
    };
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message:
        e instanceof Error ? e.message : "Failed to disconnect Google Health",
    };
  }
}

async function connectStrava() {
  importing.value = true;
  importStatus.value = null;
  try {
    await stravaOAuth.connect();
    importStatus.value = {
      success: true,
      message: "Strava connected. Importing your rides...",
    };
    importing.value = false;
    await stravaSync();
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message: e instanceof Error ? e.message : "Strava connection failed",
    };
    importing.value = false;
  }
}

async function stravaSync() {
  if (importing.value) return;
  try {
    importing.value = true;
    const token = auth.token;
    const resp = await fetch("/api/v1/import/strava/sync?background=false", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (resp.ok) {
      const result = await resp.json();
      importStatus.value = {
        success: true,
        message: `Imported ${result.imported} rides from Strava (${result.total_fetched} fetched)`,
      };
      emit("summary-change");
    } else {
      const err = await resp.json().catch(() => ({}));
      importStatus.value = {
        success: false,
        message: err.detail || "Strava sync failed",
      };
    }
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message:
        "Strava sync error: " + (e instanceof Error ? e.message : String(e)),
    };
  } finally {
    importing.value = false;
  }
}

async function disconnectStrava() {
  try {
    await stravaOAuth.disconnect();
    importStatus.value = { success: true, message: "Strava disconnected" };
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message: e instanceof Error ? e.message : "Failed to disconnect Strava",
    };
  }
}

async function connectWahoo() {
  importing.value = true;
  importStatus.value = null;
  try {
    await wahooOAuth.connect();
    importStatus.value = {
      success: true,
      message: "Wahoo connected successfully",
    };
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message: e instanceof Error ? e.message : String(e),
    };
  } finally {
    importing.value = false;
  }
}

async function disconnectWahoo() {
  try {
    await wahooOAuth.disconnect();
    importStatus.value = { success: true, message: "Wahoo disconnected" };
  } catch (e: unknown) {
    importStatus.value = {
      success: false,
      message: e instanceof Error ? e.message : "Failed to disconnect Wahoo",
    };
  }
}

async function wahooSync() {
  if (importing.value) return;
  try {
    importing.value = true;
    status.value = "Wahoo import in progress...";
    const token = auth.token;
    const resp = await fetch("/api/v1/import/wahoo/sync", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (resp.ok) {
      const result = await resp.json();
      status.value = `Imported ${result.imported} rides from Wahoo`;
      emit("summary-change");
    } else {
      const err = await resp.json().catch(() => ({}));
      status.value = "Wahoo import failed: " + (err.detail || resp.statusText);
    }
  } catch (e: unknown) {
    status.value =
      "Wahoo import error: " + (e instanceof Error ? e.message : String(e));
  } finally {
    importing.value = false;
  }
}
</script>

<style scoped>
.panel {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.upload-area {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  background: var(--bg-tertiary);
  transition: all 0.2s;
}

.upload-area:hover {
  background: var(--border);
}

.upload-placeholder {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.form-actions {
  margin: 12px 0;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent);
  color: var(--bg-primary);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--border);
}

.btn-google-fit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 10px 16px;
  background: #fff;
  color: #444;
  border: 1px solid #dadce0;
  margin-top: 12px;
}

.btn-google-fit:hover:not(:disabled) {
  background: #f8f9fa;
}

.btn-strava {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 10px 16px;
  background: #fc5200;
  color: #fff;
}

.btn-strava:hover:not(:disabled) {
  background: #e64a00;
}

.progress-track {
  width: 100%;
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  margin-top: 16px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s;
}

.result-box {
  margin-top: 12px;
  padding: 12px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

.result-box.success {
  background: rgba(66, 183, 77, 0.1);
  border: 1px solid var(--success);
  color: var(--success);
}

.result-box.error {
  background: rgba(234, 67, 53, 0.1);
  border: 1px solid var(--error);
  color: var(--error);
}

.oauth-separator {
  display: flex;
  align-items: center;
  margin: 20px 0;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.oauth-separator span {
  padding: 0 12px;
}

.oauth-separator::before,
.oauth-separator::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--border);
}

.provider-group {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
}

.provider-group h3 {
  margin: 0 0 10px;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.provider-group--muted {
  opacity: 0.7;
}

.provider-hint {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
}
</style>
