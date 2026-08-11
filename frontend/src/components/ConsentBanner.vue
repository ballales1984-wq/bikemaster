<!--
  GDPR / AI Act consent banner.
  Shown on first visit until the user accepts/declines each consent type.
-->
<template>
  <Transition name="fade">
    <div
      v-if="visible"
      class="consent-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Consensi privacy"
    >
      <div class="consent-card">
        <h2>Consensi e trasparenza</h2>
        <p class="consent-intro">
          Per rispettare il nuovo quadro normativo europeo (GDPR e AI Act), ti
          chiediamo di confermare le seguenti scelte prima di continuare.
        </p>

        <div class="consent-item">
          <label class="toggle">
            <input
              v-model="consents.essential"
              type="checkbox"
              disabled
              checked
            />
            <span>
              <strong>Cookie e dati essenziali</strong>
              <small
                >Necessari per il funzionamento dell'app (autenticazione,
                preferenze). Non possono essere disattivati.</small
              >
            </span>
          </label>
        </div>

        <div class="consent-item">
          <label class="toggle">
            <input v-model="consents.ai_coach" type="checkbox" />
            <span>
              <strong>AI Coach</strong>
              <small
                >Consento all'uso di un modello di intelligenza artificiale per
                generare consigli di allenamento personalizzati (AI Act -
                Trasparenza).</small
              >
            </span>
          </label>
        </div>

        <div class="consent-item">
          <label class="toggle">
            <input v-model="consents.health_data" type="checkbox" />
            <span>
              <strong>Dati sanitari</strong>
              <small
                >Consento il trattamento di dati sensibili come frequenza
                cardiaca, peso e indicatori metabolici (GDPR Art. 9).</small
              >
            </span>
          </label>
        </div>

        <div class="consent-item">
          <label class="toggle">
            <input v-model="consents.external_sync" type="checkbox" />
            <span>
              <strong>Sincronizzazione esterna</strong>
              <small
                >Consento la sincronizzazione con servizi terzi (Strava, Garmin,
                Google Fit) se attivata successivamente.</small
              >
            </span>
          </label>
        </div>

        <div class="consent-actions">
          <button class="btn btn-primary" :disabled="!canSave" @click="save">
            Conferma e continua
          </button>
          <button class="btn btn-ghost" @click="declineAll">
            Rifiuta non essenziali
          </button>
        </div>

        <p class="consent-note">
          Puoi modificare queste preferenze in qualsiasi momento da
          Impostazioni. Per informazioni dettagliate consulta la
          <router-link to="/privacy">Privacy Policy</router-link> e i
          <router-link to="/terms">Termini di servizio</router-link>.
        </p>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { resolveApiBase } from "../utils/backend-config";

const emit = defineEmits(["saved"]);

const auth = useAuthStore();
const visible = ref(false);

const consents = reactive({
  essential: true,
  ai_coach: false,
  health_data: false,
  external_sync: false,
});

const canSave = computed(() => consents.essential);

async function save() {
  try {
    const base = resolveApiBase();
    const url = base ? `${base}/api/v1/legal/consent` : "/api/v1/legal/consent";
    const entries = [
      { consent_type: "essential", granted: true },
      { consent_type: "ai_coach", granted: consents.ai_coach },
      { consent_type: "health_data", granted: consents.health_data },
      { consent_type: "external_sync", granted: consents.external_sync },
    ];
    for (const entry of entries) {
      await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${auth.token}`,
        },
        body: JSON.stringify(entry),
      }).catch(() => {});
    }
    localStorage.setItem(
      "bikemaster_consent_v1",
      JSON.stringify({ ...consents, savedAt: Date.now() }),
    );
    visible.value = false;
    emit("saved", { ...consents });
  } catch {
    visible.value = false;
    emit("saved", { ...consents });
  }
}

function declineAll() {
  consents.ai_coach = false;
  consents.health_data = false;
  consents.external_sync = false;
  save();
}

onMounted(() => {
  try {
    const raw = localStorage.getItem("bikemaster_consent_v1");
    if (raw) {
      const saved = JSON.parse(raw);
      if (saved && typeof saved.savedAt === "number") {
        return;
      }
    }
  } catch {
    /* ignore */
  }
  visible.value = true;
});
</script>

<style scoped>
.consent-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  padding: 16px;
}
.consent-card {
  max-width: 560px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  background: #14171f;
  border: 1px solid #2a2f3a;
  border-radius: 12px;
  padding: 20px;
  color: #e6e8ee;
}
.consent-card h2 {
  margin: 0 0 10px;
  font-size: 1.2rem;
}
.consent-intro {
  color: #b0b5c1;
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 14px;
}
.consent-item {
  margin-bottom: 12px;
}
.toggle {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 0.9rem;
  color: #ccc;
}
.toggle input {
  margin-top: 3px;
}
.toggle span {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.toggle small {
  color: #9aa0ac;
  font-size: 0.8rem;
}
.consent-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 14px;
}
.consent-note {
  margin-top: 12px;
  font-size: 0.8rem;
  color: #9aa0ac;
  line-height: 1.45;
}
.btn {
  border: none;
  cursor: pointer;
  font-weight: 600;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.9rem;
}
.btn-primary {
  background: linear-gradient(135deg, #00ffcc, #0088ff);
  color: #0a0b10;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-ghost {
  background: transparent;
  border: 1px solid #444;
  color: #ccc;
}
a {
  color: #42b983;
  text-decoration: none;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
