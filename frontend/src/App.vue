<template>
  <div class="app">
    <header class="app-header">
      <h1>🚴 BikeMaster</h1>
      <p>Cycling Performance Intelligence</p>
    </header>

    <HeaderTabs v-model:active="activeTab" />

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

      <section v-if="activeTab === 'admin'">
        <AdminPanel />
      </section>
    </main>

    <ToastContainer />
    <footer class="footer">BikeMaster v2 — Vue 3 Dashboard</footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import HeaderTabs from './components/HeaderTabs.vue'
import StatsSummary from './components/StatsSummary.vue'
import RidesPanel from './components/RidesPanel.vue'
import ImportPanel from './components/ImportPanel.vue'
import AthletePanel from './components/AthletePanel.vue'
import CoachPanel from './components/CoachPanel.vue'
import KnowledgePanel from './components/KnowledgePanel.vue'
import AdminPanel from './components/AdminPanel.vue'
import ToastContainer from './components/ToastContainer.vue'

const activeTab = ref('rides')
const summary = ref({ rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0 })

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
