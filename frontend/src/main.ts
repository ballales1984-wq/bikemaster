import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.ts'
import './index.css'
import { authToken } from './composables/useAuth.ts'

const urlParams = new URLSearchParams(window.location.search)
const token = urlParams.get('token')
const email = urlParams.get('email')
const oauthError = urlParams.get('oauth_error')
if (token) {
  localStorage.setItem('bikemaster_token', token)
  localStorage.setItem('bikemaster_user', JSON.stringify({ username: email || '', email, is_admin: false }))
  localStorage.removeItem('bikemaster_login_error')
  window.history.replaceState({}, document.title, '/')
} else if (oauthError) {
  localStorage.setItem('bikemaster_login_error', oauthError)
  window.history.replaceState({}, document.title, '/')
}

createApp(App).use(router).mount('#app')
