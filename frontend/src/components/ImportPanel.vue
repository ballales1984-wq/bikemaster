<template>
  <section>
    <div class="panel">
      <h2>📥 Import Routes</h2>

      <div class="form-group">
        <label for="import-file">Upload GPX or FIT file</label>
        <div class="upload-area" @click="pickFile" @touchstart="pickFile" @dragover.prevent @drop.prevent="onDrop">
          <input id="import-file" ref="fileInput" type="file" accept=".gpx,.fit" multiple @change="onChange" />
          <div class="upload-placeholder">{{ label }}</div>
        </div>
      </div>

      <div v-if="importStatus?.message" class="result-box" :class="importStatus.success ? 'success' : 'error'">
        {{ importStatus.message }}
      </div>
      <div class="form-actions">
<button class="btn btn-primary" @click="upload" @touchstart="upload" :disabled="!files.length || uploading">
           {{ uploading ? 'Importing...' : 'Import selected files' }}
         </button>
      </div>

<div class="oauth-separator">
         <span>or</span>
       </div>

       <button @click="connectGoogleFit" @touchstart="connectGoogleFit" class="btn btn-google-fit" :disabled="importing" type="button">
         <svg viewBox="0 0 24 24" width="18" height="18" style="margin-right: 6px;">
           <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.76h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
           <path fill="#34A853" d="M12 23c3.05 0 5.84-1.15 7.86-3l-3.57-2.76c-.98.66-2.23 1.06-3.62 1.44v2.26C15.24 21.23 13.71 22 12 22z"/>
           <path fill="#FBBC05" d="M6.27 15.73a7.5 7.5 0 0 1 0-3.46l2.93-2.27a7.5 7.5 0 0 0 1.74 3.19l-2.93 2.27z"/>
           <path fill="#EA4335" d="M18.57 6.43a7.5 7.5 0 0 0-6.57-4.43 7.5 7.5 0 0 0-1.57.23l2.93 2.26a4.99 4.99 0 0 1 5.17 4.17z"/>
         </svg>
         {{ importing ? 'Connecting...' : 'Import from Google Fit' }}
       </button>

<<<<<<< Updated upstream
       <div v-if="uploading || uploadProgress > 0" class="progress-track" aria-label="Import progress">
=======
      <button @click="connectGoogleHealth" class="btn btn-google-fit" :disabled="importing" type="button">
        <svg viewBox="0 0 24 24" width="18" height="18" style="margin-right: 6px;">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.76h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c3.05 0 5.84-1.15 7.86-3l-3.57-2.76c-.98.66-2.23 1.06-3.62 1.44v2.26C15.24 21.23 13.71 22 12 22z"/>
          <path fill="#FBBC05" d="M6.27 15.73a7.5 7.5 0 0 1 0-3.46l2.93-2.27a7.5 7.5 0 0 0 1.74 3.19l-2.93 2.27z"/>
          <path fill="#EA4335" d="M18.57 6.43a7.5 7.5 0 0 0-6.57-4.43 7.5 7.5 0 0 0-1.57.23l2.93 2.26a4.99 4.99 0 0 1 5.17 4.17z"/>
        </svg>
        {{ importing ? 'Connessione...' : 'Importa da Google Health' }}
      </button>

      <div v-if="uploading || uploadProgress > 0" class="progress-track" aria-label="Avanzamento importazione">
>>>>>>> Stashed changes
        <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
      <div id="import-progress" v-if="status" class="result-box">{{ status }}</div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiUpload, apiPost } from '../utils/api'

const emit = defineEmits(['summary-change'])
const fileInput = ref(null)
const files = ref([])
const status = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)
const importing = ref(false)
const importStatus = ref(null)

const label = computed(() => {
  if (!files.value.length) return 'Drag files here or click to select (GPX/FIT)'
  return `${files.value.length} files selected`
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
status.value = 'Import in progress...'
      for (let i = 0; i < files.value.length; i += 1) {
        await uploadOne(files.value[i])
        uploadProgress.value = Math.round(((i + 1) / files.value.length) * 100)
        status.value = `Imported ${i + 1} of ${files.value.length} files`
      }
      status.value = 'Import completed'
    files.value = []
    emit('summary-change')
  } catch (e) {
    status.value = 'Import failed: ' + (e.message || e)
  } finally {
    uploading.value = false
  }
}

async function connectGoogleFit() {
  importing.value = true
  importStatus.value = null
  try {
    // Get Google Fit auth URL
    const redirectUri = `${import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin}/api/v1/import/google-fit/callback`
    const state = btoa(JSON.stringify({ redirect_uri: redirectUri }))
    const authResp = await fetch(`/api/v1/import/google-fit/auth?redirect_uri=${encodeURIComponent(redirectUri)}&state=${encodeURIComponent(state)}`)
if (!authResp.ok) {
        throw new Error('Unable to start Google Fit authentication')
      }
    const { auth_url } = await authResp.json()

    // Open popup for Google Fit OAuth
    const popup = window.open(auth_url, 'google-fit-auth', 'width=500,height=600')
if (!popup) {
        throw new Error('Popup blocked - enable popups')
      }

    // Listen for callback
    const handleMessage = async (event) => {
      if (event.data?.type === 'google-fit-error') {
        window.removeEventListener('message', handleMessage)
        importStatus.value = {
          success: false,
          message: event.data.error_description || event.data.error || 'Google Fit error'
        }
        importing.value = false
        return
      }

      if (event.data?.type === 'google-fit-success') {
        window.removeEventListener('message', handleMessage)
        // Import activities
        const token = localStorage.getItem('bikemaster_token')
        const importResp = await fetch('/api/v1/import/google-fit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          },
          body: JSON.stringify({ access_token: event.data.token })
        })
        if (importResp.ok) {
          const result = await importResp.json()
          importStatus.value = { success: true, message: `Imported ${result.count} routes from Google Fit` }
          emit('summary-change')
        } else {
          importStatus.value = { success: false, message: 'Google Fit import error' }
        }
        importing.value = false
      }
    }
    window.addEventListener('message', handleMessage)
  } catch (e) {
    importStatus.value = { success: false, message: e.message }
    importing.value = false
  }
}

async function connectGoogleHealth() {
  importing.value = true
  importStatus.value = null
  try {
    const redirectUri = `${window.location.origin}/api/v1/import/google-health/callback`
    const state = btoa(JSON.stringify({ redirect_uri: redirectUri }))
    const authResp = await fetch(`/api/v1/import/google-health/auth?redirect_uri=${encodeURIComponent(redirectUri)}&state=${encodeURIComponent(state)}`)
    if (!authResp.ok) {
      throw new Error('Impossibile iniziare autenticazione Google Health')
    }
    const { auth_url } = await authResp.json()

    const popup = window.open(auth_url, 'google-health-auth', 'width=500,height=600')
    if (!popup) {
      throw new Error('Popup bloccato - abilita i popup')
    }

    const handleMessage = async (event) => {
      if (event.data?.type === 'google-health-error') {
        window.removeEventListener('message', handleMessage)
        importStatus.value = {
          success: false,
          message: event.data.error_description || event.data.error || 'Errore Google Health'
        }
        importing.value = false
        return
      }

      if (event.data?.type === 'google-health-success') {
        window.removeEventListener('message', handleMessage)
        const importResp = await fetch('/api/v1/import/google-health', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access_token: event.data.token })
        })
        if (importResp.ok) {
          const result = await importResp.json()
          importStatus.value = { success: true, message: `Importati ${result.count} percorsi da Google Health` }
          emit('summary-change')
        } else {
          importStatus.value = { success: false, message: 'Errore importazione Google Health' }
        }
        importing.value = false
      }
    }
    window.addEventListener('message', handleMessage)
  } catch (e) {
    importStatus.value = { success: false, message: e.message }
    importing.value = false
  }
}

onMounted(() => {
  // offer manual upload via button in markdown if needed
})
</script>

<style scoped>
.panel {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.upload-area {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  background: var(--bg-tertiary);
  transition: all 0.2s;
}

.upload-area:hover {
  background: var(--border);
}

.upload-placeholder {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.form-actions {
  margin: 12px 0;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent);
  color: var(--bg-primary);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-google-fit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 10px 16px;
  background: #fff;
  color: #444;
  border: 1px solid #dadce0;
  margin-top: 12px;
}

.btn-google-fit:hover:not(:disabled) {
  background: #f8f9fa;
}

.progress-track {
  width: 100%;
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  margin-top: 16px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s;
}

.result-box {
  margin-top: 12px;
  padding: 12px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

.result-box.success {
  background: rgba(66, 183, 77, 0.1);
  border: 1px solid var(--success);
  color: var(--success);
}

.result-box.error {
  background: rgba(234, 67, 53, 0.1);
  border: 1px solid var(--error);
  color: var(--error);
}

.oauth-separator {
  display: flex;
  align-items: center;
  margin: 20px 0;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.oauth-separator span {
  padding: 0 12px;
}

.oauth-separator::before,
.oauth-separator::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}
</style>
