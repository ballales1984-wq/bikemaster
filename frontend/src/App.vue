<template>
  <div class="app" :class="{ 'light-theme': !isDark }">
    <header class="app-header" v-show="showHeader">
      <h1 class="logo">🚴 BikeMaster</h1>
      <p v-if="loggedIn" class="tagline">Cycling Performance Intelligence</p>
      <button class="theme-toggle" @click="toggleTheme" :aria-label="isDark ? 'Light mode' : 'Dark mode'">
        {{ isDark ? '☀️' : '🌙' }}
      </button>
      <nav v-if="isPublicPage" class="public-links">
        <router-link to="/about">Chi Siamo</router-link>
        <router-link to="/contact">Contatti</router-link>
        <router-link to="/privacy">Privacy</router-link>
        <router-link to="/terms">Termini</router-link>
        <router-link to="/cookies">Cookie</router-link>
      </nav>
    </header>

    <div v-if="oauthLoading" class="oauth-loading-overlay">
      <div class="spinner"></div>
      <p class="loading-text">Finalizing login...</p>
    </div>

    <template v-if="!loggedIn && !isPublicPage && !oauthLoading">
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
const auth = useAuthStore()
const loggedIn = computed(() => auth.isLoggedIn.value)
const isAdmin = computed(() => auth.isAdmin.value)
const isPublicPage = computed(() => ['/privacy', '/terms', '/cookies', '/about', '/contact'].includes(route.path))
const showHeader = computed(() => loggedIn.value || isPublicPage.value)
const summary = ref({ rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0 })
const summaryLoading = ref(false)
const loginError = ref(localStorage.getItem('bikemaster_login_error') || '')
const oauthLoading = ref(false)

const isDark = ref(true)

function loadTheme() {
  const saved = localStorage.getItem('bikemaster_theme')
  if (saved === 'light') {
    isDark.value = false
  } else {
    isDark.value = true
  }
}

function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem('bikemaster_theme', isDark.value ? 'dark' : 'light')
}

watch(isDark, (val) => {
  document.body.classList.toggle('light-theme', !val)
})

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
    await auth.login(creds.username, creds.password)
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
    await auth.register(creds.username, creds.password)
    await auth.login(creds.username, creds.password)
    await loadSummary()
  } catch (e) {
    loginError.value = e.message
  }
}

async function onLogout() {
  await auth.logout()
    .catch(() => {})
  router.push('/')
  summary.value = { rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0 }
}

async function onSummaryChange() {
  await loadSummary()
}

onMounted(() => {
  loadTheme()
  const urlParams = new URLSearchParams(window.location.search)
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  if (urlParams.get('token') || hashParams.get('token')) {
    oauthLoading.value = true
  }
  window.addEventListener('oauth-loading-end', () => {
    oauthLoading.value = false
  })
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
.logo {
  font-size: 1.8rem;
  margin: 0 0 0.3rem;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: logoGlow 3s ease-in-out infinite alternate;
  will-change: filter;
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

.theme-toggle {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition);
  flex-shrink: 0;
}

.theme-toggle:hover {
  border-color: var(--accent);
  box-shadow: 0 0 12px rgba(0, 255, 204, 0.2);
}
.oauth-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading-text {
  margin-top: 16px;
  color: var(--text-primary);
}
</style>
