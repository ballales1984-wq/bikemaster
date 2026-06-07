<script setup>
import { ref } from 'vue'

const activeTab = ref('rides')
const summary = ref({ rides: 0, distance_km: 0, calories: 0, avg_speed_kmh: 0, duration_minutes: 0 })
const adminStats = ref(null)

function setActiveTab(tab) {
  activeTab.value = tab
}

function updateSummary(s) {
  summary.value = s
}

function updateAdminStats(stats) {
  adminStats.value = stats
}
</script>

<template>
  <div class="app">
    <header class="app-header">
      <h1>🚴 BikeMaster</h1>
      <p>Cycling Performance Intelligence</p>
    </header>

    <nav class="tabs" aria-label="Navigazione principale">
      <button class="tab" :class="{ active: activeTab === 'rides' }" @click="setActiveTab('rides')">🏍️ Rides</button>
      <button class="tab" :class="{ active: activeTab === 'import' }" @click="setActiveTab('import')">📥 Import</button>
      <button class="tab" :class="{ active: activeTab === 'athlete' }" @click="setActiveTab('athlete')">🏃 Atleta</button>
      <button class="tab" :class="{ active: activeTab === 'coach' }" @click="setActiveTab('coach')">🧠 AI Coach</button>
      <button class="tab" :class="{ active: activeTab === 'knowledge' }" @click="setActiveTab('knowledge')">📚 Knowledge</button>
      <button class="tab" :class="{ active: activeTab === 'admin' }" @click="setActiveTab('admin')">⚙️ Admin</button>
    </nav>

    <StatsSummary :stats="summary" />

    <main>
      <section v-if="activeTab === 'rides'">
        <RidesPanel @summary-change="updateSummary" />
      </section>
      <section v-if="activeTab === 'import'">
        <ImportPanel @summary-change="updateSummary" />
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
        <AdminPanel @admin-stats="updateAdminStats" />
      </section>
    </main>

    <ToastContainer />
    <footer class="footer">BikeMaster v2 — Vue 3 Dashboard</footer>
  </div>
</template>
