/**
 * VoiceSystemStore — coordinates the two voice subsystems
 * (VoiceAssistant and VoiceCommandOverlay) so they never
 * compete for getUserMedia / the audio device.
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";

export type VoiceSystem = "none" | "assistant" | "commands";

export const useVoiceSystemStore = defineStore("voiceSystem", () => {
  const activeSystem = ref<VoiceSystem>("none");
  const micBusy = ref(false);

  const isAssistantActive = computed(() => activeSystem.value === "assistant");
  const isCommandsActive = computed(() => activeSystem.value === "commands");
  const isAnyActive = computed(() => activeSystem.value !== "none");

  function activateAssistant(): void {
    deactivateCommands();
    activeSystem.value = "assistant";
  }

  function activateCommands(): void {
    deactivateAssistant();
    activeSystem.value = "commands";
  }

  function deactivateAssistant(): void {
    if (activeSystem.value === "assistant") {
      activeSystem.value = "none";
    }
  }

  function deactivateCommands(): void {
    if (activeSystem.value === "commands") {
      activeSystem.value = "none";
    }
  }

  function setMicBusy(busy: boolean): void {
    micBusy.value = busy;
  }

  return {
    activeSystem,
    micBusy,
    isAssistantActive,
    isCommandsActive,
    isAnyActive,
    activateAssistant,
    activateCommands,
    deactivateAssistant,
    deactivateCommands,
    setMicBusy,
  };
});
