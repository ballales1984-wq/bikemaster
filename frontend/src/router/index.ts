import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";
import { syncAuthState } from "../services/authSync";
import { apiGet } from "../utils/api";
import { processOAuthToken } from "../services/oauth";
import {
  AUTH_JUST_LOGGED_IN_KEY,
  AUTH_CHUNK_RELOAD_KEY,
} from "../utils/auth-storage";

const routes = [
  {
    path: "/",
    name: "home",
    component: { template: "<div />" },
  },
  {
    path: "/rides",
    name: "rides",
    component: () => import("../views/RidesView.vue"),
    meta: { title: "Le mie uscite" },
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
    path: "/admin",
    name: "admin",
    component: () => import("../components/AdminPanel.vue"),
    meta: { requiresAuth: true, requiresAdmin: true, title: "Amministrazione" },
  },
  {
    path: "/track",
    name: "tracking",
    component: () => import("../views/RideTracking.vue"),
    meta: { requiresAuth: true, title: "Tracciamento uscita" },
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

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore();
  const ui = useUIStore();
  // Capture a token delivered in the URL fragment/query (e.g. an OAuth return
  // whose navigation reached the guard before main.ts consumed it).
  processOAuthToken();
  const { hasToken, justLoggedIn } = syncAuthState();

  if (to.meta.requiresAuth && !hasToken) {
    next("/");
    return;
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    next("/");
    return;
  }

  // Profile completeness check only for fresh OAuth returns / logins.
  // A normal returning user with a valid token goes straight to /rides.
  if (hasToken && justLoggedIn && to.path === "/") {
    console.log("[OAuth] guard redirecting, profile check...");
    try {
      const hasCompleteProfile = await checkProfileComplete(auth);
      const target = hasCompleteProfile ? "/rides" : "/athlete";
      console.log("[OAuth] guard navigating to:", target);
      await next(target);
    } catch {
      console.warn("[OAuth] guard profile check failed, navigating to /athlete");
      await next("/athlete");
    }
    ui.setOauthLoading(false);
    auth.setJustLoggedIn(false);
    localStorage.removeItem(AUTH_JUST_LOGGED_IN_KEY);
    return;
  }

  // Logged-in user on the empty home route: redirect to the app.
  if (hasToken && to.path === "/") {
    next("/rides");
    return;
  }

  if (ui.oauthLoading) {
    ui.setOauthLoading(false);
  }

  next();
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
  if (!isChunkError) return;
  const key = AUTH_CHUNK_RELOAD_KEY;
  const last = Number(sessionStorage.getItem(key) || "0");
  if (Date.now() - last < 10000) return; // already tried recently, avoid a loop
  sessionStorage.setItem(key, String(Date.now()));
  window.location.assign(to?.fullPath || window.location.href);
});

export default router;
