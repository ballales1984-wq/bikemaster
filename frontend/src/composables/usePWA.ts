import { ref, onBeforeUnmount } from 'vue'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => void
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

declare global {
  interface Window {
    __pwaInstallPrompt?: BeforeInstallPromptEvent
  }
}

const showPrompt = ref(false)
const deferredPrompt = ref<BeforeInstallPromptEvent | null>(null)

function isPromptValid(evt: BeforeInstallPromptEvent | null | undefined): boolean {
  if (!evt) return false
  return typeof evt.prompt === 'function'
}

if (typeof window !== 'undefined') {
  if (window.__pwaInstallPrompt && isPromptValid(window.__pwaInstallPrompt)) {
    deferredPrompt.value = window.__pwaInstallPrompt
    showPrompt.value = true
  }
  window.addEventListener('beforeinstallprompt', (e: Event) => {
    const evt = e as BeforeInstallPromptEvent
    if (!isPromptValid(evt)) return
    e.preventDefault()
    deferredPrompt.value = evt
    showPrompt.value = true
  })
}

export function usePWA() {
  async function prompt() {
    const evt = deferredPrompt.value
    if (!evt || !isPromptValid(evt)) return
    try {
      await evt.prompt()
      const { outcome } = await evt.userChoice
      if (outcome !== 'accepted') {
        deferredPrompt.value = null
        showPrompt.value = false
      }
      return outcome
    } catch {
      deferredPrompt.value = null
      showPrompt.value = false
      return 'dismissed'
    }
  }

  onBeforeUnmount(() => {
    deferredPrompt.value = null
    showPrompt.value = false
  })

  return { showPrompt, deferredPrompt, prompt }
}
