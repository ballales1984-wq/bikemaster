import { createApp } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './index.css'
import { useAuthStore } from './stores/auth'
import { useUIStore } from './stores/ui'
import './composables/usePWA'
import { useToast } from './composables/useToast'

const pinia = createPinia()
setActivePinia(pinia)

const app = createApp(App).use(pinia).use(router)

const auth = useAuthStore()
const ui = useUIStore()

const urlParams = new URLSearchParams(window.location.search)
const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
const urlToken = urlParams.get('token') || hashParams.get('token')
const email = urlParams.get('email') || hashParams.get('email') || ''
const oauthError = urlParams.get('oauth_error') || hashParams.get('oauth_error')

if (urlToken) {
  auth.setAuthFromUrl(urlToken, email)
  window.history.replaceState({}, document.title, '/')
} else if (oauthError) {
  auth.setOauthError(oauthError)
  window.history.replaceState({}, document.title, '/')
}

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
