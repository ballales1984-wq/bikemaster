/**
 * useVoiceRecording — composable per registrazione audio vocale via MediaRecorder.
 *
 * Gestisce:
 * - Richiesta permessi microfono
 * - Avvio/arresto registrazione con stato visuale
 * - Conversione blob registrato in File per upload
 * - Riconoscimento supporto browser
 * - Visualizzazione livello audio (volume meter)
 */

import { ref, computed } from "vue";

type RecordingState = "idle" | "recording" | "processing" | "error";

export function useVoiceRecording() {
  const state = ref<RecordingState>("idle");
  const error = ref<string | null>(null);
  const audioBlob = ref<Blob | null>(null);
  const audioUrl = ref<string | null>(null);
  const volumeLevel = ref(0);
  const supported = ref(false);
  const permissionGranted = ref(false);

  let mediaRecorder: MediaRecorder | null = null;
  let audioContext: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let stream: MediaStream | null = null;
  let chunks: Blob[] = [];
  let animationId: number | null = null;
  let mimeType = "audio/webm";
  let stopResolve: ((blob: Blob | null) => void) | null = null;
  let cancelled = false;

  const isRecording = computed(() => state.value === "recording");
  const isProcessing = computed(() => state.value === "processing");

  async function checkSupport(): Promise<boolean> {
    if (typeof window === "undefined") return false;
    supported.value = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    return supported.value;
  }

  async function requestPermission(): Promise<boolean> {
    try {
      const perm = await navigator.permissions.query({ name: "microphone" });
      permissionGranted.value = perm.state === "granted";
      return permissionGranted.value || perm.state !== "denied";
    } catch {
      permissionGranted.value = true;
      return true;
    }
  }

  async function startRecording(): Promise<void> {
    if (state.value === "recording") return;
    cancelled = false;

    if (!supported.value) {
      error.value = "Registrazione audio non supportata dal browser";
      state.value = "error";
      return;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      permissionGranted.value = true;

      chunks = [];
      mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/mp4";

      mediaRecorder = new MediaRecorder(stream, { mimeType });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        if (cancelled) return;
        const blob = new Blob(chunks, { type: mimeType });
        audioBlob.value = blob;
        if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
        audioUrl.value = URL.createObjectURL(blob);
        state.value = "idle";
        cleanupStream();
        if (stopResolve) {
          stopResolve(blob);
          stopResolve = null;
        }
      };

      mediaRecorder.onerror = () => {
        error.value = "Errore durante la registrazione";
        state.value = "error";
        cleanupStream();
      };

      mediaRecorder.start(250);
      state.value = "recording";
      error.value = null;
      startVolumeMonitor();
    } catch {
      error.value = "Impossibile accedere al microfono";
      state.value = "error";
      permissionGranted.value = false;
    }
  }

  function stopRecording(): Promise<Blob | null> {
    return new Promise((resolve) => {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        stopResolve = resolve;
        mediaRecorder.stop();
      } else {
        resolve(audioBlob.value);
      }
      stopVolumeMonitor();
    });
  }

  function cancelRecording(): void {
    cancelled = true;
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    chunks = [];
    audioBlob.value = null;
    if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
    audioUrl.value = null;
    state.value = "idle";
    error.value = null;
    stopVolumeMonitor();
  }

  function getAudioFile(): File | null {
    if (!audioBlob.value) return null;
    const ext = audioBlob.value.type.includes("webm") ? "webm" : "mp4";
    return new File([audioBlob.value], `recording_${Date.now()}.${ext}`, {
      type: audioBlob.value.type,
    });
  }

  function startVolumeMonitor(): void {
    if (!stream) return;
    try {
      audioContext = new AudioContext();
      analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      analyser.fftSize = 256;
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      function updateVolume() {
        if (!analyser) return;
        analyser.getByteFrequencyData(dataArray);
        const sum = dataArray.reduce((a, b) => a + b, 0);
        volumeLevel.value = Math.min(100, Math.round((sum / dataArray.length / 255) * 100 * 3));
        animationId = requestAnimationFrame(updateVolume);
      }
      updateVolume();
    } catch {
      // Volume monitor not critical
    }
  }

  function stopVolumeMonitor(): void {
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
    if (audioContext) {
      audioContext.close().catch(() => {});
      audioContext = null;
      analyser = null;
    }
    volumeLevel.value = 0;
  }

  function cleanupStream(): void {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
  }

  function reset(): void {
    cancelRecording();
  }

  if (typeof window !== "undefined") {
    checkSupport();
  }

  return {
    state,
    error,
    audioBlob,
    audioUrl,
    volumeLevel,
    supported,
    permissionGranted,
    isRecording,
    isProcessing,
    checkSupport,
    requestPermission,
    startRecording,
    stopRecording,
    cancelRecording,
    getAudioFile,
    reset,
  };
}
