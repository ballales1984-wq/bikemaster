<!--
  VoiceSystemProvider — coordinates the two voice subsystems
  (VoiceAssistant and VoiceCommandOverlay) so they never
  compete for getUserMedia / the audio device.
-->

<template>
  <div class="voice-system">
    <VoiceCommandOverlay v-if="!assistantActive" />
    <VoiceAssistant v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useVoiceSystemStore } from "../stores/voiceSystem";
import VoiceAssistant from "../components/VoiceAssistant.vue";
import VoiceCommandOverlay from "../components/VoiceCommandOverlay.vue";

const voiceSystem = useVoiceSystemStore();

const assistantActive = computed(() => voiceSystem.isAssistantActive);
</script>

<style scoped>
.voice-system {
  position: fixed;
  bottom: var(--voice-bottom, 24px);
  right: 24px;
  z-index: var(--z-voice);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  pointer-events: none;
}

.voice-system > * {
  pointer-events: auto;
}

@media (max-width: 480px) {
  .voice-system {
    right: 16px;
  }
}
</style>
