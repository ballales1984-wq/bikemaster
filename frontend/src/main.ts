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
import { initI18n } from "./composables/useI18n";
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

// Bfcache-safe SW update tracking.
// When a new SW is found we send SKIP_WAITING but do NOT immediately reload.
// The page may be entering or stored in the back/forward cache at that moment,
// and a synchronous window.location.reload() during the freeze transition is
// what triggers Chrome's "IgnoreEventAndEvict" bfcache error.
// Instead we wait for the `controllerchange` event (which only fires while
// the page is active) and only reload then — or on pageshow restore if the
// new SW already took control while the page was in the cache.
let swUpdatePending = false;

window.addEventListener("pageshow", (event: PageTransitionEvent) => {
  if (event.persisted) {
    if (swUpdatePending && navigator.serviceWorker?.controller) {
      swUpdatePending = false;
      window.location.reload();
    }
    handleOAuthReturn();
  }
});

if ("serviceWorker" in navigator && !isTauri()) {
  navigator.serviceWorker
    .register("/sw.js?v=2", { scope: "/" })
    .then((reg) => {
      // Reload only after the new SW has taken control AND the page is
      // visible. `controllerchange` fires while the page is running
      // (not frozen in bfcache), so this avoids the
      // "IgnoreEventAndEvict" error that a synchronous reload would
      // cause during the bfcache freeze transition.
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (!swUpdatePending) return;
        if (document.visibilityState !== "visible") return;
        swUpdatePending = false;
        void reg.update();
        window.location.reload();
      });

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
                // Defer SW activation until the OAuth round-trip is done
                const attemptActivate = () => {
                  if (!hasPendingOAuth() && !auth.justLoggedIn) {
                    swUpdatePending = true;
                    try {
                      newWorker.postMessage({ type: "SKIP_WAITING" });
                    } catch {
                      // message channel closed during SW update
                    }
                  } else {
                    setTimeout(attemptActivate, 500);
                  }
                };
                setTimeout(attemptActivate, 500);
              } else {
                swUpdatePending = true;
                try {
                  newWorker.postMessage({ type: "SKIP_WAITING" });
                } catch {
                  // message channel closed during SW update
                }
                // Do NOT reload here: controllerchange will fire once
                // the new SW takes control, and we reload only when
                // the page is visible — bfcache-safe.
              }
            }
          });
        }
      });
      if (reg.waiting) {
        if (!hasPendingOAuth() && !auth.justLoggedIn) {
          swUpdatePending = true;
          try {
            reg.waiting.postMessage({ type: "SKIP_WAITING" });
          } catch {
            // message channel closed during SW update
          }
        }
      }
    })
    .catch((err) => {
      console.warn("[SW] service worker registration failed:", err);
    });
}

// Initialize the local SQLite DB (offline cache) and load the per-user
// API keys saved on the device. Best-effort if not available.
void initLocalDb();
void useApiKeysStore().load();

// Load i18n messages before mounting so the first render shows translated
// text instead of raw message keys. Non-fatal: if loading fails we still
// mount so the user isn't stranded on a blank screen.
(async () => {
  try {
    await initI18n();
  } catch (err) {
    console.warn("[i18n] message load failed, using fallback keys:", err);
  }

  app.mount("#app");

  // Safety net: the OAuth loading overlay must never permanently block the UI.
  setTimeout(() => ui.setOauthLoading(false), 10000);

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
    .catch((err) => {
      console.error("[Router] isReady failed:", err);
      ui.setOauthLoading(false);
    });
})();
