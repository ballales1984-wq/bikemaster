<!-- Boundary di errore: cattura le eccezioni dei componenti figli (hook errorCaptured) e mostra un messaggio di fallback.
     Props: nessuna. Eventi: nessuno. Se non ci sono errori renderizza lo slot default; altrimenti mostra titolo, messaggio e "Try Again".
     Accessibile (role=alert, aria-live) e ripristina il focus sull'errore. -->
<template>
  <div
v-if="error"
ref="boundary"
class="error-boundary"
data-test="error-boundary"
role="alert"
aria-live="assertive"
aria-atomic="true"
tabindex="-1"
>
    <div class="error-boundary-content">
      <div
class="error-boundary-icon" aria-hidden="true">⚠️</div>
      <h2 id="error-title"
class="error-boundary-title">
        Something went wrong
      </h2>
      <p
class="error-boundary-message" aria-describedby="error-title"
>
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
export default {
  name: "ErrorBoundary",
  data() {
    return {
      error: null as string | null,
    };
  },
  errorCaptured(err: unknown) {
    console.error("ErrorBoundary captured:", err);
    this.error =
      err instanceof Error ? err.message : String(err) || "Errore sconosciuto";
    this.$nextTick(() => {
      (this.$refs.boundary as HTMLElement | undefined)?.focus();
    });
    return false;
  },
  methods: {
    resetError() {
      this.error = null;
    },
  },
};
</script>
