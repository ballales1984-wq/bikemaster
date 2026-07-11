import { createApp } from "vue";
import { createPinia, setActivePinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./index.css";
import { useAuthStore } from "./stores/auth";
import { useUIStore } from "./stores/ui";
import "./composables/usePWA";
import { useToast } from "./composables/useToast";
import { processOAuthToken } from "./services/oauth";
import { syncAuthState } from "./services/authSync";
import { apiGet } from "./utils/api";

const pinia = createPinia();
setActivePinia(pinia);

const app = createApp(App).use(pinia).use(router);

const auth = useAuthStore();
const ui = useUIStore();

ui.loadTheme();
processOAuthToken();
syncAuthState();

// A dangling OAuth spinner (oauthLoading persisted in sessionStorage) must
// never survive a bootstrap where we are not actually completing an OAuth
// return (e.g. the user closed the Google prompt and came back with no token).
// Otherwise the full-screen overlay would cover the app with no navigation to
// clear it.
if (!auth.isLoggedIn && ui.oauthLoading) {
  ui.setOauthLoading(false);
}

// Finalize an OAuth (Google) return: check whether the athlete profile is
// complete and navigate to the right authenticated route. Unlike a plain
// `router.push("/")`, this targets the correct route directly, because when the
// SPA document stays alive across the OAuth round-trip (PWA / mobile custom-tab
// return where only the URL fragment changes) the user is already on "/", so a
// push to "/" is a no-op and they would be stuck on the empty home screen until
// a manual refresh.
let oauthFinalized = false;
async function finalizeOAuthReturn() {
  if (oauthFinalized || !auth.isLoggedIn) return;
  oauthFinalized = true;
  let profileComplete = true;
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
    profileComplete = data.profile_complete === true;
  } catch {
    profileComplete = true;
  }
  auth.setJustLoggedIn(false);
  ui.setOauthLoading(false);
  const target = profileComplete ? "/rides" : "/athlete";
  // Only navigate if we are still on the empty home route. On a full document
  // reload the router guard has already performed the redirect, so re-issuing
  // a navigation here would cause a post-mount redirect flicker / wrong page
  // (the guard and this function each query /auth/me independently).
  if (router.currentRoute.value.path === "/") {
    router.replace(target).catch(() => {});
  }
}

// Google OAuth redirects back to `<origin>/#token=...`. If that return lands
// while the SPA document is still alive (bfcache restore, or a same-document
// fragment navigation), main.ts is NOT re-executed, the token fragment is
// never consumed and the user is stuck on the login screen until a manual
// refresh. Re-apply the token and finalize the navigation in those cases.
function handleOAuthReturn() {
  if (processOAuthToken()) {
    finalizeOAuthReturn();
  }
}
function handlePageShow(event: PageTransitionEvent) {
  if (event.persisted) handleOAuthReturn();
}
// `popstate` covers same-document returns where the token arrives via the query
// string (which `hashchange` does not fire for).
window.addEventListener("hashchange", handleOAuthReturn);
window.addEventListener("popstate", handleOAuthReturn);
window.addEventListener("pageshow", handlePageShow);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker
    .register("/sw.js", { scope: "/" })
    .then((reg) => {
      reg.addEventListener("updatefound", () => {
        const newWorker = reg.installing;
        if (newWorker) {
          newWorker.addEventListener("statechange", () => {
            if (
              newWorker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              window.location.reload();
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

app.mount("#app");

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
    if (auth.justLoggedIn) finalizeOAuthReturn();
  })
  .catch(() => {});

// HMR safety: remove the global OAuth-return listeners before Vite re-executes
// main.ts, otherwise repeated hot reloads would stack duplicate listeners that
// each re-run finalizeOAuthReturn against a stale module scope.
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    window.removeEventListener("hashchange", handleOAuthReturn);
    window.removeEventListener("popstate", handleOAuthReturn);
    window.removeEventListener("pageshow", handlePageShow);
  });
}
