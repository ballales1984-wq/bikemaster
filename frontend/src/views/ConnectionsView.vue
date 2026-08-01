<!--
  Vista di gestione delle connessioni con servizi esterni.
  Consente di connettere/disconnettere servizi (Strava, Google Fit, Google Health, Wahoo)
  tramite OAuth o di configurare chiavi API personali.
  Include anche l'importazione massiva di chiavi.
  Store: connectionsStore, apiKeysStore, authStore.
-->
<template>
  <div class="connections-page">
    <h1>{{ t("connections.title") }}</h1>
    <p class="subtitle">
      {{ t("connections.subtitle") }}
    </p>

    <div class="connections-grid">
      <div
        v-for="service in services"
        :key="service.service"
        class="connection-card"
        :class="{
          connected: service.connected,
          oauth: service.method === 'oauth',
          apikey: service.method === 'apikey',
        }"
      >
        <div class="connection-header">
          <span class="connection-icon">{{
            serviceIcons[service.service] || ""
          }}</span>
          <div class="connection-title">
            <div class="connection-name">
              {{ service.label }}
            </div>
            <div class="connection-method">
              <span
                class="badge"
                :class="
                  service.method === 'oauth' ? 'badge-oauth' : 'badge-apikey'
                "
              >
                {{
                  service.method === "oauth"
                    ? t("connections.oauth")
                    : t("connections.apiKey")
                }}
              </span>
            </div>
          </div>
        </div>

        <p v-if="service.description" class="connection-desc">
          {{ service.description }}
        </p>

        <div class="connection-status">
          <span
            class="status-dot"
            :class="service.connected ? 'online' : 'offline'"
          />
          <span class="status-text">
            {{
              service.connected
                ? t("connections.connected")
                : t("connections.disconnected")
            }}
          </span>
          <span v-if="service.lastConnectedAt" class="last-connected">
            {{ formatDate(service.lastConnectedAt) }}
          </span>
        </div>

        <!-- Servizi OAuth -->
        <template v-if="service.method === 'oauth'">
          <div v-if="!service.connected" class="connection-actions">
            <button
              class="btn btn-primary"
              :disabled="connecting === service.service"
              @click="startOAuth(service.service)"
            >
              {{
                connecting === service.service
                  ? t("connections.connecting")
                  : t("connections.connect")
              }}
            </button>
          </div>
          <div v-else class="connection-actions">
            <button
              class="btn btn-danger"
              :disabled="disconnecting === service.service"
              @click="disconnectService(service.service)"
            >
              {{
                disconnecting === service.service
                  ? t("connections.disconnecting")
                  : t("connections.disconnect")
              }}
            </button>
          </div>
        </template>

        <!-- Servizi API Key -->
        <template v-if="service.method === 'apikey'">
          <form class="apikey-form" @submit.prevent>
            <label class="key-field">
              <span class="key-label">{{ service.label }} API Key</span>
              <input
                v-model="apikeyDrafts[service.service]"
                class="text-input"
                :type="showKeys ? 'text' : 'password'"
                :readonly="!keysLoaded"
                :placeholder="t('connections.apiKeyPlaceholder')"
                autocomplete="off"
              />
            </label>
            <div class="apikey-actions">
              <button
                class="btn btn-primary"
                :disabled="savingKey === service.service"
                @click="saveApiKey(service.service)"
              >
                {{
                  savingKey === service.service
                    ? t("connections.saving")
                    : t("connections.saveKey")
                }}
              </button>
              <button
                class="btn btn-ghost"
                :disabled="!hasKey(service.service)"
                @click="clearApiKey(service.service)"
              >
                {{ t("connections.clearKey") }}
              </button>
            </div>
          </form>
        </template>

        <div v-if="serviceError === service.service" class="connection-error">
          {{ lastServiceError }}
        </div>
      </div>
    </div>

    <section class="card bulk-section">
      <h2>{{ t("connections.bulkTitle") }}</h2>
      <p class="hint">
        {{ t("connections.bulkHint") }}
      </p>
      <textarea
        v-model="bulkInput"
        class="bulk-input"
        rows="5"
        :placeholder="t('connections.bulkPlaceholder')"
      />
      <div class="row key-actions">
        <button class="btn" :disabled="importingBulk" @click="importBulkKeys">
          {{
            importingBulk
              ? t("connections.importing")
              : t("connections.importBulk")
          }}
        </button>
        <span class="status" :class="bulkStatusClass">{{ bulkStatus }}</span>
      </div>
    </section>

    <section class="devices-section">
      <h2>{{ t("connections.devicesTitle") }}</h2>
      <p class="subtitle">
        {{ t("connections.devicesSubtitle") }}
      </p>

      <div class="devices-row">
        <div class="device-card ble-card">
          <div class="device-header">
            <span class="device-icon">&#x1F4F1;</span>
            <div>
              <div class="device-name">Bluetooth BLE</div>
              <div class="device-meta">
                {{ bleStore.devices.length }} dispositivo(i)
              </div>
            </div>
          </div>

          <div class="device-actions">
            <button
              class="btn btn-primary"
              :disabled="bleStore.scanning || !bleAvailable"
              @click="scanBleDevices"
            >
              {{
                bleStore.scanning
                  ? t("connections.scanning")
                  : t("connections.scanBle")
              }}
            </button>
            <button
              v-if="scannedBleDevice"
              class="btn btn-primary"
              :disabled="bleStore.loading"
              @click="registerBleDevice"
            >
              {{ t("connections.pairBle") }}
            </button>
          </div>

          <div v-if="bleStore.error" class="connection-error">
            {{ bleStore.error }}
          </div>

          <div class="device-list">
            <div
              v-for="device in bleStore.devices"
              :key="device.id"
              class="device-item"
            >
              <div class="device-info">
                <span class="device-name">{{
                  device.name || device.device_id
                }}</span>
                <span class="device-type">{{
                  bleStore.getDeviceTypeLabel(device.device_type)
                }}</span>
              </div>
              <div class="device-status">
                <span
                  class="status-dot"
                  :class="device.paired ? 'online' : 'offline'"
                />
                <button
                  class="btn btn-ghost btn-sm"
                  :disabled="bleStore.loading"
                  @click="bleStore.sync(device.id)"
                >
                  {{ t("connections.sync") }}
                </button>
                <button
                  class="btn btn-danger btn-sm"
                  :disabled="bleStore.loading"
                  @click="removeBleDevice(device)"
                >
                  {{ t("connections.remove") }}
                </button>
              </div>
            </div>
            <div
              v-if="!bleStore.devices.length && !bleStore.loading"
              class="empty-hint"
            >
              {{ t("connections.noBleDevices") }}
            </div>
          </div>
        </div>

        <div class="device-card health-card">
          <div class="device-header">
            <span class="device-icon">&#x2764;&#xFE0F;</span>
            <div>
              <div class="device-name">Android Health Connect</div>
              <div class="device-meta">
                {{
                  healthConnect.status.connected
                    ? t("connections.connected")
                    : t("connections.disconnected")
                }}
              </div>
            </div>
          </div>

          <div class="device-actions">
            <button
              v-if="!healthConnect.status.connected"
              class="btn btn-primary"
              :disabled="
                healthConnect.loading || !healthConnect.status.available
              "
              @click="connectHealthConnect"
            >
              {{
                healthConnect.loading
                  ? t("connections.connecting")
                  : t("connections.connectHealth")
              }}
            </button>
            <template v-else>
              <button
                class="btn btn-primary"
                :disabled="healthConnect.loading"
                @click="syncHealthConnect"
              >
                {{ t("connections.syncHealth") }}
              </button>
              <button
                class="btn btn-danger"
                :disabled="healthConnect.loading"
                @click="healthConnect.disconnect()"
              >
                {{ t("connections.disconnect") }}
              </button>
            </template>
          </div>

          <div v-if="healthConnect.error" class="connection-error">
            {{ healthConnect.error }}
          </div>

          <div v-if="healthConnect.status.connected" class="permission-list">
            <div class="permission-label">
              {{ t("connections.grantedPermissions") }}:
            </div>
            <div class="permission-tags">
              <span
                v-for="perm in healthConnect.status.permissions"
                :key="perm"
                class="permission-tag"
              >
                {{ healthConnect.getPermissionLabel(perm) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useI18n } from "../composables/useI18n";
import { useConnectionsStore } from "../stores/connections";
import { useApiKeysStore } from "../stores/apiKeys";
import { useBleStore } from "../stores/ble";
import type { BleDeviceType } from "../stores/ble";
import { useHealthConnectStore } from "../stores/healthConnect";
import { useToast } from "../composables/useToast";
import { useAuthStore } from "../stores/auth";
import { parseBulkKeys } from "../utils/userKeys";

const { t } = useI18n();
const connectionsStore = useConnectionsStore();
const apiKeysStore = useApiKeysStore();
const bleStore = useBleStore();
const healthConnect = useHealthConnectStore();
const authStore = useAuthStore();
const toast = useToast();

const services = computed(() => connectionsStore.services);

const connecting = ref("");
const disconnecting = ref("");
const savingKey = ref("");
const serviceError = ref("");
const lastServiceError = ref("");
const showKeys = ref(false);
const importingBulk = ref(false);
const bulkInput = ref("");
const bulkStatus = ref("");
const bulkStatusClass = ref("");
const keysLoaded = ref(false);

const apikeyDrafts: Record<string, string> = reactive({});

const serviceIcons: Record<string, string> = {
  strava: "",
  google_fit: "",
  google_health: "",
  wahoo: "",
  garmin: "",
};

const bleAvailable = ref(false);
const scannedBleDevice = ref<{
  deviceId: string;
  name: string;
  type: BleDeviceType;
} | null>(null);

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  try {
    const d = new Date(value);
    return d.toLocaleString();
  } catch {
    return String(value);
  }
}

function setServiceError(message: string, serviceName?: string) {
  lastServiceError.value = message;
  serviceError.value = serviceName || "";
}

function clearServiceError() {
  serviceError.value = "";
  lastServiceError.value = "";
}

async function startOAuth(service: string) {
  connecting.value = service;
  clearServiceError();
  try {
    if (service === "strava") {
      await connectStrava();
    } else if (service === "google_fit") {
      await connectGoogleFit();
    } else if (service === "google_health") {
      await connectGoogleHealth();
    } else if (service === "wahoo") {
      await connectWahoo();
    } else {
      throw new Error(`OAuth non supportato per ${service}`);
    }
    await connectionsStore.load();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setServiceError(msg, service);
    toast.error(msg);
  } finally {
    connecting.value = "";
  }
}

async function connectStrava() {
  const token = authStore.token;
  const headers: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};
  const redirectUri = `${import.meta.env.DEV ? "http://localhost:8000" : window.location.origin}/api/v1/import/strava/callback`;
  const authResp = await fetch(
    `/api/v1/import/strava/auth?redirect_uri=${encodeURIComponent(redirectUri)}`,
    { headers },
  );
  if (!authResp.ok) {
    const err = await authResp.json().catch(() => ({}));
    throw new Error(
      err.detail || "Impossibile avviare l'autenticazione Strava",
    );
  }
  const { auth_url, code_verifier } = await authResp.json();
  const popup = window.open(auth_url, "strava-auth", "width=600,height=700");
  if (!popup) throw new Error("Popup bloccato - abilita i popup");

  const code = await new Promise<string>((resolve, reject) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", handleMessage);
      window.removeEventListener("storage", handleStorage);
      clearInterval(pollTimer);
    };
    const timer = setTimeout(
      () => {
        finish();
        if (popup && !popup.closed) {
          try {
            popup.close();
          } catch (_) {
            /* ignore */
          }
        }
        reject(
          new Error(
            "Timeout: autenticazione Strava annullata. " +
              "Il popup potrebbe essere bloccato. Prova ad abilitare i popup per questo sito e riprova.",
          ),
        );
      },
      5 * 60 * 1000,
    );
    const pollTimer = setInterval(() => {
      if (popup && popup.closed && !settled) {
        finish();
        reject(
          new Error(
            "L'autenticazione Strava è stata annullata o il popup è stato chiuso.",
          ),
        );
      }
    }, 1000);
    const handleMessage = (event: MessageEvent) => {
      if (!event.data || event.data.type !== "strava-success") {
        if (event.data?.type === "strava-error") {
          finish();
          reject(
            new Error(
              event.data.error_description ||
                event.data.error ||
                "Strava OAuth fallito",
            ),
          );
        }
        return;
      }
      finish();
      resolve(event.data.code);
      clearTimeout(timer);
      try {
        localStorage.removeItem("bikemaster_oauth_result");
      } catch (e) {
        /* ignore */
      }
      if (popup && !popup.closed) {
        popup.close();
      }
    };
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== "bikemaster_oauth_result" || !event.newValue) return;
      try {
        handleMessage({ data: JSON.parse(event.newValue) } as MessageEvent);
      } catch (e) {
        /* ignore */
      }
    };
    window.addEventListener("message", handleMessage);
    window.addEventListener("storage", handleStorage);
  });

  const cbResp = await fetch("/api/v1/import/strava/callback", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ code, code_verifier }),
  });
  if (!cbResp.ok) {
    const err = await cbResp.json().catch(() => ({}));
    const detail: string = (err as { detail?: string }).detail || "";
    if (cbResp.status === 502 && /Authorization Error|invalid/i.test(detail)) {
      throw new Error(
        "Strava rejected the connection: the BikeMaster app is in sandbox mode. " +
          "Open strava.com/settings/api, enter the BikeMaster app and add your " +
          "Strava account to 'Athlete Testers', then try again.",
      );
    }
    throw new Error(detail || "Strava connection failed");
  }
  toast.success("Strava connected");
}

async function connectGoogleFit() {
  const redirectUri = `${import.meta.env.DEV ? "http://localhost:8000" : window.location.origin}/api/v1/import/google-fit/callback`;
  const state = btoa(JSON.stringify({ redirect_uri: redirectUri }));
  const authResp = await fetch(
    `/api/v1/import/google-fit/auth?redirect_uri=${encodeURIComponent(redirectUri)}&state=${encodeURIComponent(state)}`,
  );
  if (!authResp.ok) {
    throw new Error("Impossibile avviare l'autenticazione Google Fit");
  }
  const { auth_url } = await authResp.json();
  const popup = window.open(
    auth_url,
    "google-fit-auth",
    "width=500,height=600",
  );
  if (!popup) throw new Error("Popup bloccato - abilita i popup");

  await new Promise<void>((resolve, reject) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", handleMessage);
      window.removeEventListener("storage", handleStorage);
      clearTimeout(timer);
    };
    const timer = setTimeout(
      () => {
        finish();
        reject(new Error("Timeout: autenticazione Google Fit annullata"));
      },
      5 * 60 * 1000,
    );
    const handleMessage = async (event: MessageEvent) => {
      if (event.data?.type === "google-fit-error") {
        finish();
        reject(
          new Error(
            event.data.error_description ||
              event.data.error ||
              "Errore Google Fit",
          ),
        );
        return;
      }
      if (event.data?.type === "google-fit-success") {
        finish();
        const token = authStore.token;
        const importResp = await fetch("/api/v1/import/google-fit", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            access_token: event.data.token,
            refresh_token: event.data.refresh_token || "",
          }),
        });
        if (!importResp.ok) {
          reject(new Error("Importazione Google Fit fallita"));
          return;
        }
        const result = await importResp.json();
        toast.success(`Importati ${result.count} percorsi da Google Fit`);
        resolve();
      }
    };
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== "bikemaster_oauth_result" || !event.newValue) return;
      try {
        handleMessage({ data: JSON.parse(event.newValue) } as MessageEvent);
      } catch (e) {
        /* ignore */
      }
    };
    window.addEventListener("message", handleMessage);
    window.addEventListener("storage", handleStorage);
  });
}

async function connectGoogleHealth() {
  const redirectUri = `${import.meta.env.DEV ? "http://localhost:8000" : window.location.origin}/api/v1/import/google-health/callback`;
  const state = btoa(JSON.stringify({ redirect_uri: redirectUri }));
  const authResp = await fetch(
    `/api/v1/import/google-health/auth?redirect_uri=${encodeURIComponent(redirectUri)}&state=${encodeURIComponent(state)}`,
  );
  if (!authResp.ok) {
    throw new Error("Impossibile avviare l'autenticazione Google Health");
  }
  const { auth_url } = await authResp.json();
  const popup = window.open(
    auth_url,
    "google-health-auth",
    "width=500,height=600",
  );
  if (!popup) throw new Error("Popup bloccato - abilita i popup");

  await new Promise<void>((resolve, reject) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", handleMessage);
      window.removeEventListener("storage", handleStorage);
      clearTimeout(timer);
    };
    const timer = setTimeout(
      () => {
        finish();
        reject(new Error("Timeout: autenticazione Google Health annullata"));
      },
      5 * 60 * 1000,
    );
    const handleMessage = async (event: MessageEvent) => {
      if (event.data?.type === "google-health-error") {
        finish();
        reject(
          new Error(
            event.data.error_description ||
              event.data.error ||
              "Errore Google Health",
          ),
        );
        return;
      }
      if (event.data?.type === "google-health-success") {
        finish();
        const token = authStore.token;
        const importResp = await fetch("/api/v1/import/google-health", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            access_token: event.data.token,
            refresh_token: event.data.refresh_token || "",
          }),
        });
        if (!importResp.ok) {
          reject(new Error("Importazione Google Health fallita"));
          return;
        }
        const result = await importResp.json();
        toast.success(`Importati ${result.count} percorsi da Google Health`);
        resolve();
      }
    };
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== "bikemaster_oauth_result" || !event.newValue) return;
      try {
        handleMessage({ data: JSON.parse(event.newValue) } as MessageEvent);
      } catch (e) {
        /* ignore */
      }
    };
    window.addEventListener("message", handleMessage);
    window.addEventListener("storage", handleStorage);
  });
}

async function connectWahoo() {
  const state = btoa(JSON.stringify({ redirect_uri: window.location.origin }));
  const authResp = await fetch(
    `/api/v1/import/wahoo/auth?state=${encodeURIComponent(state)}`,
  );
  if (!authResp.ok) {
    throw new Error("Impossibile avviare l'autenticazione Wahoo");
  }
  const result = await authResp.json();
  const codeVerifier = result.code_verifier;
  const popup = window.open(
    result.auth_url,
    "wahoo-auth",
    "width=500,height=600",
  );
  if (!popup) throw new Error("Popup bloccato - abilita i popup");

  await new Promise<void>((resolve, reject) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", handleMessage);
      window.removeEventListener("storage", handleStorage);
      clearTimeout(timer);
    };
    const timer = setTimeout(
      () => {
        finish();
        reject(new Error("Timeout: autenticazione Wahoo annullata"));
      },
      5 * 60 * 1000,
    );
    const handleMessage = async (event: MessageEvent) => {
      if (event.data?.type === "wahoo-error") {
        finish();
        reject(
          new Error(
            event.data.error_description || event.data.error || "Errore Wahoo",
          ),
        );
        return;
      }
      if (event.data?.type === "wahoo-success") {
        finish();
        const token = authStore.token;
        const callbackResp = await fetch("/api/v1/import/wahoo/callback", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            code: event.data.code,
            code_verifier: codeVerifier,
          }),
        });
        if (!callbackResp.ok) {
          reject(new Error("Connessione Wahoo fallita"));
          return;
        }
        toast.success("Wahoo connesso");
        resolve();
      }
    };
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== "bikemaster_oauth_result" || !event.newValue) return;
      try {
        handleMessage({ data: JSON.parse(event.newValue) } as MessageEvent);
      } catch (e) {
        /* ignore */
      }
    };
    window.addEventListener("message", handleMessage);
    window.addEventListener("storage", handleStorage);
  });
}

async function disconnectService(service: string) {
  disconnecting.value = service;
  clearServiceError();
  try {
    await connectionsStore.disconnect(service);
    toast.success(t("connections.disconnected"));
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setServiceError(msg, service);
    toast.error(msg);
  } finally {
    disconnecting.value = "";
  }
}

function hasKey(service: string): boolean {
  return !!apiKeysStore.keys[service as keyof typeof apiKeysStore.keys];
}

async function saveApiKey(service: string) {
  const value = (apikeyDrafts[service] || "").trim();
  savingKey.value = service;
  clearServiceError();
  try {
    if (!value) {
      apiKeysStore.clearKey(service as keyof typeof apiKeysStore.keys);
    } else {
      apiKeysStore.setKey(service as keyof typeof apiKeysStore.keys, value);
    }
    apiKeysStore.save();
    delete apikeyDrafts[service];
    toast.success(t("connections.keySaved"));
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setServiceError(msg, service);
    toast.error(msg);
  } finally {
    savingKey.value = "";
  }
}

function clearApiKey(service: string) {
  apiKeysStore.clearKey(service as keyof typeof apiKeysStore.keys);
  apiKeysStore.save();
  delete apikeyDrafts[service];
  toast.success(t("connections.keyCleared"));
}

async function importBulkKeys() {
  importingBulk.value = true;
  bulkStatus.value = "";
  bulkStatusClass.value = "";
  clearServiceError();
  try {
    const parsed = parseBulkKeys(bulkInput.value);
    const found = Object.values(parsed).filter((v) => !!v).length;
    if (found === 0) {
      bulkStatus.value = t("connections.bulkNoKeys");
      bulkStatusClass.value = "err";
      return;
    }
    for (const [key, value] of Object.entries(parsed)) {
      if (value) {
        apiKeysStore.setKey(key as keyof typeof apiKeysStore.keys, value);
      }
    }
    apiKeysStore.save();
    bulkStatus.value = `${found} ${t("connections.bulkImported")}`;
    bulkStatusClass.value = "ok";
    bulkInput.value = "";
  } catch (e) {
    bulkStatus.value = e instanceof Error ? e.message : String(e);
    bulkStatusClass.value = "err";
  } finally {
    importingBulk.value = false;
  }
}

async function scanBleDevices() {
  clearServiceError();
  try {
    const result = await bleStore.scanForDevices();
    scannedBleDevice.value = result.length ? result[0] : null;
    if (!result.length) {
      toast.info(
        t("connections.noBleDevicesFound") || "Nessun dispositivo BLE trovato",
      );
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setServiceError(msg);
    toast.error(msg);
  }
}

async function registerBleDevice() {
  clearServiceError();
  try {
    if (!scannedBleDevice.value) return;
    await bleStore.register({
      device_id: scannedBleDevice.value.deviceId,
      name: scannedBleDevice.value.name,
      device_type: scannedBleDevice.value.type,
    });
    const registeredDevice = bleStore.devices.find(
      (d) => d.device_id === scannedBleDevice.value?.deviceId,
    );
    scannedBleDevice.value = null;
    if (registeredDevice) {
      toast.success(t("connections.pairedSuccess"));
      try {
        await bleStore.sync(registeredDevice.id);
        toast.success(t("connections.downloadSuccess"));
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        toast.error(msg || t("connections.downloadError"));
      }
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setServiceError(msg);
    toast.error(msg);
  }
}

async function removeBleDevice(device: { id: number }) {
  clearServiceError();
  try {
    await bleStore.unregister(device.id);
    toast.success(t("connections.deviceRemoved"));
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setServiceError(msg);
    toast.error(msg);
  }
}

async function connectHealthConnect() {
  clearServiceError();
  try {
    await healthConnect.checkAvailability();
    if (!healthConnect.status.available) {
      throw new Error("Health Connect non disponibile su questo dispositivo");
    }

    await healthConnect.connect();
    toast.success("Health Connect connesso");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setServiceError(msg);
    toast.error(msg);
  }
}

async function syncHealthConnect() {
  clearServiceError();
  try {
    const result = await healthConnect.sync();
    if (result.connected) {
      toast.success(
        result.synced > 0
          ? `Sincronizzati ${result.synced} record Health Connect`
          : "Health Connect sincronizzato",
      );
    } else {
      toast.info("Health Connect non connesso");
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Sincronizzazione fallita";
    setServiceError(msg);
    toast.error(msg);
  }
}

onMounted(async () => {
  await apiKeysStore.load();
  await connectionsStore.load();
  await bleStore.load();
  await healthConnect.checkAvailability();
  bleAvailable.value =
    typeof navigator !== "undefined" &&
    !!(navigator as unknown as Record<string, unknown>).bluetooth;
  keysLoaded.value = true;
});
</script>

<style scoped>
.connections-page {
  max-width: 980px;
  margin: 0 auto;
  padding: 2rem;
}
.subtitle {
  color: #888;
  margin-bottom: 1.5rem;
}
.connections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.connection-card {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  transition: all 0.2s;
}
.connection-card.connected {
  border-color: #42b983;
  box-shadow: 0 0 0 1px #42b983;
}
.connection-card.oauth {
  border-left: 3px solid #4285f4;
}
.connection-card.apikey {
  border-left: 3px solid #e7c66e;
}
.connection-header {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.connection-icon {
  font-size: 1.6rem;
}
.connection-title {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.connection-name {
  font-weight: 600;
  color: #eee;
}
.connection-desc {
  color: #999;
  font-size: 0.85rem;
  margin: 0;
}
.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}
.status-dot.online {
  background: #42b983;
  box-shadow: 0 0 6px rgba(66, 183, 77, 0.5);
}
.status-dot.offline {
  background: #e57373;
}
.status-text {
  color: #ccc;
}
.last-connected {
  color: #888;
  font-size: 0.78rem;
  margin-left: auto;
}
.connection-actions {
  display: flex;
  gap: 0.5rem;
}
.apikey-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.apikey-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.connection-error {
  background: rgba(229, 115, 115, 0.1);
  border: 1px solid #e57373;
  border-radius: 6px;
  padding: 0.6rem;
  color: #e57373;
  font-size: 0.85rem;
}

.bulk-section {
  margin-top: 1rem;
}
.bulk-input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.7rem 0.8rem;
  background: #0f0f0f;
  border: 1px solid #333;
  border-radius: 6px;
  color: #eee;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.82rem;
  resize: vertical;
}
.key-actions {
  margin-top: 0.4rem;
  align-items: center;
}
.status {
  font-size: 0.85rem;
}
.status.ok {
  color: #42b983;
}
.status.err {
  color: #e57373;
}

.card {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.4rem;
  margin-bottom: 1.2rem;
}
.card h2 {
  font-size: 1.1rem;
  margin-bottom: 0.6rem;
}
.hint {
  color: #999;
  font-size: 0.85rem;
  margin-bottom: 0.8rem;
}
.row {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-wrap: wrap;
}
.text-input {
  flex: 1 1 280px;
  padding: 0.6rem 0.8rem;
  background: #0f0f0f;
  border: 1px solid #333;
  border-radius: 6px;
  color: #eee;
}
.btn {
  padding: 0.6rem 1.1rem;
  background: #42b983;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-ghost {
  background: transparent;
  border: 1px solid #444;
  color: #ccc;
}
.btn-danger {
  background: #e57373;
  color: #fff;
}
.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.badge-oauth {
  background: #1b2a3a;
  color: #6eb8e7;
}
.badge-apikey {
  background: #3a2f1b;
  color: #e7c66e;
}

.key-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.6rem;
}
.key-label {
  font-size: 0.85rem;
  color: #bbb;
}

@media (max-width: 640px) {
  .connections-grid {
    grid-template-columns: 1fr;
  }
  .connections-page {
    padding: 1rem;
  }
}
.devices-section {
  margin-top: 1.5rem;
}
.devices-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}
.device-card {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.ble-card {
  border-left: 3px solid #42b983;
}
.health-card {
  border-left: 3px solid #f48fb1;
}
.device-header {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.device-icon {
  font-size: 1.6rem;
}
.device-name {
  font-weight: 600;
  color: #eee;
}
.device-meta {
  font-size: 0.82rem;
  color: #aaa;
}
.device-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.device-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.device-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  background: #111;
  border: 1px solid #2a2a2a;
  border-radius: 6px;
  padding: 0.6rem 0.8rem;
}
.device-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.device-type {
  font-size: 0.78rem;
  color: #aaa;
}
.device-status {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.empty-hint {
  font-size: 0.85rem;
  color: #777;
  padding: 0.4rem 0;
}
.permission-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.permission-label {
  font-size: 0.8rem;
  color: #bbb;
}
.permission-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.permission-tag {
  background: #2a1f35;
  color: #ce93d8;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 0.78rem;
}
.btn-sm {
  padding: 0.35rem 0.75rem;
  font-size: 0.82rem;
  border-radius: 4px;
}
</style>
