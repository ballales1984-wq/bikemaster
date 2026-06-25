import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './index.css'
import { token, user } from './composables/useAuth'
import './composables/usePWA'
import { useToast } from './composables/useToast'

const urlParams = new URLSearchParams(window.location.search)
const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
const urlToken = urlParams.get('token') || hashParams.get('token')
const email = urlParams.get('email') || hashParams.get('email')
const oauthError = urlParams.get('oauth_error') || hashParams.get('oauth_error')
if (urlToken) {
  const userData = { username: email || '', email, is_admin: false }
  localStorage.setItem('bikemaster_token', urlToken)
  localStorage.setItem('bikemaster_user', JSON.stringify(userData))
  token.value = urlToken
  user.value = userData
  localStorage.removeItem('bikemaster_login_error')
  window.history.replaceState({}, document.title, '/')
} else if (oauthError) {
  token.value = ''
  user.value = null
  localStorage.setItem('bikemaster_login_error', oauthError)
  window.history.replaceState({}, document.title, '/')
}

createApp(App).use(createPinia()).use(router).mount('#app')
