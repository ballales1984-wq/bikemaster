<template>
  <div class="app">
    <header class="app-header" :class="{ 'header-login': !loggedIn && route.path === '/', 'header-app': loggedIn }">
      <h1 class="logo">🚴 BikeMaster</h1>
      <p v-if="loggedIn" class="tagline">Cycling Performance Intelligence</p>
      <nav v-if="!loggedIn || isPublicPage" class="public-links">
        <router-link to="/about">Chi Siamo</router-link>
        <router-link to="/contact">Contatti</router-link>
        <router-link to="/privacy">Privacy</router-link>
        <router-link to="/terms">Termini</router-link>
        <router-link to="/cookies">Cookie</router-link>
      </nav>
    </header>

    <template v-if="!loggedIn && !isPublicPage">
      <div class="login-wrapper">
        <LoginForm @login="onLogin" @register="onRegister" @error="loginError = $event" />
        <p v-if="loginError" class="login-error">{{ loginError }}</p>
      </div>
    </template>

    <template v-else>
      <HeaderTabs :is-admin="isAdmin" @logout="onLogout" />

      <StatsSummary v-if="loggedIn" :stats="summary" :loading="summaryLoading" @refresh="onSummaryChange" />

      <main>
        <router-view v-slot="{ Component, ComponentProps }">
          <transition name="panel" mode="out-in">
            <component :is="Component" v-bind="ComponentProps" @summary-change="onSummaryChange" />
          </transition>
        </router-view>
      </main>

      <ToastContainer />
      <PWAInstallPrompt />
    </template>

    <footer class="footer">BikeMaster v2 — Cycling Performance Intelligence</footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import { isLoggedIn, isAdmin as checkIsAdmin, login as doLogin, register as doRegister, logout as doLogout } from './composables/useAuth'
import HeaderTabs from './components/HeaderTabs.vue'
import StatsSummary from './components/StatsSummary.vue'
import ToastContainer from './components/ToastContainer.vue'
import LoginForm from './components/LoginForm.vue'
import PWAInstallPrompt from './components/PWAInstallPrompt.vue'
import { useRides } from './composables/useRides'

const route = useRoute()
const router = useRouter()
const loggedIn = computed(() => isLoggedIn())
const isAdmin = computed(() => checkIsAdmin())
const isPublicPage = computed(() => ['/privacy', '/terms', '/cookies', '/about', '/contact'].includes(route.path))
const summary = ref({ rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0 })
const summaryLoading = ref(false)
const loginError = ref(localStorage.getItem('bikemaster_login_error') || '')

const { fetchSummary } = useRides()

async function loadSummary() {
  summaryLoading.value = true
  try {
    const data = await fetchSummary()
    summary.value = { rides: data.rides ?? 0, distance_km: data.distance_km ?? 0, calories: data.calories ?? 0, avg_speed_kmh: data.avg_speed_kmh ?? 0, duration_minutes: data.duration_minutes ?? 0 }
  } finally {
    summaryLoading.value = false
  }
}

async function onLogin(creds) {
  try {
    loginError.value = ''
    localStorage.removeItem('bikemaster_login_error')
    await doLogin(creds.username, creds.password)
    router.push('/rides')
    await loadSummary()
  } catch (e) {
    loginError.value = e.message
  }
}

async function onRegister(creds) {
  try {
    loginError.value = ''
    localStorage.removeItem('bikemaster_login_error')
    await doRegister(creds.username, creds.password)
    await doLogin(creds.username, creds.password)
    await loadSummary()
  } catch (e) {
    loginError.value = e.message
  }
}

async function onLogout() {
  await doLogout()
    .catch(() => {})
  router.push('/')
  summary.value = { rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0 }
}

async function onSummaryChange() {
  await loadSummary()
}

onMounted(() => {
  if (loggedIn.value) loadSummary()
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-header {
  text-align: center;
  padding: 1.5rem 1rem;
  border-bottom: 1px solid var(--border);
  transition: var(--transition);
}
.app-header.header-login {
  padding: 2.5rem 1rem 1.5rem;
  border-bottom: none;
}
.app-header.header-app {
  padding: 1rem;
}
.logo {
  font-size: 1.8rem;
  margin: 0 0 0.3rem;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: logoGlow 3s ease-in-out infinite alternate;
}
@keyframes logoGlow {
  from { filter: brightness(1); }
  to { filter: brightness(1.2) drop-shadow(0 0 8px rgba(0, 255, 204, 0.4)); }
}
.tagline {
  color: var(--text-muted);
  margin: 0;
  font-size: 0.9rem;
}
.public-links {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 0.8rem;
}
.public-links a {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.85rem;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  transition: color 0.2s;
}
.public-links a:hover {
  color: var(--accent);
}
.login-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
}
.footer {
  margin-top: auto;
  text-align: center;
  padding: 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.85rem;
  color: var(--text-muted);
}
.login-error {
  color: var(--error);
  text-align: center;
  margin-top: 0.5rem;
}
</style>
