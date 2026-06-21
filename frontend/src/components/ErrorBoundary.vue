<template>
  <div v-if="error" class="error-boundary" data-test="error-boundary">
    <div class="error-boundary-content">
      <div class="error-boundary-icon">⚠️</div>
      <h2 class="error-boundary-title">Something went wrong</h2>
      <p class="error-boundary-message">{{ error }}</p>
      <button class="btn btn-primary" @click="resetError">🔄 Try Again</button>
    </div>
  </div>
  <slot v-else />
</template>

<script>
import { onErrorCaptured } from 'vue'

export default {
  name: 'ErrorBoundary',
  data() {
    return {
      error: null,
    }
  },
  mounted() {
    onErrorCaptured((err) => {
      this.error = err instanceof Error ? err.message : String(err)
      return false
    })
  },
  methods: {
    resetError() {
      this.error = null
    },
  },
}
</script>
