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
  async function prompt() {
    const evt = deferredPrompt.value
    if (!evt) return
    evt.preventDefault()
    await evt.prompt()
    const { outcome } = await evt.userChoice
    if (outcome !== 'accepted') {
      deferredPrompt.value = null
      showPrompt.value = false
    }
    return outcome
  }
  return { showPrompt, deferredPrompt, prompt }
}
