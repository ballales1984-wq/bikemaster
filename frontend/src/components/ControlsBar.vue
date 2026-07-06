<template>
  <div class="controls-bar" role="group" aria-label="Tracking controls">
    <button v-if="isPaused" class="btn btn-primary" @click="$emit('resume')" aria-label="Resume tracking">
      ▶ {{ t('tracking.resume') }}
    </button>
    <button v-else class="btn btn-secondary" @click="$emit('pause')" aria-label="Pause tracking">
      ⏸ {{ t('tracking.pause') }}
    </button>
    <button class="btn btn-danger" @click="$emit('stop')" aria-label="Stop tracking">
      ⏹ {{ t('tracking.stop') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '../composables/useI18n'

const { t } = useI18n()

defineProps<{ isPaused: boolean }>()
defineEmits<{
  (e: 'pause'): void
  (e: 'resume'): void
  (e: 'stop'): void
}>()
</script>

<style scoped>
.controls-bar {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 16px 0;
}
</style>