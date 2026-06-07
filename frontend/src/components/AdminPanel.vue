<template>
  <div class="panel">
    <h2>⚙️ Amministrazione</h2>
    <div class="form-actions">
      <button class="btn btn-primary" @click="loadStats">📊 Statistiche</button>
      <button class="btn btn-secondary" @click="backupDb">💾 Backup DB</button>
      <button class="btn btn-secondary" @click="createIndexes">🗂️ Indici</button>
    </div>
    <div v-if="stats" class="result-box">{{ stats }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { apiPost } from '../utils/api.js'

const emit = defineEmits(['loading'])
const stats = ref('')

async function loadStats() {
  try {
    const data = await apiGet('/api/v1/admin/stats')
    stats.value = JSON.stringify(data, null, 2)
  } catch (e) {
    stats.value = 'Errore: ' + (e.message || e)
  }
}

async function backupDb() {
  try {
    await apiPost('/api/v1/admin/backup', {})
    stats.value = 'Backup completato'
  } catch (e) {
    stats.value = 'Errore: ' + (e.message || e)
  }
}

async function createIndexes() {
  try {
    await apiPost('/api/v1/admin/indexes', {})
    stats.value = 'Indici creati'
  } catch (e) {
    stats.value = 'Errore: ' + (e.message || e)
  }
}
</script>
