/**
 * BikeMaster Frontend — entrypoint.
 *
 * Vue 3 SPA bootstrap:
 * - initializes Pinia, router, theme and the local SQLite DB
 *
 * Cache-bust for Render deploy: OAuth popup fix v2
 * - handles the Google OAuth return (token fragment + finalize)
 * - registers the service worker for PWA/updates
 */

import { createApp } from "vue";
import { createPinia, setActivePinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./index.css";
import { useAuthStore } from "./stores/auth";
import { useUIStore } from "./stores/ui";
import { isTauri } from "./utils/backend-config";
import "./composables/usePWA";
import { processOAuthToken, hasPendingOAuth } from "./services/oauth";
import { syncAuthState } from "./services/authSync";
import { apiGet } from "./utils/api";
import type { ApiCallOptions } from "./utils/api";
import { initLocalDb } from "./db/localDb";
import { useApiKeysStore } from "./stores/apiKeys";

const pinia = createPinia();
setActivePinia(pinia);

const app = createApp(App).use(pinia).use(router);

const auth = useAuthStore();
const ui = useUIStore();

ui.loadTheme();
const tokenProcessed = processOAuthToken();
syncAuthState();

// Set when the current page load actually consumed an OAuth (Google) token,
// either from the URL fragment (full document load) or from the sessionStorage
// stash (a reload mid-round-trip). Drives the post-login navigation. We do NOT
// rely on `auth.justLoggedIn` here: the router guard also reads it and may have
// already cleared it by the time `router.isReady()` resolves, which previously
// caused `finalizeOAuthReturn` to be skipped and stranded the user on the login
// screen until a manual refresh.
let oauthReturnPending = tokenProcessed;
let oauthFinalized = false;
async function finalizeOAuthReturn() {
  if (oauthFinalized || !auth.isLoggedIn) {
    return;
  }
  oauthFinalized = true;
  oauthReturnPending = false;
  auth.setJustLoggedIn(false);
  ui.setOauthLoading(false);
  // Enter the app immediately (same as password login). Profile completeness
  // is refined afterwards so a slow /auth/me never strands the user on "/".
  const path = router.currentRoute.value.path;
  if (path === "/" || path === "") {
    try {
      await router.replace("/rides");
    } catch {
      /* ignore */
    }
  }
  try {
    const data = await apiGet<{ profile_complete?: boolean }>(
      "/api/v1/auth/me",
      {},
      {
        headers: { Authorization: `Bearer ${auth.token}` },
        suppressAuthClear: true,
        timeoutMs: 8000,
        noRetry: true,
      } as ApiCallOptions,
    );
    if (
      data.profile_complete !== true &&
      router.currentRoute.value.path === "/rides"
    ) {
      await router.replace("/athlete").catch(() => {});
    }
  } catch (err) {
    console.warn("[OAuth] profile check failed:", err);
  }
}

// Google OAuth redirects back to `<origin>/#token=...`. If that return lands
// while the SPA document is still alive (bfcache restore, or a same-document
// fragment navigation), main.ts is NOT re-executed, the token fragment is
// never consumed and the user is stuck on the login screen until a manual
// refresh. Re-apply the token and finalize the navigation in those cases.
function handleOAuthReturn() {
  if (processOAuthToken()) {
    oauthReturnPending = true;
    finalizeOAuthReturn();
  }
}
window.addEventListener("hashchange", handleOAuthReturn);
window.addEventListener("pageshow", (event: PageTransitionEvent) => {
  if (event.persisted) handleOAuthReturn();
});

if ("serviceWorker" in navigator && !isTauri()) {
  navigator.serviceWorker
    .register("/sw.js", { scope: "/" })
    .then((reg) => {
      reg.addEventListener("updatefound", () => {
        const newWorker = reg.installing;
        if (newWorker) {
          newWorker.addEventListener("statechange", () => {
            if (newWorker.state === "activated") {
              void reg.update();
            }
            if (
              newWorker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              if (hasPendingOAuth() || auth.justLoggedIn) {
                newWorker.postMessage({ type: "SKIP_WAITING" });
                setTimeout(() => {
                  if (reg.active && !hasPendingOAuth()) {
                    window.location.reload();
                  }
                }, 3000);
              } else {
                window.location.reload();
              }
            }
          });
        }
      });
      if (reg.waiting) {
        reg.waiting.postMessage({ type: "SKIP_WAITING" });
      }
    })
    .catch(() => {});
}

// Initialize the local SQLite DB (offline cache) and load the per-user
// API keys saved on the device. Best-effort if not available.
void initLocalDb();
void useApiKeysStore().load();

app.mount("#app");

// Safety net: the OAuth loading overlay must never permanently block the UI.
// If anything goes wrong during the OAuth round-trip (dropped param, transient
// error, stuck flag), force it off after a short grace period.
setTimeout(() => ui.setOauthLoading(false), 10000);

// If the OAuth (Google) return was consumed during bootstrap (full document
// load), the guard already finalizes the navigation as part of the initial
// route resolution. Re-running finalizeOAuthReturn here *before* that initial
// navigation has settled races with the guard's `next()` (both issue a
// navigation) and, depending on timing, can cancel the redirect and strand the
// user on the empty "/" home route until a manual refresh. So wait for the
// initial navigation to settle, then only finalize if the guard didn't already
// move us off "/". The same-document (fragment) return path reaches this via
// the hashchange/pageshow listeners below, where the router is already ready.
router
  .isReady()
  .then(() => {
    if (oauthReturnPending && router.currentRoute.value.path !== "/") {
      oauthFinalized = true;
      oauthReturnPending = false;
      auth.setJustLoggedIn(false);
      ui.setOauthLoading(false);
    } else if (oauthReturnPending) {
      finalizeOAuthReturn();
    } else {
      ui.setOauthLoading(false);
    }
  })
  .catch(() => {});
