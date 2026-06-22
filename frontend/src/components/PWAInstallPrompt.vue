<template>
  <Transition name="slide">
    <div v-if="show" class="pwa-banner" role="alert" aria-live="polite">
      <div class="pwa-banner-icon" aria-hidden="true">🚴</div>
      <div class="pwa-banner-text">
        <strong>Install BikeMaster</strong>
        <span>Add to home screen for offline access</span>
      </div>
      <button class="btn btn-primary btn-sm" @click="install" aria-label="Install BikeMaster app">Install</button>
      <button class="pwa-banner-close" @click="dismiss" aria-label="Dismiss install prompt">×</button>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const show = ref(false)
const deferredPrompt = ref(null)

function beforeInstallPrompt(event) {
  event.preventDefault()
  deferredPrompt.value = event
  show.value = true
}

onMounted(() => {
  window.addEventListener('beforeinstallprompt', beforeInstallPrompt)
})

async function install() {
  if (!deferredPrompt.value) return
  deferredPrompt.value.prompt()
  const { outcome } = await deferredPrompt.value.userChoice
  if (outcome === 'accepted') {
    show.value = false
  }
  deferredPrompt.value = null
}

function dismiss() {
  show.value = false
}
</script>

<style scoped>
.pwa-banner {
  position: fixed;
  bottom: 20px;
  left: 20px;
  right: 20px;
  max-width: 480px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
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
  transition: transform 0.3s ease, opacity 0.3s ease;
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
