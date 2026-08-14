/**
 * BikeMaster Frontend — Vue Router routing.
 *
 * Defines public and protected routes, the authentication guard
 * and dynamic title handling for each view.
 */

import { defineComponent, h } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";
import { syncAuthState } from "../services/authSync";
import { apiGet } from "../utils/api";
import { processOAuthToken } from "../services/oauth";
import { AUTH_CHUNK_RELOAD_KEY } from "../utils/auth-storage";

/** Empty home shell — must not use a string `template` (no runtime compiler in prod). */
const EmptyHome = defineComponent({
  name: "EmptyHome",
  setup: () => () => h("div"),
});

const routes = [
  {
    path: "/",
    name: "home",
    component: EmptyHome,
  },
  {
    path: "/welcome",
    name: "welcome",
    component: () => import("../views/WelcomePage.vue"),
    meta: { title: "Benvenuto" },
  },
  {
    path: "/rides",
    name: "rides",
    component: () => import("../views/RidesView.vue"),
    meta: { title: "Le mie uscite" },
  },
  {
    path: "/rides/:id",
    name: "ride-detail",
    component: () => import("../components/RideDetail.vue"),
    meta: { requiresAuth: true, title: "Dettaglio Uscita" },
  },
  {
    path: "/dashboard",
    name: "dashboard",
    component: () => import("../components/DashboardPanel.vue"),
    meta: { requiresAuth: true, title: "Dashboard" },
  },
  {
    path: "/import",
    name: "import",
    component: () => import("../components/ImportPanel.vue"),
    meta: { requiresAuth: true, title: "Importa uscite" },
  },
  {
    path: "/athlete",
    name: "athlete",
    component: () => import("../components/AthletePanel.vue"),
    meta: { requiresAuth: true, title: "Profilo atleta" },
  },
  {
    path: "/avatar",
    name: "avatar",
    component: () => import("../components/AthleteAvatarPanel.vue"),
    meta: { requiresAuth: true, title: "Avatar atleta" },
  },
  {
    path: "/coach",
    name: "coach",
    component: () => import("../components/CoachPanel.vue"),
    meta: { requiresAuth: true, title: "AI Coach" },
  },
  {
    path: "/knowledge",
    name: "knowledge",
    component: () => import("../components/KnowledgePanel.vue"),
    meta: { requiresAuth: true, title: "Knowledge Base" },
  },
  {
    path: "/bm2",
    name: "bm2",
    component: () => import("../components/Bm2Panel.vue"),
    meta: { requiresAuth: true, title: "BikeMaster 2.0" },
  },
  {
    path: "/calendar",
    name: "calendar",
    component: () => import("../components/CalendarPanel.vue"),
    meta: { requiresAuth: true, title: "Calendario" },
  },
  {
    path: "/granfondo",
    name: "granfondo",
    component: () => import("../components/GranfondoPlanner.vue"),
    meta: { requiresAuth: true, title: "Granfondo Planner" },
  },
  {
    path: "/map",
    name: "map",
    component: () => import("../components/RideMapPanel.vue"),
    meta: { requiresAuth: true, title: "Route Maps" },
  },
  {
    path: "/pois",
    name: "pois",
    component: () => import("../views/PoiMapView.vue"),
    meta: { requiresAuth: true, title: "Itinerari & POI" },
  },
  {
    path: "/itinerary",
    name: "itinerary",
    component: () => import("../views/ItineraryView.vue"),
    meta: { requiresAuth: true, title: "Itinerari" },
  },
  {
    path: "/aethermap",
    name: "aethermap",
    component: () => import("../views/AetherMapView.vue"),
    meta: { requiresAuth: true, title: "AetherMap" },
  },
  {
    path: "/comparison",
    name: "comparison",
    component: () => import("../components/RideComparison.vue"),
    meta: { requiresAuth: true, title: "Confronto uscite" },
  },
  {
    path: "/heatmap",
    name: "heatmap",
    component: () => import("../components/HeatmapPanel.vue"),
    meta: { requiresAuth: true, title: "Heatmap" },
  },
  {
    path: "/badges",
    name: "badges",
    component: () => import("../components/BadgesPanel.vue"),
    meta: { requiresAuth: true, title: "Badge" },
  },
  {
    path: "/weather",
    name: "weather",
    component: () => import("../components/WeatherPanel.vue"),
    meta: { requiresAuth: true, title: "Meteo" },
  },
  {
    path: "/zones",
    name: "zones",
    component: () => import("../components/ZonesPanel.vue"),
    meta: { requiresAuth: true, title: "Zone di Allenamento" },
  },
  {
    path: "/metabolism",
    name: "metabolism",
    component: () => import("../views/MetabolismView.vue"),
    meta: { requiresAuth: true, title: "Metabolismo" },
  },
  {
    path: "/beck",
    name: "beck",
    component: () => import("../views/BeckView.vue"),
    meta: { requiresAuth: true, title: "Analisi Beck" },
  },
  {
    path: "/performance",
    name: "performance",
    component: () => import("../views/PerformanceView.vue"),
    meta: { requiresAuth: true, title: "Analisi Prestazioni" },
  },
  {
    path: "/admin",
    name: "admin",
    component: () => import("../components/AdminPanel.vue"),
    meta: { requiresAuth: true, requiresAdmin: true, title: "Amministrazione" },
  },
  {
    path: "/admin/bm2",
    name: "admin-bm2",
    component: () => import("../components/AdminBm2Panel.vue"),
    meta: { requiresAuth: true, requiresAdmin: true, title: "Admin BM2" },
  },
  {
    path: "/admin/users",
    name: "admin-users",
    component: () => import("../components/AdminUserManagement.vue"),
    meta: { requiresAuth: true, requiresAdmin: true, title: "Gestione utenti" },
  },
  {
    path: "/client",
    name: "client",
    component: () => import("../views/ClientDashboard.vue"),
    meta: { requiresAuth: true, requiresClient: true, title: "Area client" },
  },
  {
    path: "/track",
    name: "tracking",
    component: () => import("../views/RideTracking.vue"),
    meta: { requiresAuth: true, title: "Tracciamento uscita" },
  },
  {
    path: "/hr24h",
    name: "hr24h",
    component: () => import("../components/Hr24hPanel.vue"),
    meta: { requiresAuth: true, title: "Frequenza cardiaca 24h" },
  },
  {
    path: "/privacy",
    name: "privacy",
    component: () => import("../views/PrivacyPolicy.vue"),
    meta: { title: "Privacy Policy" },
  },
  {
    path: "/terms",
    name: "terms",
    component: () => import("../views/TermsOfService.vue"),
    meta: { title: "Termini di servizio" },
  },
  {
    path: "/cookies",
    name: "cookies",
    component: () => import("../views/CookiePolicy.vue"),
    meta: { title: "Cookie Policy" },
  },
  {
    path: "/about",
    name: "about",
    component: () => import("../views/AboutUs.vue"),
    meta: { title: "Chi siamo" },
  },
  {
    path: "/contact",
    name: "contact",
    component: () => import("../views/ContactUs.vue"),
    meta: { title: "Contatti" },
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("../views/SettingsView.vue"),
    meta: { requiresAuth: true, title: "Impostazioni backend" },
  },
  {
    path: "/settings/connections",
    name: "settings-connections",
    component: () => import("../views/ConnectionsView.vue"),
    meta: { requiresAuth: true, title: "Connessioni" },
  },
  {
    path: "/monitoring",
    name: "monitoring",
    component: () => import("../views/MonitoringView.vue"),
    meta: { requiresAuth: true, requiresAdmin: true, title: "Monitoring" },
  },
];

// Retry a lazy component import a few times before giving up. Route chunks can
// briefly return 5xx while the (free-tier) backend cold-starts or redeploys.
function retryImport<T>(
  loader: () => Promise<T>,
  retries = 3,
  delayMs = 800,
): Promise<T> {
  return loader().catch((err) => {
    if (retries <= 0) throw err;
    return new Promise<T>((resolve) => setTimeout(resolve, delayMs)).then(() =>
      retryImport(loader, retries - 1, delayMs * 1.5),
    );
  });
}

// Wrap every lazy route loader with the retry helper (single place, no need to
// touch each route definition).
for (const route of routes) {
  const holder = route as { component: unknown };
  if (typeof holder.component === "function") {
    const loader = holder.component as () => Promise<unknown>;
    holder.component = () => retryImport(loader);
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (to && to.hash) {
      return { el: to.hash, behavior: "smooth" };
    }
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  },
});

async function checkProfileComplete(
  auth: ReturnType<typeof useAuthStore>,
): Promise<boolean> {
  try {
    const data = await apiGet<{ profile_complete?: boolean }>(
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

router.beforeEach((to) => {
  const auth = useAuthStore();
  const ui = useUIStore();
  // main.ts processes OAuth tokens during bootstrap (main.ts:37) and via
  // hashchange/pageshow listeners for same-document returns. The guard only
  // needs to handle a token that reached the router without main.ts
  // consuming it. If auth is already settled, skip — otherwise every
  // post-login navigation logs a misleading "[OAuth] no token found"
  // (the token was already consumed and the URL cleaned by main.ts).
  if (!auth.isLoggedIn) {
    processOAuthToken();
  }
  const { hasToken, justLoggedIn } = syncAuthState();

  if (to.meta.requiresAuth && !hasToken) {
    return "/";
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return "/";
  }

  if (to.meta.requiresClient && !auth.isClient) {
    return "/";
  }

  // Logged-in user on the empty home route: enter the app immediately.
  // Do NOT await /auth/me here — a slow/cold Render instance used to block
  // next() and leave the user stranded on "/" until a manual refresh
  // (password login already pushes /rides synchronously; mirror that).
  if (hasToken && to.path === "/") {
    if (justLoggedIn) {
      auth.setJustLoggedIn(false);
      ui.setOauthLoading(false);
      if (import.meta.env.DEV)
        console.log(
          "[OAuth] guard navigating to /rides (profile refine async)",
        );
      void checkProfileComplete(auth).then((complete) => {
        if (!complete && router.currentRoute.value.path === "/rides") {
          router.replace("/athlete").catch(() => {});
        }
      });
    }
    if (ui.oauthLoading) {
      ui.setOauthLoading(false);
    }
    return "/rides";
  }

  if (ui.oauthLoading) {
    ui.setOauthLoading(false);
  }
});

router.afterEach((to) => {
  if (to.meta.title) {
    document.title = to.meta.title as string;
  }
});

// Last-resort recovery: if a route chunk still fails to load (e.g. a redeploy
// replaced the hashed asset that the current index.html references), force a
// full page reload so the browser fetches the fresh index + chunks. Guarded
// against reload loops.
router.onError((error, to) => {
  const message = (error as Error)?.message || "";
  const isChunkError =
    /dynamically imported module|Importing a module script failed|Failed to fetch|Loading chunk|error loading dynamically/i.test(
      message,
    );
  console.error("[router] navigation error:", error, "to:", to?.fullPath);
  if (!isChunkError) return;
  const key = AUTH_CHUNK_RELOAD_KEY;
  const last = Number(sessionStorage.getItem(key) || "0");
  if (Date.now() - last < 10000) return;
  sessionStorage.setItem(key, String(Date.now()));
  window.location.assign(to?.fullPath || window.location.href);
});

export default router;
