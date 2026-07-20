<!--
  Vista delle impostazioni backend e preferenze utente.
  Configurazione URL backend, fallback Render, gestione chiavi API personali,
  importazione bulk chiavi, pannello sync e verifica stato connessione.
  Componenti: SyncSettingsPanel.
  Store: settingsStore, apiKeysStore.
-->
<template>
  <div class="settings-page">
    <h1>⚙️ Impostazioni backend</h1>
    <p class="subtitle">
      Configura dove l'app risiede i dati. Di default chiama lo stesso origine;
      su dispositivi/Web punta al tuo PC. Render resta come failover.
    </p>

    <section class="card">
      <h2>URL del backend</h2>
      <p class="hint">
        Inserisci l'URL del backend in esecuzione sul tuo PC (es.
        <code>https://bikemaster.home:8000</code> o un tunnel). Lascia vuoto per
        usare lo stesso origine (utile in sviluppo).
      </p>
      <div class="row">
        <input
          v-model="draftBase"
          class="text-input"
          type="text"
          placeholder="https://tuo-pc.example.com"
          @keyup.enter="save"
        />
        <button class="btn" @click="save">Salva</button>
        <button class="btn btn-ghost" @click="reset">Predefinito</button>
      </div>
      <p class="status" :class="statusClass">{{ statusText }}</p>
    </section>

    <section class="card">
      <h2>Failover Render</h2>
      <label class="toggle">
        <input
          type="checkbox"
          :checked="settings.fallbackEnabled"
          @change="toggleFallback"
        />
        <span>
          Usa Render (<code>{{ settings.fallbackBase }}</code>) come backup se il
          backend primario non risponde.
        </span>
      </label>
    </section>

    <section class="card">
      <h2>Chiavi API personali</h2>
      <p class="hint">
        Inserisci le <strong>tue</strong> chiavi per far funzionare l'app
        localmente. Vengono salvate solo su questo dispositivo (SQLite locale) e
        inviate al backend del PC ad ogni richiesta, che le usa al posto delle sue.
        Non vengono mai conservate sul server.
      </p>
      <div class="keys-grid">
        <label v-for="field in keyFields" :key="field.name" class="key-field">
          <span class="key-label">{{ field.label }}</span>
          <div class="key-input-row">
            <input
              v-model="keys[field.name]"
              class="text-input"
              :type="showKeys ? 'text' : 'password'"
              :placeholder="field.placeholder"
              autocomplete="off"
            />
            <button
              v-if="keys[field.name]"
              class="btn btn-ghost btn-key-clear"
              type="button"
              :title="'Rimuovi ' + field.label"
              @click="clearKey(field.name)"
            >
              ✕
            </button>
          </div>
        </label>
      </div>
      <div class="row key-actions">
        <button class="btn" @click="saveKeys">Salva chiavi</button>
        <button class="btn btn-ghost" @click="showKeys = !showKeys">
          {{ showKeys ? "Nascondi" : "Mostra" }}
        </button>
        <span class="status" :class="keysStatusClass">{{ keysStatus }}</span>
      </div>
    </section>

    <section class="card">
      <h2>Importa chiavi (copia-incolla)</h2>
      <p class="hint">
        Incolla tutte le variabili in una volta (JSON o righe
        <code>KEY=VALUE</code>, es. <code>GROQ_API_KEY=gsk_...</code>). Le chiavi
        verranno distribuite nei campi sopra e salvate sul dispositivo.
      </p>
      <textarea
        v-model="bulkInput"
        class="bulk-input"
        rows="5"
        placeholder='{"groq":"gsk_...","google_maps":"AIza...","serpapi":"...","weather":"...","garmin_api_key":"...","strava_client_id":"...","strava_client_secret":"...","wahoo_client_id":"...","wahoo_client_secret":"...","google_fit_client_id":"...","google_fit_client_secret":"...","google_health_client_id":"...","google_health_client_secret":"..."}'
      ></textarea>
      <div class="row key-actions">
        <button class="btn" @click="importBulk">Importa e salva</button>
        <span class="status" :class="bulkStatusClass">{{ bulkStatus }}</span>
      </div>
    </section>

    <SyncSettingsPanel />

    <section class="card">
      <h2>Stato connessione</h2>
      <div class="row">
        <span class="badge" :class="modeClass">{{ modeLabel }}</span>
        <button class="btn btn-ghost" @click="ping">Verifica</button>
      </div>
      <p class="hint">Base risolto: <code>{{ settings.resolvedBase || "(stesso origine)" }}</code></p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useSettingsStore } from "../stores/settings";
import { useApiKeysStore } from "../stores/apiKeys";
import { apiGet } from "../utils/api";
import { parseBulkKeys } from "../utils/userKeys";
import type { UserApiKeys } from "../utils/userKeys";
import SyncSettingsPanel from "../components/SyncSettingsPanel.vue";

const settings = useSettingsStore();
const apiKeys = useApiKeysStore();

const draftBase = ref(settings.apiBase);
const statusText = ref("");
const statusClass = ref("");
const showKeys = ref(false);
const keysStatus = ref("");
const keysStatusClass = ref("");
const bulkInput = ref("");
const bulkStatus = ref("");
const bulkStatusClass = ref("");

const keyFields: { name: keyof UserApiKeys; label: string; placeholder: string }[] = [
  { name: "groq", label: "Groq (AI Coach)", placeholder: "gsk_..." },
  { name: "google_maps", label: "Google Maps", placeholder: "AIza..." },
  { name: "serpapi", label: "SerpAPI", placeholder: "SerpAPI key" },
  { name: "weather", label: "Weather / OpenWeather", placeholder: "OpenWeather key" },
  { name: "garmin_api_key", label: "Garmin API Key", placeholder: "Garmin Connect key" },
  { name: "strava_client_id", label: "Strava Client ID", placeholder: "Strava OAuth client id" },
  { name: "strava_client_secret", label: "Strava Client Secret", placeholder: "Strava OAuth client secret" },
  { name: "wahoo_client_id", label: "Wahoo Client ID", placeholder: "Wahoo OAuth client id" },
  { name: "wahoo_client_secret", label: "Wahoo Client Secret", placeholder: "Wahoo OAuth client secret" },
  { name: "google_fit_client_id", label: "Google Fit Client ID", placeholder: "Google Fit OAuth client id" },
  { name: "google_fit_client_secret", label: "Google Fit Client Secret", placeholder: "Google Fit OAuth client secret" },
  { name: "google_health_client_id", label: "Google Health Client ID", placeholder: "Google Health OAuth client id" },
  { name: "google_health_client_secret", label: "Google Health Client Secret", placeholder: "Google Health OAuth client secret" },
];

const keys = reactive<UserApiKeys>({ ...apiKeys.keys });

onMounted(async () => {
  await apiKeys.load();
  Object.assign(keys, apiKeys.keys);
});

const modeLabel = computed(() => {
  switch (settings.backendMode) {
    case "pc":
      return "Backend PC (personalizzato)";
    case "render":
      return "Render (fallback)";
    default:
      return "Stesso origine (locale)";
  }
});

const modeClass = computed(() => ({
  "badge-pc": settings.backendMode === "pc",
  "badge-render": settings.backendMode === "render",
  "badge-local": settings.backendMode === "local",
}));

function save() {
  settings.setApiBase(draftBase.value);
  statusText.value = "URL backend salvato.";
  statusClass.value = "ok";
}

function reset() {
  settings.resetApiBase();
  draftBase.value = "";
  statusText.value = "Ripristinato il default (stesso origine).";
  statusClass.value = "ok";
}

function toggleFallback(e: Event) {
  const checked = (e.target as HTMLInputElement).checked;
  settings.setUseFallback(checked);
}

function saveKeys() {
  for (const field of keyFields) {
    const val = (keys[field.name] || "").trim();
    if (val) apiKeys.setKey(field.name, val);
    else apiKeys.clearKey(field.name);
  }
  apiKeys.save();
  keysStatus.value = "Chiavi salvate su questo dispositivo.";
  keysStatusClass.value = "ok";
}

function clearKey(name: keyof UserApiKeys) {
  keys[name] = "";
  apiKeys.clearKey(name);
  apiKeys.save();
  keysStatus.value = `${name} rimossa da questo dispositivo.`;
  keysStatusClass.value = "ok";
}

function importBulk() {
  const parsed = parseBulkKeys(bulkInput.value);
  const found = Object.values(parsed).filter((v) => !!v).length;
  if (found === 0) {
    bulkStatus.value = "Nessuna chiave riconosciuta nel testo incollato.";
    bulkStatusClass.value = "err";
    return;
  }
  for (const field of keyFields) {
    const val = (parsed[field.name] || "").trim();
    if (val) apiKeys.setKey(field.name, val);
    else apiKeys.clearKey(field.name);
  }
  apiKeys.save();
  Object.assign(keys, apiKeys.keys);
  bulkStatus.value = `${found} chiave/i importata/e e salvata/e.`;
  bulkStatusClass.value = "ok";
}

async function ping() {
  statusText.value = "Verifica in corso…";
  statusClass.value = "";
  try {
    await apiGet("/api/v1/health", {}, { timeoutMs: 8000 });
    statusText.value = "Backend raggiungibile ✓";
    statusClass.value = "ok";
  } catch (err) {
    statusText.value = `Backend non raggiungibile: ${(err as Error).message}`;
    statusClass.value = "err";
  }
}
</script>

<style scoped>
.settings-page {
  max-width: 820px;
  margin: 0 auto;
  padding: 2rem;
}
h1 {
  font-size: 1.8rem;
}
.subtitle {
  color: #888;
  margin-bottom: 1.5rem;
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
.btn-ghost {
  background: transparent;
  border: 1px solid #444;
  color: #ccc;
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
.toggle {
  display: flex;
  gap: 0.6rem;
  align-items: flex-start;
  font-size: 0.9rem;
  color: #ccc;
}
.badge {
  padding: 0.3rem 0.7rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}
.badge-pc {
  background: #1b3a2a;
  color: #6ee7a8;
}
.badge-render {
  background: #3a2f1b;
  color: #e7c66e;
}
.badge-local {
  background: #1b2a3a;
  color: #6eb8e7;
}
code {
  background: #0f0f0f;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  color: #ddd;
}
.keys-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0.9rem;
  margin-bottom: 0.8rem;
}
.key-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.key-input-row {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}
.key-input-row .text-input {
  flex: 1 1 auto;
}
.btn-key-clear {
  flex: 0 0 auto;
  padding: 0.5rem 0.7rem;
  line-height: 1;
}
.key-label {
  font-size: 0.85rem;
  color: #bbb;
}
.key-actions {
  margin-top: 0.4rem;
  align-items: center;
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
</style>
