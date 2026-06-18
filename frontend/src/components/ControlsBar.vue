<template>
  <div class="controls-bar">
    <button v-if="isPaused" class="btn btn-primary" @click="$emit('resume')">
      ▶ Riprendi
    </button>
    <button v-else class="btn btn-secondary" @click="$emit('pause')">
      ⏸ Pausa
    </button>
    <button class="btn btn-danger" @click="$emit('stop')">
      ⏹ Termina
    </button>
  </div>
</template>

<script setup lang="ts">
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