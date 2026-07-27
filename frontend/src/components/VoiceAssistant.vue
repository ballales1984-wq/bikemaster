<!--
  VoiceAssistant — full conversational voice assistant UI.

  Features:
  - Mic button with push-to-talk / toggle mode
  - Animated listening indicator (waveform/pulse)
  - Real-time transcript display
  - Assistant response with TTS playback
  - Conversation history (bubble list)
  - Continuous mode toggle (like Google Assistant)
  - Status messages (listening, processing, speaking)
-->

<template>
  <div v-if="supported" class="voice-assistant">
    <!-- Floating FAB -->
    <button
      class="assistant-fab"
      :class="{
        listening: isListening,
        processing: isProcessing,
        speaking: isSpeaking,
      }"
      :title="fabTitle"
      @click="toggleAssistant"
    >
      <svg
        v-if="!isListening && !isProcessing && !isSpeaking"
        viewBox="0 0 24 24"
        width="24"
        height="24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
      </svg>
      <svg
        v-else-if="isListening"
        viewBox="0 0 24 24"
        width="24"
        height="24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <rect x="6" y="6" width="12" height="12" rx="2" />
      </svg>
      <svg
        v-else-if="isProcessing"
        viewBox="0 0 24 24"
        width="24"
        height="24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="spin"
      >
        <path
          d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"
        />
      </svg>
      <svg
        v-else-if="isSpeaking"
        viewBox="0 0 24 24"
        width="24"
        height="24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
      </svg>
    </button>

    <!-- Listening indicator -->
    <div v-if="isListening" class="listening-badge">
      <span class="listening-dot"></span>
      In ascolto...
    </div>

    <!-- Conversation panel -->
    <transition name="voice-panel">
      <div v-if="expanded" class="voice-panel">
        <div class="panel-header">
          <h3>Assistente Vocale</h3>
          <div class="panel-actions">
            <label class="toggle-label" title="Conversazione continua">
              <input v-model="continuousModel" type="checkbox" />
              <span>Continua</span>
            </label>
            <button class="close-btn" @click="expanded = false">&times;</button>
          </div>
        </div>

        <div class="panel-body">
          <!-- Volume meter -->
          <div v-if="isListening" class="volume-meter">
            <div class="volume-bar" :style="{ width: volumeLevel + '%' }"></div>
          </div>

          <!-- Status -->
          <div v-if="status" class="status-message" :class="statusClass">
            {{ status }}
          </div>

          <!-- Transcript -->
          <div v-if="lastTranscript" class="transcript-box user">
            <span class="transcript-label">Tu</span>
            <p>{{ lastTranscript }}</p>
          </div>

          <!-- Assistant response -->
          <div v-if="lastResponse" class="transcript-box assistant">
            <span class="transcript-label">Assistente</span>
            <p>{{ lastResponse }}</p>
          </div>

          <!-- Error -->
          <div v-if="error" class="error-box">
            <p>{{ error }}</p>
            <button @click="error = null">Chiudi</button>
          </div>

          <!-- History -->
          <div class="history-section">
            <div class="history-header">
              <span>Cronologia</span>
              <button v-if="history.length" @click="history = []">
                Cancella
              </button>
            </div>
            <div v-if="!history.length" class="empty-history">
              Premi il microfono per iniziare
            </div>
            <div v-else class="history-list">
              <div
                v-for="(entry, idx) in history"
                :key="idx"
                class="history-entry"
                :class="entry.role"
              >
                <span class="role-badge" :class="entry.role">{{
                  entry.role === "user" ? "Tu" : "AI"
                }}</span>
                <span class="entry-text">{{ entry.text }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from "vue";
import { useVoiceRecording } from "../composables/useVoiceRecording";
import { useVoiceCommandsStore } from "../stores/voiceCommands";
import { useVoiceSystemStore } from "../stores/voiceSystem";

const recording = useVoiceRecording();
const voiceStore = useVoiceCommandsStore();
const voiceSystem = useVoiceSystemStore();

const expanded = ref(false);
const continuousModel = ref(false);
const lastTranscript = ref("");
const lastResponse = ref("");
const status = ref("");
const history = ref<{ role: "user" | "assistant"; text: string }[]>([]);
const error = ref<string | null>(null);
const isSpeaking = ref(false);
const currentAudio: { current: HTMLAudioElement | null } = { current: null };
const sessionId = ref(`session_${Date.now()}`);
const isProcessingStop = ref(false);
let continuousTimeout: number | null = null;

const supported = computed(() => recording.supported);
const isListening = computed(() => recording.isRecording);
const isProcessing = computed(() => recording.isProcessing);
const volumeLevel = computed(() => recording.volumeLevel);

const fabTitle = computed(() => {
  if (isListening.value) return "Ferma registrazione";
  if (isProcessing.value) return "Elaborazione...";
  if (isSpeaking.value) return "Riproduzione risposta";
  return "Assistente vocale";
});

const statusClass = computed(() => {
  if (isListening.value) return "listening";
  if (isProcessing.value) return "processing";
  if (isSpeaking.value) return "speaking";
  return "";
});

function setStatus(msg: string) {
  status.value = msg;
}

async function toggleAssistant(): Promise<void> {
  if (isProcessingStop.value) {
    stopSpeaking();
    recording.cancelRecording();
    voiceSystem.deactivateAssistant();
    voiceSystem.setMicBusy(false);
    return;
  }
  if (isSpeaking.value) {
    stopSpeaking();
  } else if (isListening.value) {
    await stopAndProcess();
  } else {
    voiceSystem.activateAssistant();
    await startListening();
  }
}

function stopSpeaking(): void {
  if (continuousTimeout) {
    clearTimeout(continuousTimeout);
    continuousTimeout = null;
  }
  if (currentAudio.current) {
    currentAudio.current.pause();
    currentAudio.current = null;
  }
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  isSpeaking.value = false;
  setStatus("");
  voiceSystem.setMicBusy(false);
}

async function startListening(): Promise<void> {
  if (!recording.supported) {
    error.value = "Registrazione audio non supportata";
    return;
  }

  error.value = null;
  lastTranscript.value = "";
  lastResponse.value = "";
  setStatus("");

  voiceStore.stopListening();
  recording.cancelRecording();

  voiceSystem.activateAssistant();
  voiceSystem.setMicBusy(true);

  try {
    await recording.startRecording();
    expanded.value = true;
    setStatus("In ascolo...");

    if (continuousModel.value) {
      continuousTimeout = window.setTimeout(() => {
        continuousTimeout = null;
        if (recording.isRecording) {
          stopAndProcess();
        }
      }, 8000);
    }
  } catch {
    error.value = "Impossibile avviare la registrazione";
  }
}

async function stopAndProcess(): Promise<void> {
  if (isProcessingStop.value) return;
  if (continuousTimeout) {
    clearTimeout(continuousTimeout);
    continuousTimeout = null;
  }
  isProcessingStop.value = true;

  let file = recording.getAudioFile();
  if (!file) {
    const blob = await recording.stopRecording();
    if (!blob) {
      isProcessingStop.value = false;
      return;
    }
    file = new File([blob], `recording_${Date.now()}.webm`, {
      type: blob.type,
    });
  }

  setStatus("Elaborazione...");
  recording.state.value = "processing";

  try {
    const formData = new FormData();
    formData.append("file", file);

    const token = localStorage.getItem("bikemaster_token") || "";

    const response = await fetch("/api/v1/voice/stt", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || "STT failed");
    }

    const sttResult = (await response.json()) as { text: string };
    const transcript = sttResult.text.trim();

    if (!transcript) {
      setStatus("Nessun audio riconosciuto");
      recording.state.value = "idle";
      voiceSystem.setMicBusy(false);
      return;
    }

    lastTranscript.value = transcript;
    history.value.push({ role: "user", text: transcript });
    setStatus("Risposta in corso...");

    await getAssistantResponse(transcript);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "Errore di elaborazione";
    recording.state.value = "idle";
    setStatus("");
  } finally {
    isProcessingStop.value = false;
    voiceSystem.setMicBusy(false);
  }
}

async function getAssistantResponse(text: string): Promise<void> {
  try {
    const token = localStorage.getItem("bikemaster_token") || "";

    const response = await fetch("/api/v1/voice/assistant", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ text, session_id: sessionId.value }),
    });

    if (!response.ok) {
      throw new Error("Assistant failed");
    }

    const result = (await response.json()) as {
      text: string;
      audio_url: string | null;
      intent: string | null;
      session_id: string;
    };

    lastResponse.value = result.text;
    history.value.push({ role: "assistant", text: result.text });
    sessionId.value = result.session_id;

    setStatus("");
    recording.state.value = "idle";

    // Execute intent if any
    if (result.intent && result.intent !== "general") {
      await executeIntent(result.intent, text);
    }

    // Play TTS audio
    if (result.audio_url) {
      await playAudio(result.audio_url);
    } else {
      // Fallback: use browser TTS
      speakBrowser(text);
    }

    // Continuous mode: restart listening after response
    if (continuousModel.value) {
      setStatus("In ascolo...");
      setTimeout(() => {
        if (continuousModel.value && !isSpeaking.value) {
          startListening();
        }
      }, 1500);
    }
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "Errore assistente";
    recording.state.value = "idle";
    setStatus("");
  }
}

async function playAudio(url: string): Promise<void> {
  try {
    if (currentAudio.current) {
      currentAudio.current.pause();
      currentAudio.current = null;
    }
    const audio = new Audio(url);
    currentAudio.current = audio;
    isSpeaking.value = true;
    setStatus("Riproduzione...");

    await new Promise<void>((resolve, reject) => {
      audio.onended = () => {
        isSpeaking.value = false;
        setStatus("");
        currentAudio.current = null;
        resolve();
      };
      audio.onerror = () => {
        isSpeaking.value = false;
        setStatus("");
        currentAudio.current = null;
        reject(new Error("Audio playback failed"));
      };
      audio.play().catch(reject);
    });
  } catch {
    isSpeaking.value = false;
    setStatus("");
  }
}

function speakBrowser(text: string): void {
  if (!("speechSynthesis" in window)) return;
  const synth = window.speechSynthesis;
  synth.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "it-IT";
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.onend = () => {
    isSpeaking.value = false;
    setStatus("");
  };
  isSpeaking.value = true;
  setStatus("Riproduzione...");
  synth.speak(utterance);
}

async function executeIntent(intent: string, text: string): Promise<void> {
  // Map intent to existing voice command store actions
  const lower = text.toLowerCase();
  try {
    switch (intent) {
      case "navigation": {
        const viewMatch = lower.match(/(?:apri|vai a|mostra)\s+(.+)/);
        if (viewMatch) {
          const view = viewMatch[1].trim();
          const router = (await import("../router/index")).default;
          const map: Record<string, string> = {
            calendario: "/calendar",
            uscite: "/rides",
            dashboard: "/dashboard",
            mappe: "/map",
            meteo: "/weather",
            profilo: "/athlete",
            metabolismo: "/metabolism",
            tracciamento: "/track",
            importa: "/import",
            connessioni: "/settings/connections",
            impostazioni: "/settings",
          };
          const path = map[view];
          if (path) router.push(path);
        }
        break;
      }
      case "add_ride": {
        const router = (await import("../router/index")).default;
        router.push("/rides");
        break;
      }
      default:
        break;
    }
  } catch {
    // Intent execution is best-effort
  }
}

function cleanup(): void {
  recording.cancelRecording();
  voiceStore.stopListening();
  voiceSystem.deactivateAssistant();
  voiceSystem.setMicBusy(false);
  if (currentAudio.current) {
    currentAudio.current.pause();
  }
  if (continuousTimeout) {
    clearTimeout(continuousTimeout);
    continuousTimeout = null;
  }
}

onBeforeUnmount(cleanup);
</script>

<style scoped>
.voice-assistant {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 900;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.assistant-fab {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), #00b894);
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 20px rgba(0, 255, 204, 0.35);
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.assistant-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 8px 28px rgba(0, 255, 204, 0.5);
}

.assistant-fab.listening {
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
  animation: pulse-fab 1.5s infinite;
}

.assistant-fab.processing {
  background: linear-gradient(135deg, #feca57, #ff9f43);
  box-shadow: 0 6px 20px rgba(254, 202, 87, 0.4);
}

.assistant-fab.speaking {
  background: linear-gradient(135deg, #54a0ff, #2e86de);
  box-shadow: 0 6px 20px rgba(84, 160, 255, 0.4);
}

.listening-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: #ff6b6b;
  background: var(--bg-secondary);
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 107, 107, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.listening-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff6b6b;
  animation: pulse-dot 1.2s infinite;
}

.voice-panel {
  width: 420px;
  max-height: 560px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(
    135deg,
    rgba(0, 255, 204, 0.05),
    rgba(0, 184, 148, 0.05)
  );
}

.panel-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}

.toggle-label input {
  accent-color: var(--accent);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}

.close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.panel-body {
  padding: 14px 18px;
  overflow-y: auto;
  max-height: 520px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.volume-meter {
  width: 100%;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.volume-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #00b894);
  border-radius: 3px;
  transition: width 0.1s ease;
}

.status-message {
  font-size: 0.85rem;
  text-align: center;
  padding: 6px;
  border-radius: 6px;
}

.status-message.listening {
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.1);
}

.status-message.processing {
  color: #feca57;
  background: rgba(254, 202, 87, 0.1);
}

.status-message.speaking {
  color: #54a0ff;
  background: rgba(84, 160, 255, 0.1);
}

.transcript-box {
  padding: 10px 12px;
  border-radius: 12px;
  max-width: 90%;
}

.transcript-box.user {
  background: rgba(0, 255, 204, 0.08);
  border: 1px solid rgba(0, 255, 204, 0.2);
  align-self: flex-end;
  border-bottom-right-radius: 4px;
}

.transcript-box.assistant {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  align-self: flex-start;
  border-bottom-left-radius: 4px;
}

.transcript-label {
  display: block;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 4px;
  font-weight: 600;
}

.transcript-box p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-primary);
  line-height: 1.4;
}

.error-box {
  background: rgba(255, 80, 80, 0.1);
  border: 1px solid rgba(255, 80, 80, 0.2);
  padding: 8px 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.error-box p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--error);
}

.error-box button {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8rem;
  padding: 4px 8px;
  border-radius: 4px;
}

.error-box button:hover {
  background: var(--bg-tertiary);
}

.history-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px solid var(--border);
  padding-top: 8px;
  margin-top: 4px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-header span {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  font-weight: 600;
}

.history-header button {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.empty-history {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-align: center;
  padding: 10px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
}

.history-entry {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 0.8rem;
}

.history-entry.user {
  background: rgba(0, 255, 204, 0.05);
  justify-content: flex-end;
}

.history-entry.assistant {
  background: var(--bg-tertiary);
  justify-content: flex-start;
}

.role-badge {
  font-size: 0.65rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  flex-shrink: 0;
}

.role-badge.user {
  background: rgba(0, 255, 204, 0.15);
  color: var(--accent);
}

.role-badge.assistant {
  background: rgba(84, 160, 255, 0.15);
  color: #54a0ff;
}

.entry-text {
  color: var(--text-secondary);
  line-height: 1.3;
}

@keyframes pulse-fab {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.12);
  }
}

@keyframes pulse-dot {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.4;
    transform: scale(1.4);
  }
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.voice-panel-enter-active,
.voice-panel-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}

.voice-panel-enter-from,
.voice-panel-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.95);
}
</style>
