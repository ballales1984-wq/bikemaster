import { createApp } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './index.css'
import { useAuthStore } from './stores/auth'
import { useUIStore } from './stores/ui'
import './composables/usePWA'
import { useToast } from './composables/useToast'
import { processOAuthToken } from './services/oauth'
import { syncAuthState } from './services/authSync'

const pinia = createPinia()
setActivePinia(pinia)

const app = createApp(App).use(pinia).use(router)

const auth = useAuthStore()
const ui = useUIStore()

processOAuthToken()
syncAuthState()

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js', { scope: '/' }).then(reg => {
    reg.addEventListener('updatefound', () => {
      const newWorker = reg.installing
      if (newWorker) {
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            window.location.reload()
          }
        })
      }
    })
    if (reg.waiting) {
      reg.waiting.postMessage({ type: 'SKIP_WAITING' })
    }
  }).catch(() => {})
}

app.mount('#app')
