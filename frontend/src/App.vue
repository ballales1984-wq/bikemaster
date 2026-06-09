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
      <HeaderTabs v-model:active="activeTab" :is-admin="isAdmin" @logout="onLogout" />

      <StatsSummary :stats="summary" />

      <main>
        <section v-if="activeTab === 'rides'">
          <RidesPanel @summary-change="onSummaryChange" />
        </section>

        <section v-if="activeTab === 'import'">
          <ImportPanel @summary-change="onSummaryChange" />
        </section>

        <section v-if="activeTab === 'athlete'">
          <AthletePanel />
        </section>

        <section v-if="activeTab === 'coach'">
          <CoachPanel />
        </section>

        <section v-if="activeTab === 'knowledge'">
          <KnowledgePanel />
        </section>

        <section v-if="activeTab === 'calendar'">
          <CalendarPanel />
        </section>

        <section v-if="activeTab === 'granfondo'">
          <GranfondoPlanner />
        </section>

        <section v-if="activeTab === 'heatmap'">
          <HeatmapPanel />
        </section>

        <section v-if="activeTab === 'badges'">
          <BadgesPanel />
        </section>

        <section v-if="activeTab === 'admin' && isAdmin">
          <AdminPanel />
        </section>

        <section v-if="activeTab === 'admin' && !isAdmin">
          <div class="panel access-denied">
            <h2>⛔ Accesso Negato</h2>
            <p>Non hai i permessi per accedere alla sezione amministrazione.</p>
          </div>
        </section>
      </main>

      <ToastContainer />
    </template>

    <footer class="footer">BikeMaster v2 — Vue 3 Dashboard</footer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { isLoggedIn, isAdmin as checkIsAdmin, login as doLogin, register as doRegister, logout as doLogout } from './composables/useAuth.js'
import HeaderTabs from './components/HeaderTabs.vue'
import StatsSummary from './components/StatsSummary.vue'
import RidesPanel from './components/RidesPanel.vue'
import ImportPanel from './components/ImportPanel.vue'
import AthletePanel from './components/AthletePanel.vue'
import CoachPanel from './components/CoachPanel.vue'
import KnowledgePanel from './components/KnowledgePanel.vue'
import CalendarPanel from './components/CalendarPanel.vue'
import GranfondoPlanner from './components/GranfondoPlanner.vue'
import HeatmapPanel from './components/HeatmapPanel.vue'
import BadgesPanel from './components/BadgesPanel.vue'
import AdminPanel from './components/AdminPanel.vue'
import ToastContainer from './components/ToastContainer.vue'
import LoginForm from './components/LoginForm.vue'

const loggedIn = computed(() => isLoggedIn())
const isAdmin = computed(() => checkIsAdmin())
const activeTab = ref('rides')
const summary = ref({ rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0 })
const loginError = ref('')

async function onLogin(creds) {
  try {
    await doLogin(creds.username, creds.password)
    loginError.value = ''
    activeTab.value = 'rides'
  } catch (e) {
    loginError.value = e.message
  }
}

async function onRegister(creds) {
  try {
    await doRegister(creds.username, creds.password)
    await doLogin(creds.username, creds.password)
    loginError.value = ''
  } catch (e) {
    loginError.value = e.message
  }
}

function onLogout() {
  doLogout()
  activeTab.value = 'rides'
}

async function onSummaryChange() {
  try {
    const mod = await import('./composables/useRides.js')
    const fn = mod.useRides()
    const data = await fn.fetchSummary()
    summary.value = { rides: data.rides ?? 0, distance_km: data.distance_km ?? 0, calories: data.calories ?? 0, avg_speed_kmh: data.avg_speed_kmh ?? 0, duration_minutes: data.duration_minutes ?? 0 }
  } catch (e) {
    console.error('summary refresh failed', e)
  }
}
</script>
