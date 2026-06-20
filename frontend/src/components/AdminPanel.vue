<template>
  <div class="panel">
    <h2>⚙️ Amministrazione</h2>
    <div class="form-actions">
      <button class="btn btn-primary" @click="loadStats">📊 Statistiche</button>
      <a class="btn btn-secondary" href="/api/v1/admin/backup" download>💾 Backup DB</a>
      <button class="btn btn-secondary" @click="createIndexes">🗂️ Indici</button>
    </div>
    <div v-if="stats" class="result-box">{{ stats }}</div>
    <div v-if="error" class="error-box">⛔ {{ error }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { apiGet, apiPost } from '../utils/api'

const stats = ref('')
const error = ref('')

async function loadStats() {
  try {
    error.value = ''
    const data = await apiGet('/api/v1/admin/stats')
    stats.value = JSON.stringify(data, null, 2)
  } catch (e) {
    error.value = 'Accesso negato: ' + (e.message || e)
  }
}

async function createIndexes() {
  try {
    error.value = ''
    await apiPost('/api/v1/admin/indexes', {})
    stats.value = 'Indici creati'
  } catch (e) {
    error.value = 'Accesso negato: ' + (e.message || e)
  }
}
</script>
