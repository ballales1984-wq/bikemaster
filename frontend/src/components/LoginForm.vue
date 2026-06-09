<template>
  <div class="login-panel">
    <h2>🔐 Accesso BikeMaster</h2>
    <div class="login-tabs">
      <button :class="['tab-btn', { active: mode === 'login' }]" @click="mode = 'login'">Login</button>
      <button :class="['tab-btn', { active: mode === 'register' }]" @click="mode = 'register'">Registrati</button>
    </div>

    <form @submit.prevent="submit" class="login-form">
      <div class="form-group">
        <label for="username">Username</label>
        <input id="username" v-model="form.username" type="text" placeholder="min 3 caratteri" :disabled="loading" required />
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <input id="password" v-model="form.password" type="password" :placeholder="mode === 'register' ? 'min 6 caratteri' : ''" :disabled="loading" required />
      </div>
      <button type="submit" class="btn btn-primary" :disabled="loading">
        {{ loading ? 'Caricamento...' : (mode === 'login' ? 'Entra' : 'Crea account') }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['login', 'register', 'error'])

const mode = ref('login')
const loading = ref(false)
const form = ref({ username: '', password: '' })

async function submit() {
  loading.value = true
  try {
    emit(mode.value, { ...form.value })
  } catch (e) {
    emit('error', e.message)
  } finally {
    loading.value = false
  }
}
</script>
