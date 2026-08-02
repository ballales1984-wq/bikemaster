<!--
  VoiceCommandOverlay — floating voice command UI.

  Features:
  - Floating mic button to start/stop voice recognition
  - Expandable panel showing last transcript, result, and command log
  - Auto-listen toggle
  - Command reference list
-->

<template>
  <div v-if="store.isSupported" class="voice-overlay">
    <button
      class="voice-fab"
      :class="{
        listening: store.isListening,
        processing: store.isProcessing,
      }"
      :title="
        store.isListening
          ? 'Ferma riconoscimento'
          : 'Avvia riconoscimento vocale'
      "
      @click="toggleListening"
    >
      <svg
        v-if="!store.isListening && !store.isProcessing"
        viewBox="0 0 24 24"
        width="22"
        height="22"
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
        v-else-if="store.isProcessing"
        viewBox="0 0 24 24"
        width="22"
        height="22"
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
        v-else
        viewBox="0 0 24 24"
        width="22"
        height="22"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <rect x="4" y="4" width="16" height="16" rx="2" />
        <line x1="9" y1="9" x2="15" y2="15" />
        <line x1="15" y1="9" x2="9" y2="15" />
      </svg>
    </button>

    <transition name="voice-panel">
      <div v-if="expanded" class="voice-panel">
        <div class="voice-panel-header">
          <h3>Comandi vocali</h3>
          <div class="voice-panel-actions">
            <label class="toggle-label">
              <input
                v-model="autoListenModel"
                type="checkbox"
                @change="onToggleAuto"
              />
              <span>Auto</span>
            </label>
            <button class="close-btn" @click="expanded = false">&times;</button>
          </div>
        </div>

        <div class="voice-panel-body">
          <div v-if="store.isListening" class="listening-indicator">
            <span class="pulse"></span>
            <span>In ascolto...</span>
          </div>

          <div v-if="store.lastTranscript" class="transcript-box">
            <label>Trascrizione</label>
            <p>{{ store.lastTranscript }}</p>
          </div>

          <div
            v-if="store.lastResult"
            class="result-box"
            :class="store.lastResult.success ? 'success' : 'error'"
          >
            <label>Risultato</label>
            <p>{{ store.lastResult.message }}</p>
          </div>

          <div v-if="store.error" class="error-box">
            <p>{{ store.error }}</p>
            <button @click="store.clearError">Chiudi</button>
          </div>

          <div class="history-section">
            <div class="history-header">
              <span>Cronologia</span>
              <button
                v-if="store.commandHistory.length"
                @click="store.clearLog"
              >
                Cancella
              </button>
            </div>
            <div v-if="!store.commandHistory.length" class="empty-history">
              Nessun comando registrato
            </div>
            <div v-else class="history-list">
              <div
                v-for="entry in store.commandHistory"
                :key="entry.id"
                class="history-entry"
                :class="{ success: entry.success, error: !entry.success }"
              >
                <span class="history-time">{{
                  formatTime(entry.timestamp)
                }}</span>
                <span class="history-transcript">{{ entry.transcript }}</span>
                <span class="history-message">{{ entry.message }}</span>
              </div>
            </div>
          </div>

          <div class="commands-ref">
            <label>Comandi disponibili</label>
            <div class="command-chips">
              <span
                v-for="cmd in store.commands"
                :key="cmd.id"
                class="command-chip"
                :title="cmd.description"
              >
                {{ cmd.label }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useVoiceCommandsStore } from "../stores/voiceCommands";
import { useVoiceSystemStore } from "../stores/voiceSystem";

const store = useVoiceCommandsStore();
const voiceSystem = useVoiceSystemStore();
const expanded = ref(false);

const autoListenModel = computed({
  get: () => store.autoListen,
  set: (v: boolean) => {
    store.autoListen = v;
  },
});

watch(
  () => voiceSystem.isAssistantActive,
  (active) => {
    if (active && store.isListening) {
      store.stopListening();
      expanded.value = false;
    }
  },
);

function toggleListening(): void {
  if (store.isListening) {
    store.stopListening();
  } else {
    if (voiceSystem.micBusy) {
      voiceSystem.activateAssistant();
      return;
    }
    voiceSystem.activateCommands();
    store.startListening();
    expanded.value = true;
  }
}

function onToggleAuto(): void {
  store.toggleAutoListen();
}

function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString("it-IT", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
</script>

<style scoped>
.voice-overlay {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.voice-fab {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.voice-fab:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 16px rgba(0, 255, 204, 0.2);
}

.voice-fab.listening {
  background: var(--accent);
  color: var(--bg-primary);
  border-color: var(--accent);
  animation: pulse 2s infinite;
}

.voice-fab.processing {
  background: var(--accent);
  color: var(--bg-primary);
  border-color: var(--accent);
}

.voice-panel {
  width: 380px;
  max-height: 500px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.voice-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.voice-panel-header h3 {
  margin: 0;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.voice-panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.toggle-label input {
  accent-color: var(--accent);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.4rem;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}

.voice-panel-body {
  padding: 12px 16px;
  overflow-y: auto;
  max-height: 460px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.listening-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--accent);
}

.pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.5s infinite;
}

.transcript-box label,
.result-box label,
.error-box label,
.history-header,
.commands-ref label {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.transcript-box p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  padding: 8px 10px;
  border-radius: 6px;
}

.result-box {
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 0.85rem;
}

.result-box.success {
  background: rgba(0, 255, 204, 0.1);
  border: 1px solid rgba(0, 255, 204, 0.2);
}

.result-box.error {
  background: rgba(255, 80, 80, 0.1);
  border: 1px solid rgba(255, 80, 80, 0.2);
}

.result-box p {
  margin: 0;
}

.error-box {
  background: rgba(255, 80, 80, 0.1);
  border: 1px solid rgba(255, 80, 80, 0.2);
  padding: 8px 10px;
  border-radius: 6px;
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
}

.history-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
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
}

.history-header button {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.75rem;
}

.empty-history {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-align: center;
  padding: 8px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 160px;
  overflow-y: auto;
}

.history-entry {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--bg-tertiary);
  font-size: 0.8rem;
}

.history-entry.success {
  border-left: 3px solid var(--accent);
}

.history-entry.error {
  border-left: 3px solid var(--error);
}

.history-time {
  color: var(--text-muted);
  font-size: 0.7rem;
  flex-shrink: 0;
}

.history-transcript {
  color: var(--text-primary);
  flex: 1;
  min-width: 100px;
}

.history-message {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.commands-ref {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.command-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.command-chip {
  font-size: 0.75rem;
  padding: 3px 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-secondary);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.1);
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
    opacity 0.2s ease,
    transform 0.2s ease;
}

.voice-panel-enter-from,
.voice-panel-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.96);
}
</style>
