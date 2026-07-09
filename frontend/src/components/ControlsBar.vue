<template>
  <div class="controls-bar"
role="group" aria-label="Tracking controls">
    <button
      v-if="isPaused"
      class="btn btn-primary"
      aria-label="Resume tracking"
      @click="$emit('resume')"
    >
      ▶ {{ t("tracking.resume") }}
    </button>
    <button
      v-else
      class="btn btn-secondary"
      aria-label="Pause tracking"
      @click="$emit('pause')"
    >
      ⏸ {{ t("tracking.pause") }}
    </button>
    <button
      class="btn btn-danger"
      aria-label="Stop tracking"
      @click="$emit('stop')"
    >
      ⏹ {{ t("tracking.stop") }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "../composables/useI18n";

const { t } = useI18n();

defineProps<{ isPaused: boolean }>();
defineEmits<{
  (e: "pause"): void;
  (e: "resume"): void;
  (e: "stop"): void;
}>();
</script>

<style scoped>
.controls-bar {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 16px 0;
}
</style>
