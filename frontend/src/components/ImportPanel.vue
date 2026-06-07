<template>
  <section>
    <div class="panel">
      <h2>📥 Importa Percorsi</h2>
      <div class="form-group">
        <label for="import-file">Carica file GPX o FIT</label>
        <div class="upload-area" @click="pickFile" @dragover.prevent @drop.prevent="onDrop">
          <input ref="fileInput" type="file" accept=".gpx,.fit" multiple @change="onChange" />
          <div class="upload-placeholder">{{ label }}</div>
        </div>
      </div>
      <div id="import-progress" v-if="status" class="result-box">{{ status }}</div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const emit = defineEmits(['summary-change'])
const fileInput = ref(null)
const files = ref([])
const status = ref('')
const uploading = ref(false)

const label = computed(() => {
  if (!files.value.length) return 'Trascina file qui o clicca per selezionare (GPX/FIT)'
  return `${files.value.length} file selezionati`
})

function pickFile() {
  fileInput.value?.click()
}

function onChange(e) {
  files.value = Array.from(e.target.files || [])
}

function onDrop(e) {
  files.value = Array.from(e.dataTransfer.files || [])
}

async function uploadOne(file) {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch('/api/v1/import/gpx', { method: 'POST', body: form })
  if (!resp.ok) throw new Error(`Upload ${file.name} failed`)
  return resp.json()
}

async function upload() {
  if (!files.value.length || uploading.value) return
  try {
    uploading.value = true
    status.value = 'Import in corso...'
    for (const f of files.value) {
      await uploadOne(f)
    }
    status.value = 'Import completato'
    files.value = []
    emit('summary-change')
  } catch (e) {
    status.value = 'Import fallito: ' + (e.message || e)
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  // offer manual upload via button in markdown if needed
})
</script>
