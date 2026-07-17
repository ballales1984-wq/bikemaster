<template>
  <div class="app" :class="{ 'light-theme': !ui.isDark }">
    <div class="app-bg" aria-hidden="true">
      <span class="orb orb-1" />
      <span class="orb orb-2" />
      <span class="orb orb-3" />
    </div>

    <header v-show="showHeader" class="app-header">
      <div class="header-inner">
        <div class="header-brand">
          <span class="brand-badge" aria-hidden="true">🚴</span>
          <div class="brand-text">
            <h1 class="logo">BikeMaster</h1>
            <p v-if="loggedIn" class="tagline">Cycling Performance Intelligence</p>
          </div>
        </div>

        <div class="header-actions">
          <LanguageSwitcher />
          <button
            class="theme-toggle"
            :aria-label="ui.isDark ? 'Light mode' : 'Dark mode'"
            @click="ui.toggleTheme"
          >
            {{ ui.isDark ? "☀️" : "🌙" }}
          </button>
        </div>
      </div>

      <nav v-if="isPublicPage" class="public-links">
        <router-link to="/about"> Chi Siamo </router-link>
        <router-link to="/contact"> Contatti </router-link>
        <router-link to="/privacy"> Privacy </router-link>
        <router-link to="/terms"> Termini </router-link>
        <router-link to="/cookies"> Cookie </router-link>
      </nav>
    </header>

    <div v-if="ui.oauthLoading" class="oauth-loading-overlay">
      <div class="spinner" />
      <p class="loading-text">Finalizing login...</p>
    </div>

    <PWAInstallPrompt />

    <template v-if="!loggedIn && !isPublicPage && !ui.oauthLoading">
      <div class="login-wrapper">
        <LoginForm
          @login="onLogin"
          @register="onRegister"
          @error="loginError = $event"
        />
        <p v-if="loginError" class="login-error">
          {{ loginError }}
        </p>
      </div>
    </template>

    <template v-else>
      <HeaderTabs :is-admin="isAdmin" @logout="onLogout" />

      <StatsSummary
        v-if="loggedIn"
        :stats="summary"
        :loading="summaryLoading"
        @summary-change="onSummaryChange"
      />

      <main class="app-main">
        <ErrorBoundary>
          <router-view v-slot="{ Component }">
            <transition name="route" mode="out-in">
              <component :is="Component" @summary-change="onSummaryChange" />
            </transition>
          </router-view>
        </ErrorBoundary>
      </main>

      <ToastContainer />
    </template>

    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span class="footer-logo">🚴 BikeMaster</span>
          <span class="footer-tag">Cycling Performance Intelligence</span>
        </div>
        <div class="footer-links">
          <router-link to="/about">Chi Siamo</router-link>
          <router-link to="/contact">Contatti</router-link>
          <router-link to="/privacy">Privacy</router-link>
          <router-link to="/terms">Termini</router-link>
          <router-link to="/cookies">Cookie</router-link>
        </div>
        <div class="footer-meta">
          <span class="footer-version">v2.0</span>
          <span class="footer-dot">•</span>
          <span>© {{ year }} BikeMaster</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth";
import { useUIStore } from "./stores/ui";
import { useRides } from "./composables/useRides";
import { useI18n } from "./composables/useI18n";
import LoginForm from "./components/LoginForm.vue";
import HeaderTabs from "./components/HeaderTabs.vue";
import StatsSummary from "./components/StatsSummary.vue";
import ToastContainer from "./components/ToastContainer.vue";
import PWAInstallPrompt from "./components/PWAInstallPrompt.vue";
import LanguageSwitcher from "./components/LanguageSwitcher.vue";
import ErrorBoundary from "./components/ErrorBoundary.vue";
import { AUTH_LOGIN_ERROR_KEY } from "./utils/auth-storage";
const auth = useAuthStore();
const ui = useUIStore();
const route = useRoute();
const router = useRouter();
const { locale, setLocale } = useI18n();
const loggedIn = computed(() => auth.isLoggedIn);
const isAdmin = computed(() => auth.isAdmin);
const isPublicPage = computed(() =>
  ["/privacy", "/terms", "/cookies", "/about", "/contact", "/welcome"].includes(
    route.path,
  ),
);
const showHeader = computed(() => loggedIn.value || isPublicPage.value);
const year = new Date().getFullYear();
const summary = ref({
  rides: 0,
  distance_km: 0,
  calories: 0,
  avg_speed_kmh: 0,
  duration_minutes: 0,
});
const summaryLoading = ref(false);
const loginError = ref(localStorage.getItem(AUTH_LOGIN_ERROR_KEY) || "");
const { fetchSummary } = useRides();

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

async function loadSummary() {
  summaryLoading.value = true;
  try {
    const data = await fetchSummary();
    summary.value = {
      rides: data.rides ?? 0,
      distance_km: data.distance_km ?? 0,
      calories: data.calories ?? 0,
      avg_speed_kmh: data.avg_speed_kmh ?? 0,
      duration_minutes: data.duration_minutes ?? 0,
    };
  } finally {
    summaryLoading.value = false;
  }
}

async function onLogin(creds) {
  try {
    loginError.value = "";
    localStorage.removeItem(AUTH_LOGIN_ERROR_KEY);
    await auth.login(creds.username, creds.password);
    router.push("/rides");
    await loadSummary();
  } catch (e) {
    loginError.value = e.message;
  }
}

async function onRegister(creds) {
  try {
    loginError.value = "";
    localStorage.removeItem(AUTH_LOGIN_ERROR_KEY);
    await auth.register(creds.username, creds.password);
    await auth.login(creds.username, creds.password);
    router.push("/rides");
    await loadSummary();
  } catch (e) {
    loginError.value = e.message;
  }
}

async function onLogout() {
  try {
    await auth.logout();
  } catch (e) {
    console.error("Logout failed", e);
    loginError.value = "Logout failed. Please try again.";
  }
  router.push("/");
  summary.value = {
    rides: 0,
    distance_km: 0,
    calories: 0,
    avg_speed_kmh: 0,
    duration_minutes: 0,
  };
}

async function onSummaryChange() {
  await loadSummary();
}

onMounted(() => {
  setLocale(locale.value || "en");
  window.addEventListener("oauth-loading-end", () => {
    ui.setOauthLoading(false);
  });
  if (loggedIn.value) loadSummary();
});
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}
.app-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
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
  background: radial-gradient(circle, rgba(168, 85, 247, 0.35), transparent 70%);
  top: 40%;
  left: 55%;
  animation: orbFloat3 26s ease-in-out infinite alternate;
}
@keyframes orbFloat1 {
  to { transform: translate(60px, 80px) scale(1.15); }
}
@keyframes orbFloat2 {
  to { transform: translate(-70px, -40px) scale(1.1); }
}
@keyframes orbFloat3 {
  to { transform: translate(-40px, 60px) scale(0.9); }
}
.app-header {
  text-align: center;
  padding: 1.5rem 1rem;
  border-bottom: 1px solid var(--border);
  transition: var(--transition);
  position: relative;
  z-index: 2;
  background: linear-gradient(180deg, rgba(10, 11, 16, 0.4), transparent);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}
.header-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-align: left;
}
.brand-badge {
  font-size: 2rem;
  filter: drop-shadow(0 0 10px rgba(0, 255, 204, 0.4));
  animation: float 4s ease-in-out infinite;
}
.brand-text {
  display: flex;
  flex-direction: column;
}
.logo {
  font-size: 1.9rem;
  margin: 0;
  line-height: 1.1;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: var(--letter-spacing-tight);
  animation: logoGlow 3s ease-in-out infinite alternate;
  will-change: filter;
}
@keyframes logoGlow {
  from {
    filter: brightness(1);
  }
  to {
    filter: brightness(1.2) drop-shadow(0 0 8px rgba(0, 255, 204, 0.4));
  }
}
.tagline {
  color: var(--text-muted);
  margin: 0;
  font-size: 0.85rem;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.public-links {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 0.8rem;
  padding-bottom: 0.4rem;
}
.public-links a {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.85rem;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  transition: color 0.2s;
}
.public-links a:hover {
  color: var(--accent);
}
.login-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
  position: relative;
  z-index: 1;
}
.app-main {
  position: relative;
  z-index: 1;
  flex: 1;
}
.footer {
  margin-top: auto;
  z-index: 1;
  border-top: 1px solid var(--border);
  background: linear-gradient(0deg, rgba(10, 11, 16, 0.5), transparent);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.footer-inner {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  text-align: center;
}
.footer-brand {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  flex-wrap: wrap;
  justify-content: center;
}
.footer-logo {
  font-weight: var(--font-weight-bold);
  font-size: 1.05rem;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.footer-tag {
  color: var(--text-secondary);
  font-size: 0.85rem;
}
.footer-links {
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
  justify-content: center;
}
.footer-links a {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.85rem;
  transition: color 0.2s;
}
.footer-links a:hover {
  color: var(--accent);
}
.footer-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-muted);
  font-size: 0.8rem;
}
.footer-version {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.1rem 0.6rem;
  font-size: 0.72rem;
  color: var(--accent);
}
.footer-dot {
  opacity: 0.5;
}
.login-error {
  color: var(--error);
  text-align: center;
  margin-top: 0.5rem;
}

.theme-toggle {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition);
  flex-shrink: 0;
}

.theme-toggle:hover {
  border-color: var(--accent);
  box-shadow: 0 0 12px rgba(0, 255, 204, 0.2);
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
  z-index: 1000;
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

/* ===== Route transition ===== */
.route-enter-active {
  transition: opacity 0.35s var(--ease-out-quint), transform 0.35s var(--ease-out-quint);
}
.route-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.route-enter-from {
  opacity: 0;
  transform: translateY(14px) scale(0.99);
}
.route-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.99);
}

@media (prefers-reduced-motion: reduce) {
  .orb,
  .brand-badge,
  .logo {
    animation: none !important;
  }
  .route-enter-active,
  .route-leave-active {
    transition: opacity 0.1s ease;
  }
}
</style>
