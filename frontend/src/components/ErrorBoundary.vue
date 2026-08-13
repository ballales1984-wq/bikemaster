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
      <div class="error-boundary-icon" aria-hidden="true"></div>
      <h2 id="error-title" class="error-boundary-title">
        {{ t("errorBoundary.title") }}
      </h2>
      <p class="error-boundary-message" aria-describedby="error-title">
        {{ error }}
      </p>
      <button
        class="btn btn-primary"
        :aria-label="t('errorBoundary.tryAgain')"
        @click="resetError"
      >
        {{ t("errorBoundary.tryAgain") }}
      </button>
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, onErrorCaptured, nextTick } from "vue";
import { useI18n } from "../composables/useI18n";

const { t } = useI18n();
const error = ref<string | null>(null);
const boundary = ref<HTMLElement | null>(null);

onErrorCaptured((err: unknown) => {
  console.error("ErrorBoundary captured:", err);
  error.value =
    err instanceof Error ? err.message : String(err) || "Errore sconosciuto";
  nextTick().then(() => {
    boundary.value?.focus();
  });
  return false;
});

function resetError() {
  error.value = null;
}
</script>
