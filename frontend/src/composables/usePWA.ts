import { ref } from 'vue'

const showPrompt = ref(false)
const deferredPrompt = ref<BeforeInstallPromptEvent | null>(null)

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (e: Event) => {
    e.preventDefault()
    deferredPrompt.value = e as BeforeInstallPromptEvent
    showPrompt.value = true
  })
}

export function usePWA() {
  function prompt() {
    return deferredPrompt.value?.prompt()
  }
  return { showPrompt, deferredPrompt, prompt }
}
