<!-- Stato vuoto riutilizzabile: messaggio "nessun dato" con icona/scelta, titolo, descrizione e pulsante azione opzionale.
     Props: title (obbligatorio), description, icon, actionLabel, size ("sm"|"md"|"lg").
     Eventi: action (click sul pulsante). UI: icona SVG o emoji, testo centrato e bottone primario. -->
<template>
  <div class="empty-state" :class="size">
    <div class="empty-icon" v-if="icon" :aria-hidden="true">{{ icon }}</div>
    <svg
      v-else
      class="empty-svg"
      :aria-hidden="true"
      viewBox="0 0 64 64"
      fill="none"
    >
      <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="2" />
      <path
        d="M20 32h24M32 20v24"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      />
    </svg>
    <p class="empty-title">{{ title }}</p>
    <p v-if="description" class="empty-desc">{{ description }}</p>
    <button
      v-if="actionLabel"
      class="btn btn-primary btn-sm"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
  icon?: string;
  actionLabel?: string;
  size?: "sm" | "md" | "lg";
}>();

defineEmits<{
  (e: "action"): void;
}>();
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}
.empty-state.sm {
  padding: 24px 16px;
}
.empty-state.lg {
  padding: 60px 30px;
}
.empty-icon {
  font-size: 3rem;
  margin-bottom: 12px;
}
.empty-svg {
  width: 64px;
  height: 64px;
  margin-bottom: 12px;
  opacity: 0.5;
}
.empty-title {
  font-size: 1.1rem;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.empty-desc {
  font-size: 0.9rem;
  max-width: 360px;
  margin: 0 auto 16px;
}
</style>
