/**
 * Voice commands Pinia store.
 *
 * Manages the Web Speech API recognition lifecycle,
 * command execution, and command history.
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  createCommandRegistry,
  parseTranscript,
  createLogEntry,
} from "../services/voiceCommands";
import type {
  VoiceCommandResult,
  VoiceCommandLogEntry,
  RecognitionState,
} from "../types/voiceCommands";
import type {
  SpeechRecognitionEvent,
  SpeechRecognitionErrorEvent,
} from "../types/speechRecognition";

export const useVoiceCommandsStore = defineStore("voiceCommands", () => {
  const commands = createCommandRegistry();
  const recognition = ref<any>(null);
  const state = ref<RecognitionState>({
    isListening: false,
    isProcessing: false,
    lastTranscript: "",
    lastResult: null,
    error: null,
    supported:
      typeof window !== "undefined" &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window),
  });
  const log = ref<VoiceCommandLogEntry[]>([]);
  const autoListen = ref(false);
  const wakeWordEnabled = ref(false);

  const isSupported = computed(() => state.value.supported);
  const isListening = computed(() => state.value.isListening);
  const isProcessing = computed(() => state.value.isProcessing);
  const error = computed(() => state.value.error);
  const lastTranscript = computed(() => state.value.lastTranscript);
  const lastResult = computed(() => state.value.lastResult);
  const commandHistory = computed(() => log.value);

  function clearError() {
    state.value.error = null;
  }

  function initRecognition(): any {
    if (!state.value.supported) return null;
    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) return null;

    const rec = new SpeechRecognitionCtor();
    rec.continuous = true;
    rec.interimResults = false;
    rec.lang = "it-IT";

    rec.onstart = () => {
      state.value.isListening = true;
      state.value.error = null;
    };

    rec.onend = () => {
      state.value.isListening = false;
      if (autoListen.value && !state.value.isProcessing) {
        try {
          setTimeout(() => startListening(), 300);
        } catch {
          // ignore restart errors
        }
      }
    };

    rec.onerror = (ev: SpeechRecognitionErrorEvent) => {
      if (ev.error === "no-speech" || ev.error === "aborted") {
        return;
      }
      state.value.error = `Errore riconoscimento: ${ev.error}`;
      state.value.isListening = false;
    };

    rec.onresult = (event: SpeechRecognitionEvent) => {
      const result = event.results[event.resultIndex];
      if (!result || !result[0]) return;
      const transcript = result[0].transcript.trim();
      if (!transcript) return;

      state.value.lastTranscript = transcript;
      executeTranscript(transcript);
    };

    recognition.value = rec;
    return rec;
  }

  function startListening(): void {
    if (!state.value.supported) {
      state.value.error = "Riconoscimento vocale non supportato dal browser";
      return;
    }
    if (state.value.isListening) return;

    let rec = recognition.value;
    if (!rec) {
      rec = initRecognition();
    }
    if (!rec) return;

    try {
      rec.start();
    } catch {
      state.value.error = "Impossibile avviare il riconoscimento vocale";
    }
  }

  function stopListening(): void {
    if (recognition.value && state.value.isListening) {
      recognition.value.abort();
    }
    autoListen.value = false;
    state.value.isListening = false;
  }

  async function executeTranscript(transcript: string): Promise<void> {
    state.value.isProcessing = true;
    try {
      const parsed = parseTranscript(transcript, commands);
      let result: VoiceCommandResult;

      if (!parsed) {
        result = {
          success: false,
          message: `Comando non riconosciuto: "${transcript}"`,
        };
      } else {
        try {
          result = await parsed.definition.execute(parsed.params);
        } catch (e) {
          result = {
            success: false,
            message:
              e instanceof Error ? e.message : "Errore durante l'esecuzione",
          };
        }
      }

      state.value.lastResult = result;
      const entry = createLogEntry(transcript, parsed, result);
      log.value.unshift(entry);
      if (log.value.length > 100) {
        log.value = log.value.slice(0, 100);
      }
    } finally {
      state.value.isProcessing = false;
    }
  }

  function toggleAutoListen(): void {
    autoListen.value = !autoListen.value;
    if (autoListen.value && !state.value.isListening) {
      startListening();
    } else if (!autoListen.value && state.value.isListening) {
      stopListening();
    }
  }

  function clearLog(): void {
    log.value = [];
  }

  if (
    typeof window !== "undefined" &&
    state.value.supported &&
    !recognition.value
  ) {
    initRecognition();
  }

  return {
    commands,
    state,
    log,
    autoListen,
    wakeWordEnabled,
    isSupported,
    isListening,
    isProcessing,
    error,
    lastTranscript,
    lastResult,
    commandHistory,
    startListening,
    stopListening,
    executeTranscript,
    toggleAutoListen,
    clearError,
    clearLog,
  };
});
