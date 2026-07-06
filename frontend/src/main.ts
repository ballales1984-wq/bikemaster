import { createApp } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './index.css'
import { useAuthStore } from './stores/auth'
import './composables/usePWA'
import { useToast } from './composables/useToast'

const pinia = createPinia()
setActivePinia(pinia)

const app = createApp(App).use(pinia).use(router)

const auth = useAuthStore()

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
  navigator.serviceWorker.ready.then(reg => {
    if (reg.waiting) {
      reg.waiting.postMessage({ type: 'SKIP_WAITING' })
    }
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
  })
}

app.mount('#app')
