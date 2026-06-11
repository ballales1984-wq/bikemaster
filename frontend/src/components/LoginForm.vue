<template>
  <div class="login-panel">
    <h2>🔐 Accesso BikeMaster</h2>
    <div class="login-tabs">
      <button :class="['tab-btn', { active: mode === 'login' }]" @click="mode = 'login'">Login</button>
      <button :class="['tab-btn', { active: mode === 'register' }]" @click="mode = 'register'">Registrati</button>
    </div>

    <form @submit.prevent="submit" class="login-form" novalidate>
      <div class="form-group">
        <label for="username">Username</label>
        <input id="username" v-model="form.username" type="text" placeholder="min 3 caratteri" :disabled="loading" required autocomplete="username" :class="{ error: usernameError, valid: form.username.length >= 3 && !usernameError }" />
        <span v-if="usernameError" class="field-error">{{ usernameError }}</span>
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <div class="password-wrapper">
          <input id="password" v-model="form.password" :type="showPassword ? 'text' : 'password'" :placeholder="mode === 'register' ? 'min 6 caratteri' : ''" :disabled="loading" required autocomplete="current-password" :class="{ error: passwordError, valid: form.password.length >= 6 && !passwordError }" />
          <button type="button" class="password-toggle" @click="showPassword = !showPassword" :aria-label="showPassword ? 'Nascondi password' : 'Mostra password'">
            {{ showPassword ? '🙈' : '👁️' }}
          </button>
        </div>
        <span v-if="passwordError" class="field-error">{{ passwordError }}</span>
      </div>
      <button type="submit" class="btn btn-primary" :disabled="loading || !isFormValid">
        {{ loading ? '🔄 Caricamento...' : (mode === 'login' ? 'Entra' : 'Crea account') }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const emit = defineEmits(['login', 'register', 'error'])

const mode = ref('login')
const loading = ref(false)
const showPassword = ref(false)
const form = ref({ username: '', password: '' })
const usernameError = ref('')
const passwordError = ref('')

const isFormValid = computed(() => {
  const userOk = form.value.username.length >= 3
  const passOk = mode.value === 'register' ? form.value.password.length >= 6 : form.value.password.length > 0
  return userOk && passOk && !usernameError.value && !passwordError.value
})

function validate() {
  usernameError.value = ''
  passwordError.value = ''
  if (form.value.username.length > 0 && form.value.username.length < 3) {
    usernameError.value = 'Minimo 3 caratteri'
  }
  if (mode.value === 'register' && form.value.password.length > 0 && form.value.password.length < 6) {
    passwordError.value = 'Minimo 6 caratteri'
  }
}

async function submit() {
  validate()
  if (!isFormValid.value) return
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

<style scoped>
.login-panel {
  max-width: 420px;
  margin: 40px auto;
  background: var(--bg-secondary);
  padding: 32px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}

.login-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 24px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border);
}

.tab-btn {
  flex: 1;
  padding: 10px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: none;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.2s;
}

.tab-btn.active {
  background: var(--accent);
  color: var(--bg-primary);
  font-weight: bold;
}

.tab-btn:hover:not(.active) {
  background: var(--border);
  color: var(--text-primary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.login-error {
  color: var(--error);
  text-align: center;
  font-size: 0.9rem;
  margin-top: 8px;
}

.password-wrapper {
  position: relative;
}

.password-wrapper input {
  padding-right: 44px;
}

.password-toggle {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 6px 8px;
  font-size: 1.1rem;
  line-height: 1;
  border-radius: 4px;
  transition: color 0.2s;
}

.password-toggle:hover {
  color: var(--text-primary);
  background: var(--border);
}

.field-error {
  color: var(--error);
  font-size: 0.78rem;
  margin-top: 3px;
  display: block;
}

.form-group input.error {
  border-color: var(--error);
}

.form-group input.valid {
  border-color: var(--success);
}
</style>
