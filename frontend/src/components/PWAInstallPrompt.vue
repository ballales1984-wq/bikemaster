<!-- Banner installazione PWA: invita a installare l'app nella home screen per l'accesso offline.
     Props: nessuna. Eventi: nessuno (usa composable usePWA). Mostra il banner solo se è disponibile un evento beforeinstallprompt.
     UI: banner fisso con icona, testo, pulsanti "Install" e "chiudi" (dismiss); transizione slide; nasconde dopo installazione. -->
<template>
  <Transition name="slide">
    <div v-if="showBanner" class="pwa-banner" role="alert" aria-live="polite">
      <div
class="pwa-banner-icon" aria-hidden="true"></div>
      <div class="pwa-banner-text">
        <strong>Install BikeMaster</strong>
        <span>Add to home screen for offline access</span>
      </div>
      <button
        class="btn btn-primary btn-sm"
        aria-label="Install BikeMaster app"
        @click="install"
      >
        Install
      </button>
      <button
        class="pwa-banner-close"
        aria-label="Dismiss install prompt"
        @click="dismiss"
      >
        ×
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { usePWA } from "../composables/usePWA";
import { computed, onMounted, onBeforeUnmount } from "vue";

const { showPrompt, deferredPrompt, prompt } = usePWA();

const showBanner = computed(() => {
  if (!showPrompt.value) return false;
  if (!deferredPrompt.value) return false;
  return typeof deferredPrompt.value.prompt === "function";
});

async function install() {
  if (!showBanner.value) return;
  const outcome = await prompt();
  if (outcome === "accepted") {
    showPrompt.value = false;
  }
}

function dismiss() {
  showPrompt.value = false;
  deferredPrompt.value = null;
}

onMounted(() => {
  const handler = () => {
    showPrompt.value = false;
    deferredPrompt.value = null;
  };
  window.addEventListener("appinstalled", handler);
  onBeforeUnmount(() => {
    window.removeEventListener("appinstalled", handler);
  });
});
</script>

<style scoped>
.pwa-banner {
  position: fixed;
  bottom: env(safe-area-inset-bottom, 20px);
  left: 20px;
  right: 20px;
  max-width: 480px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: var(--shadow);
  z-index: 5000;
}

.pwa-banner-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.pwa-banner-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pwa-banner-text strong {
  font-size: 0.95rem;
}

.pwa-banner-text span {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.pwa-banner-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.3rem;
  cursor: pointer;
  padding: 4px 8px;
  line-height: 1;
}

.pwa-banner-close:hover {
  color: var(--text-primary);
}

.slide-enter-active,
.slide-leave-active {
  transition:
    transform 0.3s ease,
    opacity 0.3s ease;
}

.slide-enter-from {
  transform: translateY(120%);
  opacity: 0;
}

.slide-leave-to {
  transform: translateY(120%);
  opacity: 0;
}

@media (max-width: 480px) {
  .pwa-banner {
    left: 10px;
    right: 10px;
    bottom: 10px;
    flex-wrap: wrap;
  }
}
</style>
