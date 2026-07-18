/**
 * Composable Voice Coach: TTS (speak) e STT (listen) via Web Speech API, con
 * fallback testuale se il browser non supporta le API. Riconosce comandi vocali
 * in italiano/inglese (stop, pause, resume, status) e notifica via handler
 * `on`. Espone gli stati `ttsSupported`/`sttSupported`/`isListening`/
 * `lastTranscript`/`lastCommand` e le azioni `speak`, `startListening`,
 * `stopListening`, `parseCommand`.
 */
import { ref, onBeforeUnmount } from "vue";
import type { ParsedVoiceCommand, VoiceCommand } from "../types/notifications";

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: unknown) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
}

const IT_COMMANDS: Record<VoiceCommand, string[]> = {
  stop: ["stop", "ferma", "fermati"],
  pause: ["pausa", "ferma un attimo"],
  resume: ["riprendi", "continua", "via"],
  status: ["come sto andando", "come va", "come stai andando", "come sto"],
  unknown: [],
};

const EN_COMMANDS: Record<VoiceCommand, string[]> = {
  stop: ["stop"],
  pause: ["pause"],
  resume: ["resume", "continue", "go"],
  status: ["how am i doing", "status", "how am i", "how's it going"],
  unknown: [],
};

function parseCommand(text: string, lang: "it" | "en"): ParsedVoiceCommand {
  const normalized = (text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z0-9\s]/g, "");
  const cmds = lang === "en" ? EN_COMMANDS : IT_COMMANDS;
  for (const key of Object.keys(cmds) as VoiceCommand[]) {
    if (key === "unknown") continue;
    for (const phrase of cmds[key]) {
      if (normalized.includes(phrase)) {
        return { command: key, raw: text, language: lang };
      }
    }
  }
  return { command: "unknown", raw: text, language: lang };
}

/**
 * Voice Coach composable: TTS (speak) + STT (listen) via the Web Speech API,
 * with a graceful textual fallback when the browser lacks support. Mirrors the
 * backend VoiceCoach decision layer for the live ride experience.
 */
export function useVoiceCoach(language: "it" | "en" = "it") {
  const ttsSupported = ref(false);
  const sttSupported = ref(false);
  const isListening = ref(false);
  const lastTranscript = ref("");
  const lastCommand = ref<ParsedVoiceCommand | null>(null);

  let recognition: SpeechRecognitionLike | null = null;

  if (typeof window !== "undefined") {
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: SpeechRecognitionCtor })
        .SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionCtor })
        .webkitSpeechRecognition;
    sttSupported.value = !!SpeechRecognition;
    ttsSupported.value =
      typeof window !== "undefined" && "speechSynthesis" in window;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = language === "en" ? "en-US" : "it-IT";
      rec.onresult = (event: unknown) => {
        const ev = event as {
          results: { [k: number]: { [j: number]: { transcript: string } } };
        };
        const transcript = ev.results[0][0].transcript;
        lastTranscript.value = transcript;
        lastCommand.value = parseCommand(transcript, language);
        onCommand(lastCommand.value);
      };
      rec.onend = () => {
        isListening.value = false;
      };
      rec.onerror = () => {
        isListening.value = false;
      };
      recognition = rec;
    }
  }

  const commandHandlers: Partial<Record<VoiceCommand, () => void>> = {};
  function onCommand(_cmd: ParsedVoiceCommand) {
    const handler = commandHandlers[_cmd.command];
    if (handler) handler();
  }

  function on(command: VoiceCommand, handler: () => void) {
    commandHandlers[command] = handler;
  }

  function speak(text: string) {
    if (!ttsSupported.value) return;
    const synth = (window as unknown as { speechSynthesis?: SpeechSynthesis })
      .speechSynthesis;
    if (!synth) return;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language === "en" ? "en-US" : "it-IT";
    synth.speak(utterance);
  }

  function startListening() {
    if (!recognition || isListening.value) return;
    isListening.value = true;
    recognition.start();
  }

  function stopListening() {
    if (!recognition) return;
    recognition.stop();
    isListening.value = false;
  }

  onBeforeUnmount(() => {
    stopListening();
  });

  const boundParse = (text: string) => parseCommand(text, language);

  return {
    ttsSupported,
    sttSupported,
    isListening,
    lastTranscript,
    lastCommand,
    on,
    speak,
    startListening,
    stopListening,
    parseCommand: boundParse,
  };
}
