<template>
  <div
    v-if="error"
    class="error-boundary"
    data-test="error-boundary"
    role="alert"
    aria-live="polite"
    tabindex="-1"
  >
    <div class="error-boundary-content">
      <div
class="error-boundary-icon" aria-hidden="true">⚠️</div>
      <h2 id="error-title" class="error-boundary-title">
        Something went wrong
      </h2>
      <p class="error-boundary-message"
aria-describedby="error-title">
        {{ error }}
      </p>
      <button
        class="btn btn-primary"
        aria-label="Try again"
        @click="resetError"
      >
        🔄 Try Again
      </button>
    </div>
  </div>
  <slot v-else />
</template>

<script lang="ts">
import { onErrorCaptured } from "vue";

export default {
  name: "ErrorBoundary",
  data() {
    return {
      error: null as string | null,
    };
  },
  mounted() {
    onErrorCaptured((err: unknown) => {
      this.error = err instanceof Error ? err.message : String(err);
      return false;
    });
  },
  methods: {
    resetError() {
      this.error = null;
    },
  },
};
</script>
