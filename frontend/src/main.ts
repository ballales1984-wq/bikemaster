import { createApp } from "vue";
import { createPinia, setActivePinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./index.css";
import { useAuthStore } from "./stores/auth";
import { useUIStore } from "./stores/ui";
import "./composables/usePWA";
import { useToast } from "./composables/useToast";
import { processOAuthToken, hasPendingOAuth } from "./services/oauth";
import { syncAuthState } from "./services/authSync";
import { apiGet } from "./utils/api";
import type { ApiCallOptions } from "./utils/api";

const pinia = createPinia();
setActivePinia(pinia);

const app = createApp(App).use(pinia).use(router);

const auth = useAuthStore();
const ui = useUIStore();

ui.loadTheme();
const tokenProcessed = processOAuthToken();
console.log("[OAuth] bootstrap processOAuthToken:", tokenProcessed, "loggedIn:", auth.isLoggedIn);
syncAuthState();
console.log("[OAuth] bootstrap syncAuthState done, justLoggedIn:", auth.justLoggedIn);

// Finalize an OAuth (Google) return: check whether the athlete profile is
// complete and navigate to the right authenticated route. Unlike a plain
// `router.push("/")`, this targets the correct route directly, because when the
// SPA document stays alive across the OAuth round-trip (PWA / mobile custom-tab
// return where only the URL fragment changes) the user is already on "/", so a
// push to "/" is a no-op and they would be stuck on the empty home screen until
// a manual refresh.
let oauthFinalized = false;
async function finalizeOAuthReturn() {
  if (oauthFinalized || !auth.isLoggedIn) {
    console.log("[OAuth] finalize skipped:", { finalized: oauthFinalized, loggedIn: auth.isLoggedIn });
    return;
  }
  oauthFinalized = true;
  console.log("[OAuth] finalize started, current route:", router.currentRoute.value.path);
  let profileComplete = false;
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
    profileComplete = data.profile_complete === true;
  } catch (err) {
    console.warn("[OAuth] profile check failed:", err);
    profileComplete = false;
  }
  auth.setJustLoggedIn(false);
  ui.setOauthLoading(false);
  const target = profileComplete ? "/rides" : "/athlete";
  console.log("[OAuth] finalize target:", target, "current:", router.currentRoute.value.path);
  if (router.currentRoute.value.path !== target) {
    console.log("[OAuth] navigating to:", target);
    router.replace(target).catch(() => {});
  } else {
    console.log("[OAuth] already on target route:", target);
  }
}

// Google OAuth redirects back to `<origin>/#token=...`. If that return lands
// while the SPA document is still alive (bfcache restore, or a same-document
// fragment navigation), main.ts is NOT re-executed, the token fragment is
// never consumed and the user is stuck on the login screen until a manual
// refresh. Re-apply the token and finalize the navigation in those cases.
function handleOAuthReturn() {
  console.log("[OAuth] handleOAuthReturn, hash:", window.location.hash.slice(0, 50));
  if (processOAuthToken()) {
    finalizeOAuthReturn();
  }
}
window.addEventListener("hashchange", handleOAuthReturn);
window.addEventListener("pageshow", (event: PageTransitionEvent) => {
  if (event.persisted) handleOAuthReturn();
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker
    .register("/sw.js", { scope: "/" })
    .then((reg) => {
      reg.addEventListener("updatefound", () => {
        const newWorker = reg.installing;
        if (newWorker) {
          newWorker.addEventListener("statechange", () => {
            // Never force a reload while an OAuth return is being finalized:
            // reloading mid-round-trip drops the in-flight login and strands
            // the user on the login screen. The token is recovered from
            // sessionStorage on the next load instead.
            if (
              newWorker.state === "installed" &&
              navigator.serviceWorker.controller &&
              !hasPendingOAuth() &&
              !auth.justLoggedIn
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
    console.log("[OAuth] router.isReady, justLoggedIn:", auth.justLoggedIn, "route:", router.currentRoute.value.path);
    if (auth.justLoggedIn) finalizeOAuthReturn();
    else ui.setOauthLoading(false);
  })
  .catch(() => {});
