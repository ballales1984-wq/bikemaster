import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index.ts'
import './index.css'
import { authToken, authUser } from './composables/useAuth.ts'

const urlParams = new URLSearchParams(window.location.search)
const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
const token = urlParams.get('token') || hashParams.get('token')
const email = urlParams.get('email') || hashParams.get('email')
const oauthError = urlParams.get('oauth_error') || hashParams.get('oauth_error')
if (token) {
  const user = { username: email || '', email, is_admin: false }
  localStorage.setItem('bikemaster_token', token)
  localStorage.setItem('bikemaster_user', JSON.stringify(user))
  authToken.value = token
  authUser.value = user
  localStorage.removeItem('bikemaster_login_error')
  window.history.replaceState({}, document.title, '/')
} else if (oauthError) {
  authToken.value = ''
  authUser.value = null
  localStorage.setItem('bikemaster_login_error', oauthError)
  window.history.replaceState({}, document.title, '/')
}

createApp(App).use(createPinia()).use(router).mount('#app')
