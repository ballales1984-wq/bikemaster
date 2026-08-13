<!--
BikeMaster Frontend — AppLayout shell.

Responsibility:
- Sidebar navigation (collapsible, icons + labels, mobile bottom nav)
- TopBar (breadcrumb, theme toggle, user menu)
- Content area with router-view
- Footer
- Mobile responsive
-->

<template>
  <div class="layout" :class="{ 'sidebar-collapsed': ui.sidebarCollapsed }">
    <Sidebar
      :collapsed="ui.sidebarCollapsed"
      :is-admin="isAdmin"
      :is-client="isClient"
      @toggle="ui.toggleSidebar"
      @logout="onLogout"
    />

    <div class="layout-main">
      <TopBar
        :collapsed="ui.sidebarCollapsed"
        @toggle-sidebar="ui.toggleSidebar"
        @logout="onLogout"
      />

      <main id="main-content" class="layout-content">
        <ErrorBoundary>
          <router-view v-slot="{ Component }">
            <transition name="route" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </ErrorBoundary>
      </main>

      <footer class="layout-footer">
        <div class="footer-inner">
          <div class="footer-brand">
            <span class="footer-logo">BikeMaster</span>
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
            <span class="footer-version">v{{ version }}</span>
            <span class="footer-dot">•</span>
            <span>© {{ year }} BikeMaster</span>
          </div>
        </div>
      </footer>
    </div>

    <BottomNav v-if="!isPublicPage" />
    <nav v-if="isPublicPage" class="public-links-mobile">
      <router-link to="/about">Chi Siamo</router-link>
      <router-link to="/contact">Contatti</router-link>
      <router-link to="/privacy">Privacy</router-link>
      <router-link to="/terms">Termini</router-link>
      <router-link to="/cookies">Cookie</router-link>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";
import { apiGet } from "../utils/api";
import Sidebar from "../components/navigation/Sidebar.vue";
import TopBar from "../components/navigation/TopBar.vue";
import BottomNav from "../components/navigation/BottomNav.vue";
import ErrorBoundary from "../components/ErrorBoundary.vue";

const auth = useAuthStore();
const ui = useUIStore();
const route = useRoute();
const router = useRouter();
const version = ref("");

const isAdmin = computed(() => auth.isAdmin);
const isClient = computed(() => auth.isClient);
const isPublicPage = computed(() =>
  ["/privacy", "/terms", "/cookies", "/about", "/contact", "/welcome"].includes(
    route.path,
  ),
);
const year = new Date().getFullYear();

async function loadVersion() {
  try {
    const data = await apiGet<{ version: string }>(
      "/api/v1/version",
      {},
      { timeoutMs: 5000, noRetry: true },
    );
    version.value = data.version || "";
  } catch {
    version.value = "";
  }
}

async function onLogout() {
  try {
    await auth.logout();
  } catch (e) {
    console.error("Logout failed", (e as Error).message);
  }
  router.push("/");
}

onMounted(() => {
  loadVersion();
});
</script>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
  position: relative;
}

.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  margin-left: var(--sidebar-width);
  transition: margin-left var(--transition);
}

.sidebar-collapsed .layout-main {
  margin-left: var(--sidebar-width-collapsed);
}

.layout-content {
  flex: 1;
  padding: var(--space-5);
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

.layout-footer {
  border-top: 1px solid var(--border);
  background: linear-gradient(0deg, rgba(10, 11, 16, 0.5), transparent);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.footer-inner {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-6) 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  text-align: center;
}

.footer-brand {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
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
  gap: var(--space-5);
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
  gap: var(--space-2);
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

.public-links-mobile {
  display: none;
}

@media (max-width: 768px) {
  .layout-main {
    margin-left: 0 !important;
  }

  .layout-content {
    padding: var(--space-3);
    padding-bottom: 80px;
  }

  .public-links-mobile {
    display: flex;
    gap: var(--space-4);
    justify-content: center;
    flex-wrap: wrap;
    padding: var(--space-3);
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: var(--z-header);
  }

  .public-links-mobile a {
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.8rem;
    padding: var(--space-1) var(--space-2);
    border-radius: 4px;
    transition: color 0.2s;
  }

  .public-links-mobile a:hover {
    color: var(--accent);
  }
}

@media (prefers-reduced-motion: reduce) {
  .layout-main {
    transition: none;
  }
}
</style>
