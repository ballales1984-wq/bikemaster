<!--
  Vista delle impostazioni backend e preferenze utente.
  Configurazione URL backend, fallback Render, sincronizzazione e verifica stato connessione.
  Le chiavi API sono gestite nella pagina Connessioni.
  Componenti: SyncSettingsPanel.
  Store: settingsStore.
-->
<template>
  <div class="settings-page">
    <h1>Impostazioni backend</h1>
    <p class="subtitle">
      Configura dove l'app risiede i dati. Di default usa lo stesso
      origine; in produzione il backend &egrave; su Render.
    </p>

    <section class="card">
      <h2>Failover Render</h2>
      <label class="toggle">
        <input
          type="checkbox"
          :checked="settings.fallbackEnabled"
          @change="toggleFallback"
        />
        <span>
          Usa Render (<code>{{ settings.fallbackBase }}</code
          >) come backup se il backend primario non risponde.
        </span>
      </label>
    </section>

    <section class="card link-card">
      <h2>Chiavi API e connessioni</h2>
      <p class="hint">
        La gestione delle chiavi API e delle connessioni OAuth &egrave;
        disponibile nella pagina
        <router-link to="/settings/connections" class="inline-link"
          >Connessioni</router-link
        >.
      </p>
    </section>

    <SyncSettingsPanel />

    <section class="card">
      <h2>Stato connessione</h2>
      <div class="row">
        <span class="badge" :class="modeClass">{{ modeLabel }}</span>
        <button class="btn btn-ghost" @click="ping">Verifica</button>
      </div>
      <p class="status" :class="statusClass">{{ statusText }}</p>
      <p class="hint">
        Base risolto:
        <code>{{ settings.resolvedBase || "(stesso origine)" }}</code>
      </p>
    </section>

    <section class="card">
      <h2>Consensi e normative</h2>
      <p class="hint">
        Gestisci i consensi per il trattamento dei dati e le normative europee
        (GDPR / AI Act).
      </p>
      <div class="consent-list">
        <div
          v-for="item in consents"
          :key="item.consent_type"
          class="consent-row"
        >
          <span class="consent-label">{{ item.label }}</span>
          <label class="toggle">
            <input
              type="checkbox"
              :checked="item.granted"
              @change="
                toggleConsent(
                  item.consent_type,
                  ($event.target as HTMLInputElement).checked,
                )
              "
            />
            <span>{{ item.granted ? "Attivo" : "Disattivato" }}</span>
          </label>
        </div>
      </div>
      <div class="row" style="margin-top: 12px">
        <router-link to="/privacy" class="inline-link"
          >Privacy Policy</router-link
        >
        <router-link to="/terms" class="inline-link"
          >Termini di servizio</router-link
        >
        <router-link to="/cookies" class="inline-link"
          >Cookie Policy</router-link
        >
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useSettingsStore } from "../stores/settings";
import { apiGet } from "../utils/api";
import SyncSettingsPanel from "../components/SyncSettingsPanel.vue";
import { useAuthStore } from "../stores/auth";
import { resolveApiBase } from "../utils/backend-config";
const auth = useAuthStore();

const settings = useSettingsStore();

const statusText = ref("");
const statusClass = ref("");
const consents = ref<
  Array<{ consent_type: string; label: string; granted: boolean }>
>([
  {
    consent_type: "essential",
    label: "Cookie e dati essenziali",
    granted: true,
  },
  { consent_type: "ai_coach", label: "AI Coach", granted: false },
  { consent_type: "health_data", label: "Dati sanitari", granted: false },
  {
    consent_type: "external_sync",
    label: "Sincronizzazione esterna",
    granted: false,
  },
]);

async function loadConsents() {
  if (!auth.isLoggedIn) return;
  try {
    const data = await apiGet<{
      consents: Array<{ consent_type: string; granted: number }>;
    }>("/api/v1/legal/consent", {}, { suppressAuthClear: true });
    const map = new Map(
      data.consents.map((c) => [c.consent_type, c.granted === 1]),
    );
    for (const item of consents.value) {
      if (map.has(item.consent_type)) {
        item.granted = map.get(item.consent_type) ?? item.granted;
      }
    }
  } catch {
    /* ignore */
  }
}

async function toggleConsent(consent_type: string, granted: boolean) {
  if (!auth.isLoggedIn) return;
  try {
    const base = resolveApiBase();
    const url = base ? `${base}/api/v1/legal/consent` : "/api/v1/legal/consent";
    await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify({ consent_type, granted, source: "settings" }),
    }).catch(() => {});
    const item = consents.value.find((c) => c.consent_type === consent_type);
    if (item) item.granted = granted;
  } catch {
    /* ignore */
  }
}

const modeLabel = computed(() => {
  switch (settings.backendMode) {
    case "render":
      return "Render (produzione)";
    case "mobile":
      return "Mobile (rete locale)";
    default:
      return "Stesso origine (locale)";
  }
});

const modeClass = computed(() => ({
  "badge-render": settings.backendMode === "render",
  "badge-local": settings.backendMode === "local",
  "badge-mobile": settings.backendMode === "mobile",
}));

function toggleFallback(e: Event) {
  const checked = (e.target as HTMLInputElement).checked;
  settings.setUseFallback(checked);
}

async function ping() {
  statusText.value = "Verifica in corso…";
  statusClass.value = "";
  try {
    await apiGet("/api/v1/health", {}, { timeoutMs: 8000 });
    statusText.value = "Backend raggiungibile ";
    statusClass.value = "ok";
  } catch (err) {
    statusText.value = `Backend non raggiungibile: ${(err as Error).message}`;
    statusClass.value = "err";
  }
}

onMounted(() => {
  loadConsents();
});
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
.badge-render {
  background: #3a2f1b;
  color: #e7c66e;
}
.badge-local {
  background: #1b2a3a;
  color: #6eb8e7;
}
.badge-mobile {
  background: #2a1b3a;
  color: #c084fc;
}
code {
  background: #0f0f0f;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  color: #ddd;
}
.link-card {
}
.link-card .hint {
  margin-bottom: 0;
}
.inline-link {
  color: #42b983;
  text-decoration: none;
  font-weight: 600;
}
.inline-link:hover {
  text-decoration: underline;
}
.consent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.consent-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.consent-label {
  font-size: 0.9rem;
  color: #ccc;
}
</style>
