<template>
  <div class="app">
    <header class="app-header">
      <h1>🚴 BikeMaster</h1>
      <p>Cycling Performance Intelligence</p>
    </header>

    <template v-if="!loggedIn">
      <LoginForm @login="onLogin" @register="onRegister" @error="loginError = $event" />
      <p v-if="loginError" class="login-error">{{ loginError }}</p>
    </template>

    <template v-else>
      <HeaderTabs :is-admin="isAdmin" @logout="onLogout" />

      <StatsSummary :stats="summary" :loading="summaryLoading" @refresh="onSummaryChange" />

      <main>
        <ErrorBoundary>
          <router-view v-slot="{ Component, ComponentProps }">
            <transition name="panel" mode="out-in">
              <component :is="Component" v-bind="ComponentProps" @summary-change="onSummaryChange" />
            </transition>
          </router-view>
        </ErrorBoundary>
      </main>

      <ToastContainer />
      <PWAInstallPrompt />
    </template>

    <footer class="footer">BikeMaster v2 — Vue 3 Dashboard</footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isLoggedIn, isAdmin as checkIsAdmin, login as doLogin, register as doRegister, logout as doLogout } from './composables/useAuth'
import HeaderTabs from './components/HeaderTabs.vue'
import StatsSummary from './components/StatsSummary.vue'
import ToastContainer from './components/ToastContainer.vue'
import LoginForm from './components/LoginForm.vue'
import ErrorBoundary from './components/ErrorBoundary.vue'
import PWAInstallPrompt from './components/PWAInstallPrompt.vue'
import { useRides } from './composables/useRides'

const router = useRouter()
const loggedIn = computed(() => isLoggedIn())
const isAdmin = computed(() => checkIsAdmin())
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

function onLogout() {
  doLogout()
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
