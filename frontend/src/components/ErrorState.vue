<!-- Stato di errore riutilizzabile: messaggio di errore con icona, titolo, descrizione e pulsante "Retry" opzionale.
     Props: title, message, showRetry (default true). Eventi: retry (click sul pulsante). UI: icona , testo centrato e bottone primario. -->
<template>
  <div class="error-state">
    <div class="error-icon"></div>
    <div class="error-title">
      {{ title }}
    </div>
    <div class="error-desc">
      {{ message }}
    </div>
    <button
      v-if="showRetry"
      class="btn btn-primary retry-btn"
      @click="$emit('retry')"
    >
      Retry
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps({
  title: { type: String, default: "Loading error" },
  message: { type: String, default: "Unable to load data. Try again later." },
  showRetry: { type: Boolean, default: true },
});
defineEmits(["retry"]);
</script>

<style scoped>
.error-state {
  text-align: center;
  padding: 30px 20px;
  color: var(--error);
}

.error-icon {
  font-size: 2.5rem;
  margin-bottom: 10px;
}

.error-title {
  font-size: 1.1rem;
  font-weight: bold;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.error-desc {
  font-size: 0.9rem;
  color: var(--text-secondary);
  max-width: 360px;
  margin: 0 auto;
}

.retry-btn {
  margin-top: 14px;
}
</style>
