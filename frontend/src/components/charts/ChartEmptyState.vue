<!-- ChartEmptyState: stato vuoto sostitutivo per grafici senza dati.
     Props: title, description, actionLabel, onAction.
     UI: card centrata con icona, testo e azione opzionale. -->
<template>
  <div class="chart-empty">
    <div class="chart-empty__icon" aria-hidden="true"></div>
    <p class="chart-empty__title">{{ title }}</p>
    <p v-if="description" class="chart-empty__desc">{{ description }}</p>
    <button
      v-if="actionLabel && onAction"
      class="chart-empty__action"
      @click="onAction"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}>();
</script>

<style scoped>
.chart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
  border: 1px dashed var(--border);
  border-radius: var(--radius, 12px);
  background: var(--bg-tertiary, rgba(255, 255, 255, 0.02));
}
.chart-empty__icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--border);
  opacity: 0.6;
}
.chart-empty__title {
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}
.chart-empty__desc {
  font-size: 0.85rem;
  margin: 0;
  max-width: 260px;
}
.chart-empty__action {
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s;
}
.chart-empty__action:hover {
  border-color: var(--accent);
  background: var(--border);
}
</style>
