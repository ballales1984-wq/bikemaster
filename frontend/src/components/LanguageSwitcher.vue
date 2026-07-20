<!-- Selettore lingua: toggle IT/EN che cambia la locale corrente tramite il composable useI18n.
     Props: none. Events: none (uses setLocale from useI18n). UI: two buttons, the active one is highlighted; descriptive aria-label. -->
<template>
  <div class="lang-switcher">
    <button
      v-for="loc in locales"
      :key="loc.code"
      class="lang-btn"
      :class="{ active: locale === loc.code }"
      :aria-label="'Switch to ' + loc.label"
      @click="setLocale(loc.code)"
    >
      {{ loc.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "../composables/useI18n";

const { locale, setLocale } = useI18n();

const locales = [
  { code: "it", label: "IT" },
  { code: "en", label: "EN" },
];
</script>

<style scoped>
.lang-switcher {
  display: inline-flex;
  gap: 4px;
}
.lang-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.75rem;
  transition: var(--transition);
}
.lang-btn.active {
  border-color: var(--accent);
  color: var(--accent);
}
.lang-btn:hover {
  border-color: var(--accent);
}
</style>

