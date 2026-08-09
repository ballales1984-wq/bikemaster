/**
 * Handles the client-side OAuth 2.0 flow.
 *
 * Processes the token present in the URL (query or fragment) after the provider
 * redirect, persists it in the Pinia store and removes it from the address
 * bar. To survive page reloads during the round-trip, it temporarily saves the
 * token in sessionStorage and recovers it if needed. The auth store itself
 * also mirrors state to sessionStorage so a mid-round-trip reload (service
 * worker update, bfcache restore) cannot drop a finalized login.
 *
 * Exports: hasPendingOAuth, processOAuthToken
 */

import { useAuthStore, isTokenExpired } from "../stores/auth";
import { useUIStore } from "../stores/ui";

// In-flight OAuth tokens are stashed here so a page reload that happens during
// the OAuth round-trip (a service-worker update, a bfcache restore, a transient
// error) cannot drop the login. The flag is cleared as soon as the token is
// consumed from the URL, so it only ever bridges the gap between "token arrived
// in the URL" and "auth state persisted to localStorage".
const OAUTH_PENDING_KEY = "bikemaster_oauth_pending";
const OAUTH_STATE_KEY = "bikemaster_oauth_state";

type PendingOAuth = { token: string; email: string; userId: string };

function generateOAuthState(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function storeOAuthState(state: string): void {
  try {
    sessionStorage.setItem(OAUTH_STATE_KEY, state);
  } catch {
    /* ignore */
  }
}

export function consumeOAuthState(): string | null {
  try {
    const state = sessionStorage.getItem(OAUTH_STATE_KEY);
    sessionStorage.removeItem(OAUTH_STATE_KEY);
    return state;
  } catch {
    return null;
  }
}

function validateOAuthState(returnedState: string | null): boolean {
  if (!returnedState) return true;
  const expected = consumeOAuthState();
  if (!expected) {
    console.warn(
      "[OAuth] state parameter present but no expected state stored",
    );
    return false;
  }
  if (returnedState !== expected) {
    console.warn("[OAuth] state mismatch — possible CSRF");
    return false;
  }
  return true;
}

function persistPendingOAuth(token: string, email: string, userId: string) {
  try {
    sessionStorage.setItem(
      OAUTH_PENDING_KEY,
      JSON.stringify({ token, email, userId } as PendingOAuth),
    );
  } catch {
    /* sessionStorage unavailable — login simply won't survive a reload */
  }
}

function clearPendingOAuth() {
  try {
    sessionStorage.removeItem(OAUTH_PENDING_KEY);
  } catch {
    /* ignore */
  }
}

function consumePendingOAuth(): PendingOAuth | null {
  try {
    const raw = sessionStorage.getItem(OAUTH_PENDING_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PendingOAuth;
    if (parsed && typeof parsed.token === "string" && parsed.token) {
      sessionStorage.removeItem(OAUTH_PENDING_KEY);
      return parsed;
    }
    sessionStorage.removeItem(OAUTH_PENDING_KEY);
    return null;
  } catch {
    return null;
  }
}

function clearUrlToken() {
  if (window.history.replaceState) {
    window.history.replaceState({}, document.title, "/");
  }
}

export function hasPendingOAuth(): boolean {
  try {
    return sessionStorage.getItem(OAUTH_PENDING_KEY) !== null;
  } catch {
    return false;
  }
}

export function processOAuthToken(): boolean {
  const auth = useAuthStore();
  const ui = useUIStore();
  const urlParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(
    window.location.hash.replace(/^#/, ""),
  );
  const urlToken = urlParams.get("token") || hashParams.get("token");
  const email = urlParams.get("email") || hashParams.get("email") || "";
  const userId = urlParams.get("user_id") || hashParams.get("user_id") || "";
  const oauthError =
    urlParams.get("oauth_error") || hashParams.get("oauth_error");
  const returnedState =
    urlParams.get("state") || hashParams.get("state") || null;

  if (oauthError) {
    clearPendingOAuth();
    auth.setOauthError(oauthError);
    ui.setOauthLoading(false);
    clearUrlToken();
    console.warn("[OAuth] URL error:", oauthError);
    return true;
  }

  if (!validateOAuthState(returnedState)) {
    clearPendingOAuth();
    ui.setOauthLoading(false);
    clearUrlToken();
    ui.setToast("Invalid OAuth state. Please try logging in again.", "error");
    return false;
  }

  // Fresh OAuth return: the token is in the URL fragment/query.
  if (urlToken) {
    if (isTokenExpired(urlToken)) {
      clearPendingOAuth();
      ui.setOauthLoading(false);
      clearUrlToken();
      ui.setToast("OAuth token expired. Please try logging in again.", "error");
      console.warn("[OAuth] token expired, rejecting");
      return false;
    }
    persistPendingOAuth(urlToken, email, userId);
    if (auth.isLoggedIn && auth.isTokenValid()) {
      clearPendingOAuth();
      ui.setOauthLoading(false);
      clearUrlToken();
      if (import.meta.env.DEV)
        console.log("[OAuth] already logged in, skipping");
      return false;
    }
    auth.setAuthFromUrl(urlToken, email, userId);
    clearPendingOAuth();
    ui.setOauthLoading(false);
    clearUrlToken();
    if (import.meta.env.DEV)
      console.log("[OAuth] token consumed from URL, profile:", email);
    return true;
  }

  // No token in the URL: recover one stashed by a previous load that was
  // interrupted by a reload during the OAuth round-trip.
  const pending = consumePendingOAuth();
  if (pending) {
    auth.setAuthFromUrl(pending.token, pending.email, pending.userId);
    clearPendingOAuth();
    ui.setOauthLoading(false);
    if (import.meta.env.DEV)
      console.log("[OAuth] token recovered from sessionStorage");
    return true;
  }

  // Safety: if there is no OAuth token/error to process, never leave the app
  // stuck behind the loading overlay (e.g. a backend redirect that dropped
  // the param, or a transient round-trip error).
  if (import.meta.env.DEV)
    console.log("[OAuth] no token found in URL or sessionStorage");
  ui.setOauthLoading(false);
  return false;
}

export { storeOAuthState, consumeOAuthState };
