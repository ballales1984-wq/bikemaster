<template>
  <div class="panel">
    <h2>📚 Knowledge Base</h2>
    <div class="form-grid">
      <div class="form-group"><label for="kb-query">Cerca argomento</label><input type="text" v-model="query" /></div>
      <button class="btn btn-primary" @click="search">Cerca</button>
      <button class="btn btn-secondary" @click="listTopics">Lista Argomenti</button>
    </div>
    <div v-if="result" class="result-box">{{ result }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { apiPost } from '../utils/api.js'

const query = ref('')
const result = ref('')

async function search() {
  try {
    const data = await apiPost('/api/v1/knowledge/query', { query: query.value })
    result.value = JSON.stringify(data, null, 2)
  } catch (e) {
    result.value = 'Errore: ' + (e.message || e)
  }
}

async function listTopics() {
  try {
    const data = await apiGet('/api/v1/knowledge')
    result.value = JSON.stringify(data, null, 2)
  } catch (e) {
    result.value = 'Errore: ' + (e.message || e)
  }
}
</script>
