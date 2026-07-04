import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './index.css'
import { useAuthStore } from './stores/auth'
import './composables/usePWA'
import { useToast } from './composables/useToast'

const pinia = createPinia()

const urlParams = new URLSearchParams(window.location.search)
const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
const urlToken = urlParams.get('token') || hashParams.get('token')
const email = urlParams.get('email') || hashParams.get('email')
const oauthError = urlParams.get('oauth_error') || hashParams.get('oauth_error')

const app = createApp(App).use(pinia).use(router)

const auth = useAuthStore()

if (urlToken) {
  const userData = { username: email || '', email, is_admin: false }
  localStorage.setItem('bikemaster_token', urlToken)
  localStorage.setItem('bikemaster_user', JSON.stringify(userData))
  auth.token.value = urlToken
  auth.user.value = userData
  localStorage.removeItem('bikemaster_login_error')
  window.history.replaceState({}, document.title, '/')
} else if (oauthError) {
  auth.token.value = ''
  auth.user.value = null
  localStorage.setItem('bikemaster_login_error', oauthError)
  window.history.replaceState({}, document.title, '/')
}

app.mount('#app')
