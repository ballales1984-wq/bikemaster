<template>
  <section>
    <div class="panel">
      <h2>📥 Importa Percorsi</h2>
      <div class="form-group">
         <label for="import-file">Carica file GPX o FIT</label>
        <div class="upload-area" @click="pickFile" @dragover.prevent @drop.prevent="onDrop">
          <input id="import-file" ref="fileInput" type="file" accept=".gpx,.fit" multiple @change="onChange" />
          <div class="upload-placeholder">{{ label }}</div>
        </div>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" @click="upload" :disabled="!files.length || uploading">
          {{ uploading ? 'Importazione in corso...' : 'Importa file selezionati' }}
        </button>
      </div>
      <div v-if="uploading || uploadProgress > 0" class="progress-track" aria-label="Avanzamento importazione">
        <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
      <div id="import-progress" v-if="status" class="result-box">{{ status }}</div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiUpload } from '../utils/api.ts'

const emit = defineEmits(['summary-change'])
const fileInput = ref(null)
const files = ref([])
const status = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)

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
  const ext = file.name.toLowerCase().split('.').pop()
  const path = ext === 'fit' || ext === 'fitf' ? '/api/v1/import/fit' : '/api/v1/import/gpx'
  return apiUpload(path, file)
}

async function upload() {
  if (!files.value.length || uploading.value) return
  try {
    uploading.value = true
    uploadProgress.value = 0
    status.value = 'Import in corso...'
    for (let i = 0; i < files.value.length; i += 1) {
      await uploadOne(files.value[i])
      uploadProgress.value = Math.round(((i + 1) / files.value.length) * 100)
      status.value = `Importati ${i + 1} di ${files.value.length} file`
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
