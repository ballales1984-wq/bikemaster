<!--
BikeMaster Frontend — componente root.

Liability:
- layout globale (header, sfondo animato, tema scuro/chiaro)
- gestisce login/registrazione quando non autenticato
- routing outlet verso view e pannelli autenticati
- overlay loading OAuth e prompt installazione PWA
-->

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
          <span class="brand-badge" aria-hidden="true"></span>
          <div class="brand-text">
            <h1 class="logo">BikeMaster</h1>
            <p v-if="loggedIn" class="tagline">
              Cycling Performance Intelligence
            </p>
          </div>
        </div>

        <div class="header-actions">
          <WeatherClockWidget />
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

    <ConsentBanner @saved="onConsentSaved" />

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

    <template v-else>
      <HeaderTabs
        :is-admin="isAdmin"
        :is-client="isClient"
        @logout="onLogout"
      />

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

      <VoiceSystemProvider />

      <HelpGuide />
    </template>

    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span class="footer-logo"> BikeMaster</span>
          <span class="footer-tag">Cycling Performance Intelligence</span>
        </div>
        <div class="footer-links">
          <router-link to="/about">Chi Siamo</router-link>
          <router-link to="/contact">Contatti</router-link>
          <router-link to="/privacy">Privacy</router-link>
          <router-link to="/terms">Termini</router-link>
          <router-link to="/cookies">Cookie</router-link>
        </div>
        <div class="footer-social">
          <button
            class="social-btn"
            title="Condividi su Facebook"
            @click="shareOnFacebook"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path
                d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z"
              />
            </svg>
          </button>
          <a
            class="social-btn"
            href="https://www.instagram.com/bikemaster_app"
            target="_blank"
            rel="noopener"
            title="Instagram"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path
                d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"
              />
            </svg>
          </a>
          <a
            class="social-btn"
            href="https://www.linkedin.com/shareArticle?mini=true&url=https://www.bikemaster.app"
            target="_blank"
            rel="noopener"
            title="Condividi su LinkedIn"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path
                d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
              />
            </svg>
          </a>
          <button class="social-btn" title="Copia link" @click="copyLink">
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path
                d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"
              />
              <path
                d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"
              />
            </svg>
          </button>
        </div>
        <div class="footer-meta">
          <span v-if="version" class="footer-version">v{{ version }}</span>
          <span v-else class="footer-version">v2.0</span>
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
import { apiGet } from "./utils/api";
import LoginForm from "./components/LoginForm.vue";
import HeaderTabs from "./components/HeaderTabs.vue";
import StatsSummary from "./components/StatsSummary.vue";
import ToastContainer from "./components/ToastContainer.vue";
import PWAInstallPrompt from "./components/PWAInstallPrompt.vue";
import LanguageSwitcher from "./components/LanguageSwitcher.vue";
import WeatherClockWidget from "./components/WeatherClockWidget.vue";
import ErrorBoundary from "./components/ErrorBoundary.vue";
import HelpGuide from "./components/HelpGuide.vue";
import VoiceSystemProvider from "./components/VoiceSystemProvider.vue";
import ConsentBanner from "./components/ConsentBanner.vue";
const auth = useAuthStore();
const ui = useUIStore();
const route = useRoute();
const router = useRouter();
const { locale, setLocale } = useI18n();
const loggedIn = computed(() => auth.isLoggedIn);
const isAdmin = computed(() => auth.isAdmin);
const isClient = computed(() => auth.isClient);
const isPublicPage = computed(() =>
  ["/privacy", "/terms", "/cookies", "/about", "/contact", "/welcome"].includes(
    route.path,
  ),
);
const showHeader = computed(() => loggedIn.value || isPublicPage.value);
const year = new Date().getFullYear();
const version = ref("");
const summary = ref({
  rides: 0,
  distance_km: 0,
  calories: 0,
  avg_speed_kmh: 0,
  duration_minutes: 0,
});
const summaryLoading = ref(false);
const loginError = ref("");
const { fetchSummary } = useRides();

const appUrl =
  typeof window !== "undefined"
    ? window.location.origin
    : "https://www.bikemaster.app";

async function shareOnFacebook() {
  const url = encodeURIComponent(window.location.href);
  window.open(
    `https://www.facebook.com/sharer/sharer.php?u=${url}`,
    "_blank",
    "width=600,height=400",
  );
}

async function shareOnLinkedIn() {
  const url = encodeURIComponent(window.location.href);
  window.open(
    `https://www.linkedin.com/sharing/share-offsite/?url=${url}`,
    "_blank",
    "width=600,height=400",
  );
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href);
    ui.setToast("Link copiato negli appunti", "success");
  } catch {
    ui.setToast("Impossibile copiare il link", "error");
  }
}

async function loadVersion() {
  try {
    const data = await apiGet(
      "/api/v1/version",
      {},
      { timeoutMs: 5000, noRetry: true },
    );
    version.value = data.version || "";
  } catch {
    version.value = "";
  }
}

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

// Safety net for Google OAuth: if auth is set but the router is still on the
// empty home route (guard race / stalled profile check), enter the app like
// password login does with router.push("/rides").
watch(
  () => [loggedIn.value, route.path],
  ([logged, path]) => {
    if (logged && path === "/") {
      router.replace("/rides").catch(() => {});
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
    await auth.login(creds.username, creds.password);
    const complete = await checkProfileComplete();
    const target = complete ? "/rides" : "/athlete";
    router.push(target);
    await loadSummary();
  } catch (e) {
    loginError.value = e.message;
  }
}

async function onGoogleLogin() {
  loginError.value = "";
  ui.setOauthLoading(false);
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
    await loadSummary();
  }
}

async function onRegister(creds) {
  try {
    loginError.value = "";
    await auth.register(creds.username, creds.password);
    try {
      await auth.login(creds.username, creds.password);
      router.push("/rides");
      await loadSummary();
    } catch {
      loginError.value =
        "Account created. Please log in with your new credentials.";
    }
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
  loadVersion();
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
  z-index: var(--z-base);
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
.app-header {
  text-align: center;
  padding: 1.5rem 1rem;
  border-bottom: 1px solid var(--border);
  transition: var(--transition);
  position: relative;
  z-index: var(--z-header);
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
  z-index: var(--z-content);
}
.app-main {
  position: relative;
  z-index: var(--z-content);
  flex: 1;
}
.footer {
  margin-top: auto;
  z-index: var(--z-content);
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
.footer-social {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.social-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
}
.social-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  transform: translateY(-2px);
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

/* ===== Route transition ===== */
.route-enter-active {
  transition:
    opacity 0.35s var(--ease-out-quint),
    transform 0.35s var(--ease-out-quint);
}
.route-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
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
