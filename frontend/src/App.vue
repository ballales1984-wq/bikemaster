<!--
BikeMaster Frontend — App.vue root.

Responsibilities:
- Public pages (login, welcome, legal pages)
- OAuth loading overlay
- PWA install prompt
- Consent banner
- Delegate authenticated layout to AppLayout
-->

<template>
  <div class="app" :class="{ 'light-theme': !ui.isDark }">
    <div class="app-bg" aria-hidden="true">
      <span class="orb orb-1" />
      <span class="orb orb-2" />
      <span class="orb orb-3" />
    </div>

    <div class="skip-link">
      <a href="#main-content">Salta al contenuto</a>
    </div>

    <div v-if="ui.oauthLoading" class="oauth-loading-overlay">
      <div class="spinner" />
      <p class="loading-text">Finalizing login...</p>
    </div>

    <template v-if="!loggedIn && !isPublicPage && !ui.oauthLoading">
      <div class="login-wrapper">
        <LoginForm
          @login="onLogin"
          @register="onRegister"
          @google-login="onGoogleLogin"
          @error="loginError = $event"
        />
        <p v-if="loginError" class="login-error">
          {{ loginError }}
        </p>
      </div>
    </template>

    <template v-else-if="loggedIn">
      <AppLayout @logout="onLogout" />
    </template>

    <template v-else>
      <ErrorBoundary>
        <router-view />
      </ErrorBoundary>
    </template>

    <PWAInstallPrompt />

    <ConsentBanner @saved="onConsentSaved" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth";
import { useUIStore } from "./stores/ui";
import { useI18n } from "./composables/useI18n";
import { apiGet } from "./utils/api";
import LoginForm from "./components/LoginForm.vue";
import PWAInstallPrompt from "./components/PWAInstallPrompt.vue";
import ConsentBanner from "./components/ConsentBanner.vue";
import ErrorBoundary from "./components/ErrorBoundary.vue";
import AppLayout from "./layouts/AppLayout.vue";

const auth = useAuthStore();
const ui = useUIStore();
const route = useRoute();
const router = useRouter();
const { locale, setLocale } = useI18n();
const loggedIn = computed(() => auth.isLoggedIn);
const isPublicPage = computed(() =>
  ["/privacy", "/terms", "/cookies", "/about", "/contact", "/welcome"].includes(
    route.path,
  ),
);
const loginError = ref("");

watch(
  () => ui.isDark,
  (val) => {
    document.body.classList.toggle("light-theme", !val);
  },
  { immediate: true },
);

watch(
  () => loggedIn.value,
  (val) => {
    if (val && ui.oauthLoading) {
      ui.setOauthLoading(false);
    }
  },
);

watch(
  () => [loggedIn.value, route.path],
  ([logged, path]) => {
    if (logged && path === "/" && !ui.oauthLoading) {
      router.replace("/rides").catch(() => {});
    }
  },
);

watch(
  () => route.path,
  () => {
    loginError.value = "";
  },
);

async function onLogin(creds: { username: string; password: string }) {
  try {
    loginError.value = "";
    await auth.login(creds.username, creds.password);
    const complete = await checkProfileComplete();
    const target = complete ? "/rides" : "/athlete";
    router.push(target);
  } catch (e) {
    const err = e as Error;
    loginError.value = err.message;
  }
}

async function onGoogleLogin() {
  loginError.value = "";
  if (loggedIn.value) {
    const complete = await checkProfileComplete();
    if (!complete && (route.path === "/" || route.path === "")) {
      try {
        await router.replace("/athlete");
      } catch {
        /* ignore */
      }
    } else if (route.path === "/" || route.path === "") {
      try {
        await router.replace("/rides");
      } catch {
        /* ignore */
      }
    }
  }
}

async function onRegister(creds: { username: string; password: string }) {
  try {
    loginError.value = "";
    await auth.register(creds.username, creds.password);
    try {
      await auth.login(creds.username, creds.password);
      router.push("/rides");
    } catch {
      loginError.value =
        "Account created. Please log in with your new credentials.";
    }
  } catch (e) {
    const err = e as Error;
    loginError.value = err.message;
  }
}

async function onLogout() {
  try {
    await auth.logout();
  } catch (e) {
    console.error("Logout failed", (e as Error).message);
    loginError.value = "Logout failed. Please try again.";
  }
  router.push("/");
}

async function checkProfileComplete() {
  try {
    const data = await apiGet(
      "/api/v1/auth/me",
      {},
      {
        headers: { Authorization: `Bearer ${auth.token}` },
        suppressAuthClear: true,
        timeoutMs: 8000,
        noRetry: true,
      },
    );
    return data.profile_complete === true;
  } catch {
    return false;
  }
}

function onConsentSaved() {
  /* consent recorded; no further action required */
}

onMounted(() => {
  setLocale(locale.value || "en");
  window.addEventListener("oauth-loading-end", () => {
    ui.setOauthLoading(false);
  });
});
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: var(--z-base);
}

.skip-link {
  position: absolute;
  top: -100%;
  left: 16px;
  z-index: 9999;
}

.skip-link a {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: var(--accent);
  color: #000;
  font-weight: 600;
  border-radius: var(--radius-sm);
  text-decoration: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.skip-link a:focus {
  top: 16px;
}

.app-bg {
  position: fixed;
  inset: 0;
  z-index: var(--z-bg);
  pointer-events: none;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
  will-change: transform;
}

.orb-1 {
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, rgba(0, 255, 204, 0.5), transparent 70%);
  top: -120px;
  left: -100px;
  animation: orbFloat1 18s ease-in-out infinite alternate;
}

.orb-2 {
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(0, 136, 255, 0.45), transparent 70%);
  bottom: -120px;
  right: -80px;
  animation: orbFloat2 22s ease-in-out infinite alternate;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(
    circle,
    rgba(168, 85, 247, 0.35),
    transparent 70%
  );
  top: 40%;
  left: 55%;
  animation: orbFloat3 26s ease-in-out infinite alternate;
}

@keyframes orbFloat1 {
  to {
    transform: translate(60px, 80px) scale(1.15);
  }
}

@keyframes orbFloat2 {
  to {
    transform: translate(-70px, -40px) scale(1.1);
  }
}

@keyframes orbFloat3 {
  to {
    transform: translate(-40px, 60px) scale(0.9);
  }
}

.login-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
  position: relative;
  z-index: var(--z-content);
}

.login-error {
  color: var(--error);
  text-align: center;
  margin-top: 0.5rem;
}

.oauth-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal-backdrop);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  margin-top: 16px;
  color: var(--text-primary);
}

@media (prefers-reduced-motion: reduce) {
  .orb {
    animation: none !important;
  }
}
</style>
