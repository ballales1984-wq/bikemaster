<!-- Form di login/registrazione: tab Login/Register con validazione, toggle password e accesso Google OAuth.
     Props: nessuna. Eventi: login, register (con {username,password}), google-login, error. Usa auth store e useI18n.
     UI: tab accessibili (role=tab), input con label fluttuanti ed errori, spinner, separatore OAuth e pulsante Google. -->
<template>
  <div class="login-panel">
    <h2> {{ mode === "login" ? t("auth.login") : t("auth.register") }}</h2>
    <div
class="login-tabs" role="tablist" aria-label="Login modes">
      <button
        :id="'tab-login'"
        :class="['tab-btn', { active: mode === 'login' }]"
        role="tab"
        :aria-selected="mode === 'login'"
        aria-controls="login-form"
        @click="mode = 'login'"
        @keydown.arrowleft="mode = 'register'"
        @keydown.arrowright="mode = 'login'"
      >
        {{ t("auth.login") }}
      </button>
      <button
        :id="'tab-register'"
        :class="['tab-btn', { active: mode === 'register' }]"
        role="tab"
        :aria-selected="mode === 'register'"
        aria-controls="login-form"
        @click="mode = 'register'"
        @keydown.arrowleft="mode = 'login'"
        @keydown.arrowright="mode = 'register'"
      >
        {{ t("auth.register") }}
      </button>
    </div>

    <form
      :id="'login-form'"
      class="login-form"
      novalidate
      role="tabpanel"
      :aria-labelledby="mode === 'login' ? 'tab-login' : 'tab-register'"
      @submit.prevent="submit"
    >
      <div class="form-group" :class="{ 'has-error': usernameError }">
        <input
          id="username"
          v-model="form.username"
          type="text"
          :placeholder="t('common.name')"
          :disabled="loading"
          required
          autocomplete="username"
          :aria-invalid="!!usernameError"
          :aria-describedby="usernameError ? 'username-error' : undefined"
          :class="{
            error: usernameError,
            valid: form.username.length >= 3 && !usernameError,
          }"
        />
        <label for="username" class="floating-label">{{ t("auth.username") }}</label>
        <span
          v-if="usernameError"
          id="username-error"
          class="field-error"
          role="alert"
          aria-live="assertive"
          >{{ usernameError }}</span
        >
      </div>
      <div class="form-group" :class="{ 'has-error': passwordError }">
        <div class="password-wrapper">
          <input
            id="password"
            v-model="form.password"
            :type="showPassword ? 'text' : 'password'"
            :placeholder="mode === 'register' ? 'min 6 characters' : ''"
            :disabled="loading"
            required
            autocomplete="current-password"
            :aria-invalid="!!passwordError"
            :aria-describedby="passwordError ? 'password-error' : undefined"
            :class="{
              error: passwordError,
              valid: form.password.length >= 6 && !passwordError,
            }"
          />
          <label for="password" class="floating-label">{{ t("auth.password") }}</label>
          <button
            type="button"
            class="password-toggle"
            :aria-label="showPassword ? 'Hide password' : 'Show password'"
            :aria-pressed="showPassword"
            @click="showPassword = !showPassword"
          >
            {{ showPassword ? "" : "" }}
          </button>
        </div>
        <span
          v-if="passwordError"
          id="password-error"
          class="field-error"
          role="alert"
          aria-live="assertive"
          >{{ passwordError }}</span
        >
      </div>
      <button
        type="submit"
        class="btn btn-primary login-submit"
        :class="{ shake: shakeState }"
        :disabled="loading || !isFormValid"
        :aria-busy="loading"
      >
        <span
          v-if="loading"
          class="btn-spinner"
          aria-hidden="true"
        />
        <span class="btn-label">{{
          loading
            ? t("common.loading")
            : mode === "login"
              ? t("auth.login")
              : t("auth.register")
        }}</span>
      </button>
    </form>

    <div class="oauth-separator">
      <span>{{ t("common.or") }}</span>
    </div>
    <button
      class="btn btn-google"
      :disabled="loading"
      type="button"
      :aria-label="'Sign in with Google'"
      @click="loginWithGoogle"
    >
      <svg
class="google-icon" viewBox="0 0 24 24" width="20" height="20">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.76h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c3.05 0 5.84-1.15 7.86-3l-3.57-2.76c-.98.66-2.23 1.06-3.62 1.44v2.26C15.24 21.23 13.71 22 12 22z"
        />
        <path
          fill="#FBBC05"
          d="M6.27 15.73a7.5 7.5 0 0 1 0-3.46l2.93-2.27a7.5 7.5 0 0 0 1.74 3.19l-2.93 2.27z"
        />
        <path
          fill="#EA4335"
          d="M18.57 6.43a7.5 7.5 0 0 0-6.57-4.43 7.5 7.5 0 0 0-1.57.23l2.93 2.26a4.99 4.99 0 0 1 5.17 4.17z"
        />
      </svg>
      Sign in with Google
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useI18n } from "../composables/useI18n";
import { useUIStore } from "../stores/ui";
import { useAuthStore } from "../stores/auth";
import { resolveApiBase } from "../utils/backend-config";

const { t } = useI18n();
const ui = useUIStore();
const auth = useAuthStore();

const emit = defineEmits(["login", "register", "google-login", "error"]);

const mode = ref("login");
const loading = ref(false);
const showPassword = ref(false);
const shakeState = ref(false);
const form = ref({ username: "", password: "" });
const usernameError = ref("");
const passwordError = ref("");

const isFormValid = computed(() => {
  const userOk = form.value.username.length >= 3;
  const passOk =
    mode.value === "register"
      ? form.value.password.length >= 6
      : form.value.password.length > 0;
  return userOk && passOk && !usernameError.value && !passwordError.value;
});

function validate() {
  usernameError.value = "";
  passwordError.value = "";
  if (form.value.username.length > 0 && form.value.username.length < 3) {
    usernameError.value = "Min 3 characters";
  }
  if (
    mode.value === "register" &&
    form.value.password.length > 0 &&
    form.value.password.length < 6
  ) {
    passwordError.value = "Min 6 characters";
  }
}

function handleTouch(e) {
  if (e.type === "touchstart") {
    const target = e.target;
    target.classList.add("touch-active");
    const removeTouch = () => {
      target.classList.remove("touch-active");
      target.removeEventListener("touchend", removeTouch);
      target.removeEventListener("touchcancel", removeTouch);
    };
    target.addEventListener("touchend", removeTouch);
    target.addEventListener("touchcancel", removeTouch);
  }
}

async function submit() {
  validate();
  if (!isFormValid.value) {
    triggerShake();
    return;
  }
  loading.value = true;
  try {
    emit(mode.value, { ...form.value });
  } finally {
    loading.value = false;
  }
}

function triggerShake() {
  shakeState.value = false;
  requestAnimationFrame(() => {
    shakeState.value = true;
    setTimeout(() => (shakeState.value = false), 450);
  });
}

const isCapacitorApp = typeof window.Capacitor !== "undefined";

function getRedirectUri() {
  if (isCapacitorApp) {
    return "com.bikemaster.app://callback";
  }
  const base = resolveApiBase();
  if (base) {
    return `${base}/api/v1/auth/google/callback`;
  }
  return `${window.location.origin}/api/v1/auth/google/callback`;
}

async function loginWithGoogle() {
  loading.value = true;
  try {
    const base = resolveApiBase();
    const response = await fetch(`${base}/api/v1/auth/google`);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || `Google login error: ${response.status}`);
    }

    if (data.auth_url) {
      window.location.href = data.auth_url;
      return;
    }

    if (!data.access_token) {
      throw new Error("Google login error: invalid server response");
    }

    auth.setAuthFromUrl(data.access_token, data.email || "", data.id ? String(data.id) : undefined);
    ui.setOauthLoading(false);
    emit("google-login", { token: data.access_token });
  } catch (e) {
    ui.setOauthLoading(false);
    emit("error", e.message);
    alert(e.message);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-panel {
  position: relative;
  max-width: 420px;
  margin: 40px auto;
  background: var(--bg-secondary);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  padding: 32px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.login-panel::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: var(--radius);
  padding: 1px;
  background: var(--gradient-border);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  mask-composite: exclude;
  opacity: 0.5;
  animation: rotateGradient 6s linear infinite;
  pointer-events: none;
}
.login-panel::after {
  content: "";
  position: absolute;
  top: 0;
  left: 25%;
  width: 50%;
  height: 2px;
  background: var(--accent-gradient);
  box-shadow: var(--glow-soft);
  opacity: 0.7;
  pointer-events: none;
}
.login-panel h2 {
  text-align: center;
  margin-bottom: 20px;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-size: 1.4rem;
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.form-group {
  position: relative;
  display: flex;
  flex-direction: column;
}
.form-group input {
  background: rgba(0, 0, 0, 0.2);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
  font-size: 1rem;
  transition: var(--transition);
  font-family: inherit;
}
.form-group .floating-label {
  position: absolute;
  left: 14px;
  top: 14px;
  color: var(--text-muted);
  font-size: 1rem;
  pointer-events: none;
  transition: all var(--transition-fast);
  background: linear-gradient(var(--bg-secondary), var(--bg-secondary));
  padding: 0 4px;
}
.password-wrapper input:focus + .floating-label,
.password-wrapper input:not(:placeholder-shown) + .floating-label,
.form-group input:focus + .floating-label,
.form-group input:not(:placeholder-shown) + .floating-label {
  top: -8px;
  font-size: 0.72rem;
  color: var(--accent);
  letter-spacing: 0.04em;
}
.form-group input:focus {
  outline: none;
  border-color: var(--accent);
  background: rgba(0, 0, 0, 0.4);
  box-shadow: 0 0 0 3px rgba(0, 255, 204, 0.1), var(--glow-accent);
}
.login-submit.shake {
  animation: shake 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97);
}
@keyframes shake {
  10%, 90% { transform: translateX(-2px); }
  20%, 80% { transform: translateX(4px); }
  30%, 50%, 70% { transform: translateX(-6px); }
  40%, 60% { transform: translateX(6px); }
}
.btn-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(0, 0, 0, 0.3);
  border-top-color: #000;
  border-radius: 50%;
  animation: btnSpin 0.7s linear infinite;
  vertical-align: middle;
  margin-right: 8px;
}
@keyframes btnSpin {
  to { transform: rotate(360deg); }
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
  outline: none;
}
.tab-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.tab-btn.touch-active,
.btn.touch-active {
  transform: scale(0.97);
  opacity: 0.8;
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

.oauth-separator {
  display: flex;
  align-items: center;
  margin: 24px 0 16px;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.oauth-separator span {
  padding: 0 12px;
}

.oauth-separator::before,
.oauth-separator::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--border);
}

.btn-google {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px;
  background: #fff;
  color: #444;
  border: 1px solid #dadce0;
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-google:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #bdc1d1;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.btn-google:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.google-icon {
  flex-shrink: 0;
}
</style>
