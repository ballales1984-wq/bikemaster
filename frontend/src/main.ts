import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.ts'
import './index.css'
import { authToken } from './composables/useAuth.ts'

const urlParams = new URLSearchParams(window.location.search)
const token = urlParams.get('token')
const email = urlParams.get('email')
if (token) {
  localStorage.setItem('bikemaster_token', token)
  localStorage.setItem('bikemaster_user', JSON.stringify({ username: email || '', email, is_admin: false }))
  window.history.replaceState({}, document.title, '/')
}

createApp(App).use(router).mount('#app')
