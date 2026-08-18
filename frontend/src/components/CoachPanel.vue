<!-- Pannello coach AI: chat conversazionale con l'assistente di allenamento (endpoint /api/v1/coach).
     Props: nessuna. Eventi: nessuno. Mostra pill di training scores, finestra chat con messaggi/indicatore "sta scrivendo",
     domande rapide e input con supporto vocale (SpeechRecognition) e lettura TTS. Pulsanti report completo e pulizia chat. -->
<template>
  <div class="coach-panel">
    <div class="coach-header">
      <div class="coach-title">
        <span class="coach-avatar"></span>
        <div>
          <h2>{{ t("coach.title") }}</h2>
          <span class="coach-status">{{
            connected ? " " + t("coach.online") : " " + t("coach.offline")
          }}</span>
          <span
            class="ai-badge"
            title="AI-generated advice (AI Act transparency)"
          >
            AI
          </span>
        </div>
      </div>
      <div class="header-actions">
        <button
          class="btn btn-sm btn-secondary"
          :disabled="loadingReport"
          :title="t('coach.report')"
          :aria-label="t('coach.report')"
          @click="loadFullReport"
        >
          {{ loadingReport ? "⏳" : "" }} {{ t("coach.report") }}
        </button>
        <button
          class="btn btn-sm btn-secondary"
          :title="t('coach.clear')"
          :aria-label="t('coach.clear')"
          @click="clearChat"
        >
          🗑️
        </button>
      </div>
    </div>

    <!-- Score cards -->
    <div v-if="scores.length" class="score-strip">
      <div v-for="s in scores" :key="s.label" class="score-pill">
        <span class="pill-val" :style="{ color: s.color }">{{ s.value }}</span>
        <span class="pill-lbl">{{ s.label }}</span>
      </div>
    </div>

    <!-- Chat window -->
    <div ref="chatWindow" class="chat-window">
      <!-- Welcome message -->
      <div v-if="messages.length === 0" class="message bot-msg">
        <div class="msg-avatar"></div>
        <div class="msg-content">
          <div class="msg-bubble">
            {{ t("coach.welcome") }}
          </div>
          <div class="quick-actions">
            <button
              v-for="q in quickQuestions"
              :key="q"
              class="quick-btn"
              @click="sendQuick(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>
      </div>

      <!-- Messages -->
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message"
        :class="msg.role === 'user' ? 'user-msg' : 'bot-msg'"
      >
        <div class="msg-avatar">
          {{ msg.role === "user" ? "" : "" }}
        </div>
        <div class="msg-content">
          <!-- eslint-disable-next-line vue/no-v-html -- formatMsg() sanitizes with DOMPurify -->
          <div class="msg-bubble" v-html="formatMsg(msg.content)" />
          <div class="msg-time">
            {{ msg.time }}
          </div>
        </div>
      </div>

      <!-- Typing indicator -->
      <div v-if="thinking" class="message bot-msg">
        <div class="msg-avatar"></div>
        <div class="msg-content">
          <div class="msg-bubble typing-bubble">
            <span class="dot" /><span class="dot" /><span class="dot" />
          </div>
        </div>
      </div>
    </div>

    <!-- BM2 Physics Analysis -->
    <div v-if="bm2Result" class="bm2-results">
      <h4>{{ t("bm2.physicsAnalysis") }}</h4>
      <div v-if="'validation' in bm2Result" class="bm2-card">
        <header>
          <strong>Validazione potenza</strong>
          <span class="bm2-value">Ride #{{ bm2Result.ride_id }}</span>
        </header>
        <dl class="bm2-valgrid">
          <dt>Punti</dt>
          <dd>{{ bm2Result.validation.n_points }}</dd>
          <dt>MAE</dt>
          <dd>{{ bm2Result.validation.mae_w.toFixed(1) }} W</dd>
          <dt>RMSE</dt>
          <dd>{{ bm2Result.validation.rmse_w.toFixed(1) }} W</dd>
          <dt>Bias</dt>
          <dd>{{ bm2Result.validation.bias_w.toFixed(1) }} W</dd>
          <dt>Potenza media misurata</dt>
          <dd>{{ bm2Result.validation.mean_measured_w.toFixed(1) }} W</dd>
          <dt>Potenza media stimata</dt>
          <dd>{{ bm2Result.validation.mean_estimated_w.toFixed(1) }} W</dd>
          <dt>R²</dt>
          <dd>{{ bm2Result.validation.r2.toFixed(3) }}</dd>
        </dl>
      </div>
      <div v-if="'results' in bm2Result" class="bm2-card">
        <header>
          <strong>{{ bm2Result.question }}</strong>
          <span class="bm2-value">{{
            bm2Result.confidence
              ? Math.round(bm2Result.confidence * 100) + "%"
              : ""
          }}</span>
        </header>
        <dl>
          <dt>Modelli</dt>
          <dd>{{ bm2Result.models_used.join(", ") }}</dd>
        </dl>
        <div
          v-for="[name, r] in Object.entries(bm2Result.results)"
          :key="name"
          class="bm2-card"
          style="margin-top: 0.5rem"
        >
          <header>
            <strong>{{ name }}</strong>
            <span class="bm2-value">{{ r.value.toFixed(1) }} {{ r.unit }}</span>
          </header>
          <dl>
            <dt>Formula</dt>
            <dd>{{ r.formula }}</dd>
            <dt>Dati usati</dt>
            <dd>{{ r.data_used.join(", ") }}</dd>
            <dt>Precisione</dt>
            <dd>±{{ r.precision.toFixed(2) }} {{ r.unit }}</dd>
            <dt>Affidabilità</dt>
            <dd>{{ Math.round(r.confidence * 100) }}%</dd>
            <dt>Fonte</dt>
            <dd>{{ r.source }}</dd>
          </dl>
        </div>
        <aside
          v-if="bm2Result.insights.length"
          class="bm2-insights"
          style="margin-top: 1rem"
        >
          <h3>Concetti</h3>
          <ul>
            <li
              v-for="(ins, i) in bm2Result.insights"
              :key="i"
              :class="'bm2-' + ins.severity"
            >
              <strong>{{ ins.concept }}</strong> — {{ ins.detail }}
            </li>
          </ul>
        </aside>
        <aside
          v-if="bm2Result.simulation"
          class="bm2-sim"
          style="margin-top: 1rem"
        >
          <h3>Simulazione ("what if")</h3>
          <ul class="bm2-deltas">
            <li
              v-for="(delta, model) in bm2Result.simulation.deltas"
              :key="model"
            >
              {{ model }}:
              <span :class="delta >= 0 ? 'bm2-up' : 'bm2-down'"
                >{{ delta >= 0 ? "+" : "" }}{{ delta.toFixed(2) }}</span
              >
            </li>
          </ul>
        </aside>
      </div>
    </div>

    <!-- Input area -->
    <div class="chat-input-area">
      <textarea
        ref="inputRef"
        v-model="userInput"
        class="chat-input"
        :placeholder="t('coach.placeholder')"
        rows="1"
        :disabled="thinking"
        :aria-label="t('coach.ask')"
        @keydown.enter.prevent="sendMessage"
        @input="autoResize"
      />
      <button
        v-if="voiceSupported"
        class="voice-btn"
        :class="{ listening: isListening }"
        :disabled="thinking"
        :title="isListening ? 'Stop listening' : 'Voice input'"
        :aria-label="isListening ? 'Stop listening' : 'Voice input'"
        @click="toggleVoice"
      >
        <span v-if="!isListening">🎤</span>
        <span v-else>⏹</span>
      </button>
      <button
        v-if="ttsSupported"
        class="voice-btn"
        :disabled="thinking || !lastAssistantMessage"
        :title="autoRead ? 'Disable voice' : 'Enable voice'"
        :aria-label="autoRead ? 'Disable voice' : 'Enable voice'"
        @click="toggleAutoRead"
      >
        <span>{{ autoRead ? "🔊" : "🔇" }}</span>
      </button>
      <button
        class="send-btn"
        :disabled="!userInput.trim() || thinking"
        @click="sendMessage"
      >
        <span v-if="!thinking"></span>
        <span
          v-else
          class="spinner"
          style="width: 16px; height: 16px; border-width: 2px"
        />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "../composables/useI18n";
import { apiGet, apiPost, ApiError } from "../utils/api";
import DOMPurify from "dompurify";
import type { CoachData } from "../types/index";
import type { Bm2CoachResult } from "../types/bm2";

const { t } = useI18n();

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  time: string;
}

interface ScoreItem {
  label: string;
  value: string;
  color: string;
}

const messages = ref<ChatMessage[]>([]);
const userInput = ref("");
const thinking = ref(false);
const loadingReport = ref(false);
const connected = ref(true);
const chatWindow = ref<HTMLElement | null>(null);
const inputRef = ref<HTMLTextAreaElement | null>(null);
const coachData = ref<CoachData | null>(null);
const athleteId = ref<number | null>(null);
const bm2Result = ref<Bm2CoachResult | null>(null);

const quickQuestions = [
  " Prossimo allenamento consigliato",
  " Quanto recupero mi serve?",
  " Analizza le mie ultime uscite",
  " Come aumentare il FTP?",
  " Analisi BM2 della ride selezionata",
];

const scores = computed<ScoreItem[]>(() => {
  const s = coachData.value?.training_scores;
  if (!s) return [];
  const colors: Record<string, string> = {
    Performance: "var(--color-performance)",
    Endurance: "var(--color-endurance)",
    Efficiency: "var(--color-efficiency)",
    Recovery: "var(--color-recovery)",
  };
  return s.map((sc) => ({
    label: sc.label,
    value: Number(sc.value || 0).toFixed(1),
    color: colors[sc.label] || "var(--accent)",
  }));
});

function formatMsg(text: string): string {
  if (!text) return "";
  const html = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br>")
    .replace(/^- (.+)/gm, "<li>$1</li>");
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ["strong", "em", "br", "li", "ul"],
    ALLOWED_ATTR: [],
  });
}

function getTime(): string {
  return new Date().toLocaleTimeString("it-IT", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

let scrollRaf = 0;
async function scrollToBottom() {
  if (scrollRaf) cancelAnimationFrame(scrollRaf);
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = 0;
    if (chatWindow.value) {
      chatWindow.value.scrollTop = chatWindow.value.scrollHeight;
    }
  });
}

let resizeRaf = 0;
function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement;
  if (resizeRaf) cancelAnimationFrame(resizeRaf);
  resizeRaf = requestAnimationFrame(() => {
    resizeRaf = 0;
    const newHeight = Math.min(el.scrollHeight, 120);
    if (el.style.height !== newHeight + "px") {
      el.style.height = newHeight + "px";
    }
  });
}

const voiceSupported = ref(false);
const ttsSupported = ref(false);
const isListening = ref(false);
const autoRead = ref(false);
const lastAssistantMessage = ref("");
const recognition = ref<any>(null);

function initVoice() {
  const SpeechRecognitionCtor =
    (window as any).SpeechRecognition ||
    (window as any).webkitSpeechRecognition;
  voiceSupported.value = !!SpeechRecognitionCtor;
  ttsSupported.value =
    typeof window !== "undefined" && "speechSynthesis" in window;
  if (voiceSupported.value && SpeechRecognitionCtor) {
    recognition.value = new SpeechRecognitionCtor();
    recognition.value.continuous = false;
    recognition.value.interimResults = false;
    recognition.value.lang = "it-IT";
    recognition.value.onresult = (event: unknown) => {
      const ev = event as {
        results: { [key: number]: { [key: number]: { transcript: string } } };
      };
      const transcript = ev.results[0][0].transcript;
      userInput.value = transcript;
    };
    recognition.value.onend = () => {
      isListening.value = false;
    };
    recognition.value.onerror = () => {
      isListening.value = false;
    };
  }
}

function toggleVoice() {
  if (!recognition.value) return;
  if (isListening.value) {
    recognition.value.stop();
    isListening.value = false;
  } else {
    isListening.value = true;
    recognition.value.start();
  }
}

function toggleAutoRead() {
  const newAutoRead = !autoRead.value;
  autoRead.value = newAutoRead;
  if (!newAutoRead) {
    window.speechSynthesis.cancel();
  } else if (lastAssistantMessage.value) {
    speak(lastAssistantMessage.value);
  }
}

function speak(text: string) {
  if (!ttsSupported.value) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "it-IT";
  window.speechSynthesis.speak(utterance);
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || thinking.value) return;

  messages.value.push({ role: "user", content: text, time: getTime() });
  userInput.value = "";
  if (inputRef.value) {
    inputRef.value.style.height = "auto";
  }
  thinking.value = true;
  await scrollToBottom();

  const isBm2Question =
    /bm2|bike.master 2|analisi ride|simulazione|what if|power-meter|validazione/i.test(
      text,
    );

  try {
    if (isBm2Question) {
      const params: Record<string, unknown> = {};
      if (athleteId.value) params.athlete_id = athleteId.value;
      const resp = await apiPost<Record<string, unknown>>(
        "/api/v1/coach/chat/bm2",
        {
          message: text,
          ...params,
        },
      );
      const reply =
        (resp.response as string) ||
        (resp.message as string) ||
        (resp.advice as string) ||
        JSON.stringify(resp);
      messages.value.push({
        role: "assistant",
        content: reply,
        time: getTime(),
      });
      lastAssistantMessage.value = reply;
      if (autoRead.value) {
        speak(reply);
      }
      if (resp.bm2_result) {
        bm2Result.value = resp.bm2_result as Bm2CoachResult;
      }
    } else {
      const params: Record<string, unknown> = {};
      if (athleteId.value) params.athlete_id = athleteId.value;
      const resp = await apiPost<Record<string, unknown>>(
        "/api/v1/coach/chat",
        {
          message: text,
          ...params,
        },
      );
      const reply =
        (resp.response as string) ||
        (resp.message as string) ||
        (resp.advice as string) ||
        JSON.stringify(resp);
      messages.value.push({
        role: "assistant",
        content: reply,
        time: getTime(),
      });
      lastAssistantMessage.value = reply;
      if (autoRead.value) {
        speak(reply);
      }
    }
  } catch (e) {
    const err = e as Error | undefined;
    const detail = err?.message || String(e);
    const status = (err as ApiError & { status?: number })?.status;
    const isColdStart =
      status === 503 ||
      status === 502 ||
      status === 0 ||
      /non raggiungibile|fetch failed|network|Failed to fetch/i.test(detail);
    const userMsg = isColdStart
      ? "Il server cloud e' in avvio. Riprova tra 30-60 secondi."
      : "Errore nella risposta. " + detail;
    console.error("Coach chat error:", detail);
    messages.value.push({
      role: "assistant",
      content: userMsg,
      time: getTime(),
    });
    connected.value = false;
  } finally {
    thinking.value = false;
    await scrollToBottom();
  }
}

async function sendQuick(question: string) {
  userInput.value = question;
  await sendMessage();
}

async function loadFullReport() {
  if (!athleteId.value) return;
  loadingReport.value = true;
  try {
    const data = await apiGet<CoachData>("/api/v1/coach/full", {
      athlete_id: String(athleteId.value),
    });
    coachData.value = data;
    if (data.training_advice) {
      messages.value.push({
        role: "assistant",
        content: `** Report Completo**\n\n**Allenamento:**\n${data.training_advice}\n\n**Recupero:**\n${data.recovery_advice || "—"}`,
        time: getTime(),
      });
      await scrollToBottom();
    }
  } catch (e) {
    console.error("coach full", e);
  } finally {
    loadingReport.value = false;
  }
}

function clearChat() {
  messages.value = [];
}

async function init() {
  try {
    const me = await apiGet<{ athlete?: { id: number } }>(
      "/api/v1/athletes/me",
    );
    athleteId.value = me.athlete?.id ?? null;
    if (athleteId.value) {
      const scores = await apiGet<CoachData>("/api/v1/coach/full", {
        athlete_id: String(athleteId.value),
      });
      coachData.value = scores;
    }
  } catch (_e) {
    console.warn("init coach", _e);
  }

  if (import.meta.env.PROD) {
    void apiGet("/healthz", {}, { noRetry: true, timeoutMs: 3000 }).catch(
      () => {
        /* warm-up best-effort */
      },
    );
  }
}

onMounted(() => {
  init();
  initVoice();
});
</script>

<style scoped>
.coach-panel {
  display: flex;
  flex-direction: column;
  height: 70vh;
  min-height: 500px;
}

.coach-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.coach-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.coach-avatar {
  font-size: 2rem;
  background: var(--bg-secondary);
  border: 2px solid var(--accent);
  border-radius: 50%;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.coach-title h2 {
  margin: 0;
  font-size: 1.2rem;
  color: var(--accent);
}

.coach-status {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Score strip */
.score-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.score-pill {
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.pill-val {
  font-size: 1rem;
  font-weight: 700;
  font-family: "Outfit", sans-serif;
}

.pill-lbl {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Chat window */
.chat-window {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 12px 4px;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.chat-window::-webkit-scrollbar {
  width: 4px;
}
.chat-window::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}

/* Messages */
.message {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  animation: msgIn 0.3s ease;
}

.user-msg {
  flex-direction: row-reverse;
}

@keyframes msgIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.msg-avatar {
  font-size: 1.4rem;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: 50%;
  border: 1px solid var(--border);
}

.msg-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 80%;
}

.user-msg .msg-content {
  align-items: flex-end;
}

.msg-bubble {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 10px 14px;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-primary);
}

.user-msg .msg-bubble {
  background: rgba(0, 255, 204, 0.12);
  border-color: rgba(0, 255, 204, 0.25);
  color: var(--text-primary);
  border-radius: 16px 16px 4px 16px;
}

.bot-msg .msg-bubble {
  border-radius: 16px 16px 16px 4px;
}

.msg-time {
  font-size: 0.68rem;
  color: var(--text-muted);
  padding: 0 4px;
}

/* Typing indicator */
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 14px 16px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: bounce 1.2s infinite;
}
.dot:nth-child(2) {
  animation-delay: 0.2s;
}
.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-6px);
    opacity: 1;
  }
}

/* Quick actions */
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.quick-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: var(--transition);
  text-align: left;
}

.quick-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(0, 255, 204, 0.08);
  transform: translateY(-1px);
}

/* BM2 Physics Analysis */
.bm2-results {
  margin-top: 1rem;
  padding: 0.75rem;
  border: 1px solid #2a3b34;
  border-radius: 8px;
  background: #101c18;
}
.bm2-results h4 {
  margin: 0 0 0.75rem;
  color: var(--accent);
  font-size: 0.95rem;
}
.bm2-card {
  border: 1px solid #2a3b34;
  border-radius: 8px;
  padding: 0.75rem;
  margin-top: 0.75rem;
}
.bm2-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.bm2-value {
  font-weight: 700;
}
.bm2-card dl {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 2px 8px;
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
}
.bm2-card dt {
  color: #8aa;
}
.bm2-insights,
.bm2-sim {
  margin-top: 1rem;
}
.bm2-deltas {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
}
.bm2-up {
  color: #4ecca3;
  font-weight: 700;
}
.bm2-down {
  color: #ff6b6b;
  font-weight: 700;
}
.bm2-valgrid {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 2px 8px;
  font-size: 0.85rem;
  margin: 0.5rem 0 0;
}
.bm2-valgrid dt {
  color: #8aa;
}

/* Input area */
.chat-input-area {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  margin-top: 8px;
}

.chat-input {
  flex: 1;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 12px 18px;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-family: inherit;
  resize: none;
  outline: none;
  overflow: hidden;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
  min-height: 46px;
  max-height: 120px;
  line-height: 1.5;
}

.chat-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(0, 255, 204, 0.1);
}

.chat-input::placeholder {
  color: var(--text-muted);
}
.chat-input:disabled {
  opacity: 0.5;
}

.send-btn {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: none;
  background: var(--accent-gradient);
  color: #000;
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: var(--transition);
  box-shadow: 0 4px 12px rgba(0, 255, 204, 0.3);
}

.voice-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: var(--transition);
}

.voice-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.voice-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.voice-btn.listening {
  background: rgba(255, 80, 80, 0.15);
  border-color: #ff5050;
  color: #ff5050;
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(255, 80, 80, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(255, 80, 80, 0);
  }
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.1);
  box-shadow: 0 6px 18px rgba(0, 255, 204, 0.4);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .coach-panel {
    height: 60vh;
  }
  .msg-content {
    max-width: 90%;
  }
  .quick-actions {
    gap: 4px;
  }
  .quick-btn {
    font-size: 0.72rem;
    padding: 5px 10px;
  }
}

.ai-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0, 255, 204, 0.12);
  color: #42b983;
  border: 1px solid rgba(0, 255, 204, 0.35);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
